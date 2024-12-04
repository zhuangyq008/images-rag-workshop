import json
import base64
from fastapi import HTTPException
from utils.config import Config

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
