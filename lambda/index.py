import json
import base64
import uuid
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from mangum import Mangum

from models.api_response import APIResponse
from models.request_models import ImageUploadRequest, ImageUpdateRequest, ImageSearchRequest
from utils.config import Config
from utils.aws_client_factory import AWSClientFactory
from utils.exceptions import (
    ImageProcessingError,
    ImageUploadError,
    ImageNotFoundError,
    InvalidRequestError,
    OpenSearchError
)
from services.opensearch_client import OpenSearchClient
from services.embedding_generator import EmbeddingGenerator

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# FastAPI app
app = FastAPI(title="Image Processing API")

# Initialize clients
s3_client = AWSClientFactory.create_s3_client()
bedrock_client = AWSClientFactory.create_bedrock_runtime_client()
opensearch_client = OpenSearchClient()
embedding_generator = EmbeddingGenerator(bedrock_client)

logger.info("Initializing application and clients")

# Ensure OpenSearch index exists
try:
    opensearch_client.ensure_index_exists()
    logger.info("OpenSearch index check completed")
except Exception as e:
    logger.error(f"Failed to ensure OpenSearch index exists: {str(e)}")
    raise

@app.exception_handler(ImageProcessingError)
async def image_processing_exception_handler(request: Request, exc: ImageProcessingError):
    logger.error(f"ImageProcessingError: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse.error(
            code=exc.status_code,
            message=exc.detail["message"],
            data={
                "error_code": exc.detail["error_code"],
                "details": exc.detail["details"]
            }
        ).dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse.error(
            code=exc.status_code,
            message=str(exc.detail)
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=APIResponse.error(
            code=500,
            message="Internal server error",
            data={"error": str(exc)}
        ).dict()
    )

@app.post("/images")
async def upload_image(request: ImageUploadRequest) -> APIResponse:
    logger.info("Starting image upload process")
    try:
        # Validate image data
        try:
            image_data = base64.b64decode(request.image)
            logger.info("Image data successfully decoded")
        except Exception as e:
            logger.error(f"Failed to decode image data: {str(e)}")
            raise ImageUploadError("Invalid image data format", {"detail": str(e)})

        image_id = str(uuid.uuid4())
        s3_key = f'images/{image_id}'
        logger.info(f"Generated image ID: {image_id}")

        # Upload to S3
        try:
            s3_client.put_object(
                Bucket=Config.BUCKET_NAME,
                Key=s3_key,
                Body=image_data,
                ContentType='image/jpeg'
            )
            logger.info(f"Successfully uploaded image to S3: {s3_key}")
        except Exception as e:
            logger.error(f"Failed to upload image to S3: {str(e)}")
            raise ImageUploadError("Failed to upload image to S3", {"detail": str(e)})

        # Generate embedding
        try:
            logger.info("Starting embedding generation")
            embedding = embedding_generator.generate_embedding(image_data, 'image')
            logger.info("Successfully generated image embedding")
        except Exception as e:
            logger.error(f"Failed to generate image embedding: {str(e)}")
            raise ImageUploadError("Failed to generate image embedding", {"detail": str(e)})

        # Index in OpenSearch
        try:
            document = {
                'id': image_id,
                'description': request.description,
                'tags': request.tags,
                'vector_field': embedding,
                's3_key': s3_key
            }
            logger.info(f"Indexing document in OpenSearch: {image_id}")
            opensearch_client.index_document(document)
            logger.info(f"Successfully indexed document in OpenSearch: {image_id}")
        except Exception as e:
            logger.error(f"Failed to index document in OpenSearch: {str(e)}")
            # Clean up S3 object if OpenSearch indexing fails
            try:
                logger.info(f"Attempting to clean up S3 object after failed indexing: {s3_key}")
                s3_client.delete_object(Bucket=Config.BUCKET_NAME, Key=s3_key)
                logger.info(f"Successfully cleaned up S3 object: {s3_key}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up S3 object: {str(cleanup_error)}")
            raise OpenSearchError("Failed to index image metadata", {"detail": str(e)})

        logger.info(f"Image upload process completed successfully: {image_id}")
        return APIResponse.success(
            message="Image uploaded successfully",
            data={"image_id": image_id}
        )
    except ImageProcessingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during image upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/images")
async def update_image(request: ImageUpdateRequest) -> APIResponse:
    logger.info(f"Starting image update process for ID: {request.image_id}")
    try:
        try:
            logger.info(f"Updating document in OpenSearch: {request.image_id}")
            opensearch_client.update_document(
                request.image_id,
                request.description,
                request.tags
            )
            logger.info(f"Successfully updated document in OpenSearch: {request.image_id}")
        except Exception as e:
            logger.error(f"Failed to update document: {str(e)}")
            raise ImageNotFoundError(request.image_id)

        return APIResponse.success(
            message="Image metadata updated successfully",
            data={"image_id": request.image_id}
        )
    except ImageProcessingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during image update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/images/search")
async def search_images(request: ImageSearchRequest) -> APIResponse:
    logger.info("Starting image search process")
    try:
        if not request.query_image and not request.query_text:
            logger.error("Invalid search request: no query provided")
            raise InvalidRequestError(
                "Either query_image or query_text must be provided",
                {"provided_params": {
                    "query_image": bool(request.query_image),
                    "query_text": bool(request.query_text)
                }}
            )

        if request.query_image:
            try:
                logger.info("Processing image-based search")
                query_image = base64.b64decode(request.query_image)
                query_embedding = embedding_generator.generate_embedding(query_image, 'image')
                logger.info("Successfully generated query image embedding")
            except Exception as e:
                logger.error(f"Failed to process query image: {str(e)}")
                raise InvalidRequestError("Invalid image data format", {"detail": str(e)})
        else:
            logger.info("Processing text-based search")
            query_embedding = embedding_generator.generate_embedding(request.query_text, 'text')
            logger.info("Successfully generated query text embedding")

        logger.info("Executing OpenSearch query")
        results = opensearch_client.query_opensearch(query_embedding, request.k)
        logger.info(f"Search completed successfully, found {len(results)} results")

        return APIResponse.success(
            message="Search completed successfully",
            data={"results": results}
        )
    except ImageProcessingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during image search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/images/{image_id}")
async def delete_image(image_id: str) -> APIResponse:
    logger.info(f"Starting image deletion process for ID: {image_id}")
    try:
        # Delete from OpenSearch
        try:
            logger.info(f"Deleting document from OpenSearch: {image_id}")
            opensearch_client.delete_document(image_id)
            logger.info(f"Successfully deleted document from OpenSearch: {image_id}")
        except Exception as e:
            logger.error(f"Failed to delete document from OpenSearch: {str(e)}")
            raise ImageNotFoundError(image_id)

        # Delete from S3
        try:
            s3_key = f'images/{image_id}'
            logger.info(f"Deleting object from S3: {s3_key}")
            s3_client.delete_object(
                Bucket=Config.BUCKET_NAME,
                Key=s3_key
            )
            logger.info(f"Successfully deleted object from S3: {s3_key}")
        except Exception as e:
            logger.error(f"Failed to delete object from S3: {str(e)}")
            raise ImageProcessingError(
                status_code=500,
                error_code="S3_DELETE_ERROR",
                message="Failed to delete image from S3",
                details={"image_id": image_id, "error": str(e)}
            )

        logger.info(f"Image deletion completed successfully: {image_id}")
        return APIResponse.success(
            message="Image deleted successfully",
            data={"image_id": image_id}
        )
    except ImageProcessingError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during image deletion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Lambda handler
handler = Mangum(app)
