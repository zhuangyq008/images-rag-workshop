import json
import base64
from fastapi import HTTPException
from utils.config import Config
from utils.aws_client_factory import AWSClientFactory
import uuid
import jsonlines
from botocore.exceptions import ClientError

class EmbeddingGenerator:
    def __init__(self, bedrock_runtime_client):
        self.bedrock_runtime = bedrock_runtime_client

    def generate_embedding(self, input_image, input_description):
        if input_image=='':
            body = json.dumps({
                "inputText": input_description,
                "embeddingConfig": {
                    "outputEmbeddingLength": Config.VECTOR_DIMENSION
                }
            })
        elif input_description=='':
            body = json.dumps({
                "inputImage": input_image,
                "embeddingConfig": {
                    "outputEmbeddingLength": Config.VECTOR_DIMENSION
                }
            })
        else:
            body = json.dumps({
                "inputText": input_description,
                "inputImage": input_image,
                "embeddingConfig": {
                    "outputEmbeddingLength": Config.VECTOR_DIMENSION
                }
            })
        model_id = Config.EMVEDDINGMODEL_ID

        try:
            response = self.bedrock_runtime.invoke_model(
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            embedding_json = json.loads(response['body'].read().decode('utf-8'))
            return embedding_json["embedding"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")

    def create_embedding_generator_invocation_job(self, batch_gen_embedding_dict, file_prefix):
        # Initialization: Initialize an S3 client
        s3_client = AWSClientFactory.create_s3_client()
        # Initialization: Initialize a bedrock client
        bedrock_client = AWSClientFactory.create_bedrock_client()
        # Initialization: Invocation job configuration
        embedding_payload_file_name = f"{file_prefix}-embedding.jsonl"
        embeddingGeneratorInputDataConfig=({
            "s3InputDataConfig": {
                "s3Uri": f"s3://{Config.BUCKET_NAME}/INVOCATION-INPUT-NO-IMAGE/{embedding_payload_file_name}"
            }
        })
        embedding_output_folder_name = f"{file_prefix}-embedding/"
        embeddingGeneratorOutputDataConfig=({
            "s3OutputDataConfig": {
                "s3Uri": f"s3://{Config.BUCKET_NAME}/INVOCATION-OUTPUT-NO-IMAGE/{embedding_output_folder_name}"
            }
        })
        try:
            # Construct embedding generation payload
            embedding_gen_batch_inference_data = []
            for recordId in batch_gen_embedding_dict:
                input_image = batch_gen_embedding_dict[recordId]["image_base64"]
                input_description = batch_gen_embedding_dict[recordId]["description"]
                embedding_gen_payload = {
                    "recordId": recordId, 
                    "modelInput": {
                        "inputText": input_description,
                        "inputImage": input_image,
                        "embeddingConfig": {
                            "outputEmbeddingLength": Config.VECTOR_DIMENSION
                        }
                    }
                }
                embedding_gen_batch_inference_data.append(embedding_gen_payload)
            with jsonlines.open(f'/tmp/{embedding_payload_file_name}', 'w') as writer:
                writer.write_all(embedding_gen_batch_inference_data)
                s3_client.upload_file(f'/tmp/{embedding_payload_file_name}', Config.BUCKET_NAME, 'INVOCATION-INPUT-NO-IMAGE/'+embedding_payload_file_name)
            # Create and start invocation job
            uuid = file_prefix.split("-")[0]
            embedding_gen_response = bedrock_client.create_model_invocation_job(
                roleArn=Config.BEDROCK_INVOKE_JOB_ROLE,
                modelId=Config.EMVEDDINGMODEL_ID,
                jobName=f"generate-embedding-batch-job-{uuid}",
                inputDataConfig=embeddingGeneratorInputDataConfig,
                outputDataConfig=embeddingGeneratorOutputDataConfig
            )
            jobArn = embedding_gen_response.get('jobArn')
            return jobArn, f"s3://{Config.BUCKET_NAME}/INVOCATION-OUTPUT-NO-IMAGE/{embedding_output_folder_name}"
        except (ClientError, Exception) as e:
            raise HTTPException(status_code=500, detail=f"Error when creating invocation job: {str(e)}")