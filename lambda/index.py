import json
import base64
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from mangum import Mangum

from models.api_response import APIResponse
from models.request_models import ImageUploadRequest, ImageUpdateRequest, ImageSearchRequest
from utils.config import Config
from utils.aws_client_factory import AWSClientFactory
from services.opensearch_client import OpenSearchClient
from services.embedding_generator import EmbeddingGenerator

# FastAPI app
app = FastAPI(title="Image Processing API")

# Initialize clients
s3_client = AWSClientFactory.create_s3_client()
bedrock_client = AWSClientFactory.create_bedrock_runtime_client()
opensearch_client = OpenSearchClient()
embedding_generator = EmbeddingGenerator(bedrock_client)

# Ensure OpenSearch index exists
opensearch_client.ensure_index_exists()

@app.post("/images")
async def upload_image(request: ImageUploadRequest) -> APIResponse:
    try:
        image_data = base64.b64decode(request.image)
        image_id = str(uuid.uuid4())
        s3_key = f'images/{image_id}'

        # Upload to S3
        s3_client.put_object(
            Bucket=Config.BUCKET_NAME,
            Key=s3_key,
            Body=image_data,
            ContentType='image/jpeg'
        )

        # Generate embedding
        embedding = embedding_generator.generate_embedding(image_data, 'image')

        # Index in OpenSearch
        document = {
            'id': image_id,
            'description': request.description,
            'tags': request.tags,
            'vector_field': embedding,
            's3_key': s3_key
        }
        opensearch_client.index_document(document)

        return APIResponse(
            code=200,
            message="Image uploaded successfully",
            data={"image_id": image_id},
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/images")
async def update_image(request: ImageUpdateRequest) -> APIResponse:
    try:
        opensearch_client.update_document(
            request.image_id,
            request.description,
            request.tags
        )

        return APIResponse(
            code=200,
            message="Image metadata updated successfully",
            data={"image_id": request.image_id},
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/images/search")
async def search_images(request: ImageSearchRequest) -> APIResponse:
    try:
        if request.query_image:
            query_image = base64.b64decode(request.query_image)
            query_embedding = embedding_generator.generate_embedding(query_image, 'image')
        elif request.query_text:
            query_embedding = embedding_generator.generate_embedding(request.query_text, 'text')
        else:
            raise HTTPException(status_code=400, detail="Either query_image or query_text must be provided")

        results = opensearch_client.query_opensearch(query_embedding, request.k)

        return APIResponse(
            code=200,
            message="Search completed successfully",
            data={"results": results},
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/images/{image_id}")
async def delete_image(image_id: str) -> APIResponse:
    try:
        # Delete from OpenSearch
        opensearch_client.delete_document(image_id)

        # Delete from S3
        s3_client.delete_object(
            Bucket=Config.BUCKET_NAME,
            Key=f'images/{image_id}'
        )

        return APIResponse(
            code=200,
            message="Image deleted successfully",
            data={"image_id": image_id},
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Lambda handler
handler = Mangum(app)
