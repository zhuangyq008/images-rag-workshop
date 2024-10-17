import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as opensearchserverless from 'aws-cdk-lib/aws-opensearchserverless';

export class CdkImageProcessingStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create S3 bucket for image storage with the specified naming pattern
    const imageBucket = new s3.Bucket(this, 'ImageBucket', {
      bucketName: `imagebucket-${this.account}-${this.region}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // Create OpenSearch Serverless encryption policy
    const encryptionPolicy = new opensearchserverless.CfnSecurityPolicy(this, 'CollectionEncryptionPolicy', {
      name: 'encryption-policy',
      type: 'encryption',
      description: 'Encryption policy for image collection',
      policy: JSON.stringify({
        Rules: [
          {
            ResourceType: 'collection',
            Resource: ['collection/image-collection'],
          },
        ],
        AWSOwnedKey: true,
      }),
    });

    // Create OpenSearch Serverless collection
    const collection = new opensearchserverless.CfnCollection(this, 'ImageCollection', {
      name: 'image-collection',
      type: 'VECTORSEARCH',
    });

    // Ensure the collection is created after the encryption policy
    collection.addDependency(encryptionPolicy);

    // Create Lambda function
    const imageProcessingFunction = new lambda.Function(this, 'ImageProcessingFunction', {
      runtime: lambda.Runtime.PYTHON_3_10,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda'),
      environment: {
        BUCKET_NAME: imageBucket.bucketName,
        COLLECTION_NAME: collection.name,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Create OpenSearch Serverless data access policy
    const dataAccessPolicy = new opensearchserverless.CfnAccessPolicy(this, 'CollectionDataAccessPolicy', {
      name: 'image-collection-data-policy',
      type: 'data',
      description: 'Data access policy for image collection',
      policy: JSON.stringify([
        {
          Description: "Allow Lambda function to access the collection",
          Rules: [
            {
              ResourceType: 'index',
              Resource: ['index/image-collection/*'],
              Permission: [
                'aoss:CreateIndex',
                'aoss:DeleteIndex',
                'aoss:UpdateIndex',
                'aoss:DescribeIndex',
                'aoss:ReadDocument',
                'aoss:WriteDocument',
              ],
            },
            {
              ResourceType: 'collection',
              Resource: ['collection/image-collection'],
              Permission: [
                'aoss:CreateCollectionItems',
                'aoss:DeleteCollectionItems',
                'aoss:UpdateCollectionItems',
                'aoss:DescribeCollectionItems',
              ],
            },
          ],
          Principal: [imageProcessingFunction.role!.roleArn],
        },
      ]),
    });

    // Create OpenSearch Serverless network policy
    const networkPolicy = new opensearchserverless.CfnSecurityPolicy(this, 'CollectionNetworkPolicy', {
      name: 'image-collection-network-policy',
      type: 'network',
      description: 'Network policy for image collection',
      policy: JSON.stringify([
        {
          Rules: [
            {
              ResourceType: 'collection',
              Resource: ['collection/image-collection'],
            },
          ],
          AllowFromPublic: true,
        },
      ]),
    });

    // Grant Lambda permissions
    imageBucket.grantReadWrite(imageProcessingFunction);
    imageProcessingFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: ['*'],
    }));
    imageProcessingFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'aoss:CreateIndex',
        'aoss:DeleteIndex',
        'aoss:UpdateIndex',
        'aoss:DescribeIndex',
        'aoss:ReadDocument',
        'aoss:WriteDocument',
        'aoss:CreateCollectionItems',
        'aoss:DeleteCollectionItems',
        'aoss:UpdateCollectionItems',
        'aoss:DescribeCollectionItems',
        'aoss:SearchCollectionItems',
      ],
      resources: [collection.attrArn],
    }));

    // Create API Gateway
    const api = new apigateway.RestApi(this, 'ImageProcessingApi', {
      restApiName: 'Image Processing Service',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
      },
    });

    // Create API resources and methods with AuthorizationType.NONE
    const imagesResource = api.root.addResource('images');
    
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
