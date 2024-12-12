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

    // Create new IAM role for Bedrock
    const bedrockRole = new iam.Role(this, 'BedrockRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      description: 'IAM role for Amazon Bedrock',
    });

    // Add trust relationship
    bedrockRole.assumeRolePolicy?.addStatements(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('bedrock.amazonaws.com')],
        actions: ['sts:AssumeRole'],
        conditions: {
          StringEquals: {
            'aws:SourceAccount': this.account,
          },
          ArnEquals: {
            'aws:SourceArn': `arn:aws:bedrock:${this.region}:${this.account}:model-invocation-job/*`,
          },
        },
      })
    );

    // Add permissions policy
    bedrockRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'S3Access',
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetObject', 's3:PutObject', 's3:ListBucket'],
        resources: [
          imageBucket.bucketArn,
          `${imageBucket.bucketArn}/*`,
        ],
        conditions: {
          StringEquals: {
            'aws:ResourceAccount': [this.account],
          },
        },
      })
    );

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
      assumedBy: new iam.CompositePrincipal(
        new iam.FederatedPrincipal(
          'cognito-identity.amazonaws.com',
          {
            'StringEquals': { 'cognito-identity.amazonaws.com:aud': identityPool.ref }
          },
          'sts:AssumeRoleWithWebIdentity'
        ),
        new iam.ServicePrincipal('lambda.amazonaws.com') // 允许 Lambda 假设该角色
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

    // Create Lambda function using Docker with ARM64 architecture
    const imageProcessingFunction = new lambda.DockerImageFunction(this, 'ImageProcessingFunctionContainer', {
      code: lambda.DockerImageCode.fromImageAsset('lambda'),
      role: authenticatedRole,
      memorySize: 512,
      architecture: lambda.Architecture.ARM_64,
      environment: {
        BUCKET_NAME: imageBucket.bucketName,
        OPENSEARCH_ENDPOINT: openSearchEndpoint,
        DDSTRIBUTION_DOMAIN: cloudFrontDistribution.domainName,
        BEDROCK_ROLE_ARN: bedrockRole.roleArn  // Add the Bedrock role ARN to the environment variables
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Get caller identity ARN from context
    const callerArn = this.node.tryGetContext('callerArn') || cdk.Fn.importValue('CallerArn');
    
    // Grant Lambda permissions
    imageBucket.grantReadWrite(imageProcessingFunction);
    imageProcessingFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel', "bedrock:CreateModelInvocationJob", "bedrock:ListModelInvocationJobs", "bedrock:GetModelInvocationJob"],
      resources: ['*'],
    }));
    imageProcessingFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'es:*'
      ],
      resources: ['*'],
    }));

    // Create API Gateway
    const api = new apigateway.RestApi(this, 'ImageProcessingApi', {
      restApiName: 'Image Processing Service',
    });

    // Create API resources and methods with AuthorizationType.NONE
    const imagesResource = api.root.addResource('images');
    
        
    imagesResource.addMethod('POST', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // Upload
    imagesResource.addMethod('PUT', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    });  // Update

    const deleteResource = imagesResource.addResource('{image_id}');

    deleteResource.addMethod('DELETE', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // DELETE
    
    const searchResource = imagesResource.addResource('search');

    searchResource.addMethod('POST', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // Search

    const batchUploadResource = imagesResource.addResource('batch-upload');

    batchUploadResource.addMethod('POST', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // Batch Upload

    const batchDescnEnrichResource = imagesResource.addResource('batch-descn-enrich');

    batchDescnEnrichResource.addMethod('POST', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // Batch Descn Enrich

    // Create API resources and methods for checking batch job state with AuthorizationType.NONE
    const checkJobStateResource = api.root.addResource('check-batch-job-state');

    checkJobStateResource.addMethod('POST', new apigateway.LambdaIntegration(imageProcessingFunction), {
      authorizationType: apigateway.AuthorizationType.NONE
    }); // Check batch job state

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

    // Output the Bedrock IAM Role ARN
    new cdk.CfnOutput(this, 'BedrockRoleArn', {
      value: bedrockRole.roleArn,
      description: 'The ARN of the IAM role for Amazon Bedrock',
    });
  }
}
