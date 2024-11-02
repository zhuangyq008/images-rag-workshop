import json
import base64
from fastapi import HTTPException
from utils.config import Config

class EmbeddingGenerator:
    def __init__(self, bedrock_runtime_client):
        self.bedrock_runtime = bedrock_runtime_client

    def generate_embedding(self, data, mode):
        if mode == 'text':
            body = json.dumps({
                "inputText": data
            })
            model_id = "amazon.titan-embed-text-v2:0"
        elif mode == 'image':
            body = json.dumps({
                "inputImage": data,
                "embeddingConfig": {
                    "outputEmbeddingLength": Config.VECTOR_DIMENSION
                }
            })
            model_id = "amazon.titan-embed-image-v1"
        else:
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'text' or 'image'.")

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
