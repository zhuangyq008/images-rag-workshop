import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as opensearch from 'aws-cdk-lib/aws-opensearchservice';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';

export class CdkImageProcessingStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create S3 bucket for image storage with the specified naming pattern
    const imageBucket = new s3.Bucket(this, 'ImageBucket', {
      bucketName: `imagebucket-${this.account}-${this.region}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // 创建 Origin Access Control
    const oac = new cloudfront.CfnOriginAccessControl(this, 'OAC', {
      originAccessControlConfig: {
        name: 'S3OAC',
        originAccessControlOriginType: 's3',
        signingBehavior: 'always', 
        signingProtocol: 'sigv4',
      }
    });

    // 创建 CloudFront 分配
    const cloudFrontDistribution = new cloudfront.Distribution(this, 'ImageDistribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(imageBucket, {
          originAccessControlId: oac.attrId
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      defaultRootObject: 'index.html',
      enableLogging: true,
    });

    // 更新 S3 存储桶策略，确保只有 CloudFront 能够访问
    imageBucket.addToResourcePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:GetObject'],
      resources: [`${imageBucket.bucketArn}/*`],
      principals: [
        new iam.ServicePrincipal('cloudfront.amazonaws.com') // 允许 CloudFront 访问
      ],
      conditions: {
        "StringEquals": {
          "AWS:SourceArn": `arn:aws:cloudfront::${this.account}:distribution/${cloudFrontDistribution.distributionId}`
        }
      }
    }));

    // 创建 Cognito 用户池
    const userPool = new cognito.UserPool(this, 'CognitoUserPool', {
      userPoolName: `MyCognitoUserPool-${this.account}`,
      passwordPolicy: {
        minLength: 8,
        requireLowercase: false,
        requireUppercase: false,
        requireDigits: false,
        requireSymbols: false
      }
    });

    // 创建用户池域
    const userPoolDomain = userPool.addDomain('CognitoUserPoolDomain', {
      cognitoDomain: {
        domainPrefix: `my-user-pool-domain-${this.account}`
      }
    });

    // 创建用户池客户端
    const userPoolClient = new cognito.UserPoolClient(this, 'CognitoUserPoolClient', {
      userPool: userPool,
      generateSecret: false,
      authFlows: {
        adminUserPassword: true
      }
    });

    // 创建 Cognito 身份池
    const identityPool = new cognito.CfnIdentityPool(this, 'CognitoIdentityPool', {
      identityPoolName: `MyIdentityPool-${this.account}`,
      allowUnauthenticatedIdentities: false,
      cognitoIdentityProviders: [
        {
          providerName: `cognito-idp.${this.region}.amazonaws.com/${userPool.userPoolId}`,
          clientId: userPoolClient.userPoolClientId
        }
      ]
    });

    // 创建 IAM 角色，授权 Cognito 用户池访问 OpenSearch
    const authenticatedRole = new iam.Role(this, 'MyAuthenticatedRole', {
      assumedBy: new iam.FederatedPrincipal(
        'cognito-identity.amazonaws.com',
        {
          'StringEquals': { 'cognito-identity.amazonaws.com:aud': identityPool.ref }
        },
        'sts:AssumeRoleWithWebIdentity'
      ),
      inlinePolicies: {
        CognitoAccessPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['*'],
              resources: ['*'],
              effect: iam.Effect.ALLOW
            })
          ]
        })
      }
    });

    // 附加角色到身份池
    new cognito.CfnIdentityPoolRoleAttachment(this, 'MyIdentityPoolRoleAttachment', {
      identityPoolId: identityPool.ref,
      roles: {
        authenticated: authenticatedRole.roleArn
      }
    });

    // 创建 OpenSearch IAM 角色
    const openSearchRole = new iam.Role(this, 'MyOpenSearchRole', {
      assumedBy: new iam.ServicePrincipal('es.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonESFullAccess'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonCognitoPowerUser')
      ]
    });

    // 创建 OpenSearch 域
    const openSearchDomain =  new opensearch.Domain(this, 'OpenSearchDomain', {
      version: opensearch.EngineVersion.OPENSEARCH_2_15,
      capacity: {
        multiAzWithStandbyEnabled: false,
        dataNodes: 1,
        dataNodeInstanceType: 'r7g.large.search'
      },
      nodeToNodeEncryption: true,
      zoneAwareness: {
        enabled: false  // 禁用区域感知
      },
      encryptionAtRest: {
        enabled: true
      },
      enforceHttps: true,
      fineGrainedAccessControl: {
        masterUserArn: authenticatedRole.roleArn
      },
      cognitoDashboardsAuth: {
        identityPoolId: identityPool.ref,
        role: openSearchRole,
        userPoolId: userPool.userPoolId
      },
      ebs: {
        enabled: true,
        volumeSize: 20,
        volumeType: ec2.EbsDeviceVolumeType.GENERAL_PURPOSE_SSD_GP3, 
      }
    });
  
    // 获取 OpenSearch 的 endpoint
    const openSearchEndpoint = openSearchDomain.domainEndpoint;

    // Create Lambda layer with dependencies
    const dependenciesLayer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      code: lambda.Code.fromAsset('lambda/lambda_layer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_10],
      description: 'Dependencies for image processing lambda',
    });

    // Create Lambda function
    const imageProcessingFunction = new lambda.Function(this, 'ImageProcessingFunction', {
      runtime: lambda.Runtime.PYTHON_3_10,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda'),
      layers: [dependenciesLayer],
      memorySize: 512,
      environment: {
        BUCKET_NAME: imageBucket.bucketName,
        OPENSEARCH_ENDPOINT: openSearchEndpoint,
        DDSTRIBUTION_DOMAIN: cloudFrontDistribution.domainName
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Get caller identity ARN from context
    const callerArn = this.node.tryGetContext('callerArn') || cdk.Fn.importValue('CallerArn');

    
    // Grant Lambda permissions
    imageBucket.grantReadWrite(imageProcessingFunction);
    imageProcessingFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: ['*'],
    }));
    imageProcessingFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'es:ESHttpGet',
        'es:ESHttpPut',
        'es:ESHttpPost',
        'es:ESHttpDelete'
      ],
      resources: [`${openSearchDomain.domainArn}/*`],
    }));

    // Create API Gateway
    const api = new apigateway.RestApi(this, 'ImageProcessingApi', {
      restApiName: 'Image Processing Service',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
      }
    });

    // Create API resources and methods with AuthorizationType.NONE
    const imagesResource = api.root.addResource('images');
    
    if (!imagesResource.node.tryFindChild('OPTIONS')) {
      imagesResource.addMethod('OPTIONS', new apigateway.MockIntegration({
        integrationResponses: [{
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'",
            'method.response.header.Access-Control-Allow-Methods': "'OPTIONS,POST,PUT,DELETE'",
          },
        }],
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          "application/json": "{\"statusCode\": 200}"
        },
      }), {
        methodResponses: [{
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
            'method.response.header.Access-Control-Allow-Headers': true,
            'method.response.header.Access-Control-Allow-Methods': true,
          },
        }],
      });
    }
        
    imagesResource.addMethod('POST', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // Upload
    imagesResource.addMethod('PUT', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    });  // Update
    imagesResource.addMethod('DELETE', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // Delete
    
    const searchResource = imagesResource.addResource('search');
    
    if (!searchResource.node.tryFindChild('OPTIONS')) {
      imagesResource.addMethod('OPTIONS', new apigateway.MockIntegration({
        integrationResponses: [{
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': "'*'",
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'",
            'method.response.header.Access-Control-Allow-Methods': "'OPTIONS,POST,PUT,DELETE'",
          },
        }],
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          "application/json": "{\"statusCode\": 200}"
        },
      }), {
        methodResponses: [{
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Origin': true,
            'method.response.header.Access-Control-Allow-Headers': true,
            'method.response.header.Access-Control-Allow-Methods': true,
          },
        }],
      });
    }

    searchResource.addMethod('POST', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // Search
    

    // Output the API Gateway URL
    new cdk.CfnOutput(this, 'ApiGatewayUrl', {
      value: api.url,
      description: 'The URL of the API Gateway',
    });

    // Output the S3 bucket name
    new cdk.CfnOutput(this, 'S3BucketName', {
      value: imageBucket.bucketName,
      description: 'The name of the S3 bucket for image storage',
    });

  }
}
