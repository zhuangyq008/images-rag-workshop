import json
from fastapi import HTTPException
from config import Config

class EmbeddingGenerator:
    def __init__(self, bedrock_runtime_client):
        self.bedrock_runtime = bedrock_runtime_client

    def generate_embedding(self, data, mode):
        if mode == 'text':
            # Text model doesn't accept embeddingConfig
            body = json.dumps({
                "inputText": data
            })
            model_id = Config.EMVEDDINGMODEL_ID
        elif mode == 'image':
            # Image model requires embeddingConfig
            body = json.dumps({
                "inputImage": data,
                "embeddingConfig": {
                    "outputEmbeddingLength": Config.IMAGE_VECTOR_DIMENSION
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
            embedding = embedding_json["embedding"]
            return embedding
        except Exception as e:
            raise Exception(f"Error generating embedding: {str(e)}")
