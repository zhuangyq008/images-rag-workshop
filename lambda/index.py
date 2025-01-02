import copy
import base64
import uuid
import logging
import datetime
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import json
import jsonlines

from models.api_response import APIResponse
from models.request_models import ImageUploadRequest, ImageUpdateRequest, ImageSearchRequest, BatchUploadRequest, BatchDescnEnrichRequest, CheckBatchJobStateRequest, BatchEmbeddingRequest
from utils.config import Config
from utils.aws_client_factory import AWSClientFactory
from utils.get_image_mime_type import get_image_mime_type
from utils.exceptions import (
    ImageProcessingError,
    ImageUploadError,
    ImageNotFoundError,
    InvalidRequestError,
    OpenSearchError
)
from services.opensearch_client import OpenSearchClient
from services.embedding_generator import EmbeddingGenerator
from services.image_retrieve import ImageRetrieve
from services.img_descn_generator import enrich_image_desc, description_generator_invocation_job
from services.image_rerank import ImageRerank

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# FastAPI app
app = FastAPI(title="Image Processing API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Initialize clients
s3_client = AWSClientFactory.create_s3_client()
bedrock_client = AWSClientFactory.create_bedrock_runtime_client()
opensearch_client = OpenSearchClient()
embedding_generator = EmbeddingGenerator(bedrock_client)
image_retrieve = ImageRetrieve(embedding_generator, opensearch_client)

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
    return APIResponse.error(
        code=exc.status_code,
        message=exc.detail["message"],
        data={
            "error_code": exc.detail["error_code"],
            "details": exc.detail["details"]
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail}")
    return APIResponse.error(
        code=exc.status_code,
        message=str(exc.detail)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return APIResponse.error(
        code=500,
        message="Internal server error",
        data={"error": str(exc)}
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
        
        # Get description
        description = ''
        if request.description == '':
            # Generate description
            try:
                logger.info("Starting description generation")
                description = enrich_image_desc(request.image)
                logger.info("Successfully generated description")
            except Exception as e:
                logger.error(f"Failed to generate description: {str(e)}")
                raise ImageUploadError("Failed to generate description", {"detail": str(e)})
        else:
            description = request.description
        # Generate embedding
        try:
            logger.info("Starting embedding generation")
            embedding = embedding_generator.generate_embedding(request.image, description)
            logger.info("Successfully generated image embedding")
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(f"Failed to generate image embedding: {str(e)}")
            print(tb_str)
            raise ImageUploadError("Failed to generate image embedding", {"detail": str(e)})

        # Index in OpenSearch
        try:
            dt = datetime.datetime.now().isoformat()
            document = {
                    'id': image_id,
                    'description': description,
                    'embedding': embedding,
                    'createtime': dt,
                    'image_path': s3_key
            }                           
            logger.info(f"Indexing document in OpenSearch: {image_id}")
            _ret = opensearch_client.index_document(document)
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

@app.post("/images/batch-upload")
async def batch_upload(request: BatchUploadRequest) -> APIResponse:
    logger.info("Starting batch upload process")
    try:
        jobArn_list = request.batch_embedding_output["jobArn_list"]
        error_list = [] # To store images without generated description
        for jobArn in jobArn_list:
            # One job is one batch
            documents = []
            job_output = request.batch_embedding_output[jobArn]
            output_directory = job_output["output"]
            image_s3_uris_path = job_output["image_s3_uris"]
            # Get batch inference output: output_json_list
            s3_folder_prefix = output_directory.replace("s3://"+Config.BUCKET_NAME+"/","")
            s3_folder_prefix = s3_folder_prefix + jobArn.split("/")[-1] + "/"
            s3_key = s3_folder_prefix + output_directory.split("/")[-2] + ".jsonl.out"
            response = s3_client.get_object(Bucket=Config.BUCKET_NAME,Key=s3_key)
            file_content = response["Body"].read().decode("utf-8")
            file_content_list = file_content.split("\n")[:-1]
            output_json_list = []
            for content in file_content_list:
                output_json_list.append(json.loads(content))
            # Get image s3 uris
            s3_key = image_s3_uris_path.replace("s3://"+Config.BUCKET_NAME+"/","")
            response = s3_client.get_object(Bucket=Config.BUCKET_NAME,Key=s3_key)
            file_content = response["Body"].read().decode("utf-8")
            s3_uris_json = json.loads(file_content)
            # Construct documents
            image_num = 0
            if len(s3_uris_json) != len(output_json_list):
                raise HTTPException(status_code=500, detail=f"The number of s3 uris is {len(s3_uris_json)} while there are {len(output_json_list)} outputs.")
            else:
                image_num = len(output_json_list)
                logger.info(f"Bulk uploading {str(image_num)} images.")
            for i in range(image_num):
                if "error" in output_json_list[i]:
                    error_list.append(s3_uris_json[output_json_list[i]["recordId"]])
                    continue
                dt = datetime.datetime.now().isoformat()
                document = {
                    'description': output_json_list[i]["modelInput"]["inputText"],
                    'embedding': output_json_list[i]["modelOutput"]['embedding'],
                    'createtime': dt,
                    'image_path': s3_uris_json[output_json_list[i]["recordId"]]
                }
                documents.append(document)
            # bulk index
            try:
                logger.info("Starting bulk indexing")
                response = opensearch_client.bulk_upload(documents)
                logger.info(response)
                logger.info(f"Successfully bulk index {str(len(documents))} images in batch {jobArn}")
            except Exception as e:
                logger.error(f"Batch upload failed in OpenSearch: {str(e)}")
                raise OpenSearchError("Batch upload failed in OpenSearch:", {"detail": str(e)})

        return APIResponse.success(
            message="Batch upload completed successfully",
            data = {
                "number of error images": len(error_list),
                "error images (error occurred when generating description)": error_list
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in batch upload: {str(e)}")


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

        if request.query_image and not request.query_text :
            try:
                logger.info("Processing image-based search")

                results = image_retrieve.search_by_image(request.query_image, request.k)
                logger.info("Successfully completed image-based search")
            except Exception as e:
                logger.error(f"Failed to process query image: {str(e)}")
                tb_str = traceback.format_exc()
                print(tb_str)
                raise InvalidRequestError("Invalid image data format", {"detail": str(e)})
        elif request.query_text and not request.query_image:
            logger.info("Processing text-based search")
            results = image_retrieve.search_by_text(request.query_text, request.k)
            logger.info("Successfully completed text-based search")
        elif request.query_image and request.query_text:
             logger.info("Processing text-image-combined search")
             results = image_retrieve.search_by_text_and_image(request.query_text, request.query_image, request.k)

        logger.info(f"Search completed successfully, found {len(results)} results")
        # reranking
        if request.rerank==True:
            if not request.query_text:
                logger.error("When using reranking, query text must be provided.")
                raise InvalidRequestError("Query text empty.", {"detail": "When using reranking, query text must be provided."})
            logger.info("Search with reranking")
            reranker = ImageRerank()
            reranked_results = reranker.rerank(
                    items_list=results,
                    query_text=request.query_text,
                    query_image_base64=request.query_image
                )
            bucket_prefix = f"s3://{Config.BUCKET_NAME}/"
            results = [{**result, "image_path": f"{Config.DDSTRIBUTION_DOMAIN}{result['image_path'].replace(bucket_prefix, '')}"} for result in reranked_results]
            sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
            return APIResponse.success(
                message="Search completed successfully",
                data={"results": sorted_results}
            )
        else:
            logger.info(f"type of rerank {type(request.rerank)}")
            logger.info("Search without reranking")
            bucket_prefix = f"s3://{Config.BUCKET_NAME}"
            results = [{**result, "image_path": f"{Config.DDSTRIBUTION_DOMAIN}{result['image_path'].replace(bucket_prefix, '')}"} for result in results]
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

@app.post("/images/batch-descn-enrich")
async def batch_descn_enrich(request: BatchDescnEnrichRequest) -> APIResponse:
    logger.info("Starting batch description enrichment process")
    try:
        # Initialization: Create a reusable Paginator
        paginator = s3_client.get_paginator('list_objects_v2')
        first = True
        next_token = None
        response_data = {}
        jobArn_list = []
        batch_num = 0
        pre_batch_base64_list = {}

        while first or next_token:
            logger.info(f"batch {str(batch_num)}")
            first = False
            # Create a PageIterator from the Paginator
            page_iterator = paginator.paginate(
                Bucket=Config.BUCKET_NAME,
                Prefix=request.s3_folder_prefix,
                PaginationConfig={'PageSize': request.batch_size,'StartingToken':next_token}
            )

            # A page is one batch
            for page in page_iterator:
                # Get next token
                is_truncated = page['IsTruncated']
                if is_truncated:
                    next_token = page['NextContinuationToken']
                else:
                    next_token = None
                # Get batch image data
                image_base64_list = {}
                for obj in page['Contents']:
                    # Get image base64
                    s3_key = obj['Key']
                    response = s3_client.get_object(Bucket=Config.BUCKET_NAME,Key=s3_key)
                    streaming_body = response.get("Body").read()
                    image_base64 = base64.b64encode(streaming_body).decode('utf-8')
                    s3_uri = f"s3://{Config.BUCKET_NAME}/{s3_key}"
                    # Get MIME type
                    with open('/tmp/temp_image', 'wb') as f:
                        s3_client.download_fileobj(Config.BUCKET_NAME, s3_key, f)
                    mime_type = get_image_mime_type('/tmp/temp_image')
                    # logger.info(f"MIME type: {mime_type}")
                    image_base64_list[s3_uri] = {"base64": image_base64, "mime_type": mime_type}
                
                if len(pre_batch_base64_list) == 0:
                    pre_batch_base64_list = copy.deepcopy(image_base64_list)
                    continue
                if len(image_base64_list) < 100:
                    pre_batch_base64_list.update(image_base64_list)
                    image_base64_list = {}
                # Batch generate description
                jobArn, output_s3_uri, s3_uris = description_generator_invocation_job(pre_batch_base64_list, batch_num)
                # Update batch_num
                batch_num += 1
                # Construct response data
                response_data[jobArn] = {"output": output_s3_uri,"image_s3_uris": s3_uris}
                jobArn_list.append(jobArn)
                # Update previous base64 list
                pre_batch_base64_list = copy.deepcopy(image_base64_list)
            # for page in paginator
        # while first or next_token
        # Handle the last batch
        if len(pre_batch_base64_list) > 100:
            if len(pre_batch_base64_list) < 100:
                raise HTTPException(status_code=500, detail=f"At least 100 images for a batch, got {str(len(pre_batch_base64_list))} instead. Fail to use batch generation.")
            else:
                # Batch generate description
                jobArn, output_s3_uri, s3_uris = description_generator_invocation_job(pre_batch_base64_list, batch_num)
                # Construct response data
                response_data[jobArn] = {"output": output_s3_uri,"image_s3_uris": s3_uris}
                jobArn_list.append(jobArn)

        response_data["jobArn_list"] = jobArn_list
        
        return APIResponse.success(
            message="Batch description enrichment successfully started",
            data=response_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in batch job creation: {str(e)}")

@app.post("/images/batch-embedding-gen")
async def batch_embedding_generation(request: BatchEmbeddingRequest) -> APIResponse:
    try:
        response_data = {}
        if request.generated_descn:
            if request.batch_descn_output == {}:
                raise HTTPException(status_code=500, detail=f"The parameter descn_output_file_list must not be empty when generated_descn is true.")
        else:
            if request.s3_folder_prefix == "":
                raise HTTPException(status_code=500, detail=f"The parameter s3_folder_prefix must not be empty when generated_descn is false.")
        if request.generated_descn:
            jobArn_list = request.batch_descn_output["jobArn_list"]
            embedding_jobArn_list = []
            # One job is one batch
            for jobArn in jobArn_list:
                output_directory = request.batch_descn_output[jobArn]["output"]
                # Get batch inference output: output_json_list
                s3_folder_prefix = output_directory.replace("s3://"+Config.BUCKET_NAME+"/","")
                s3_folder_prefix = s3_folder_prefix + jobArn.split("/")[-1] + "/"
                s3_key = s3_folder_prefix + output_directory.split("/")[-2] + ".jsonl.out"
                response = s3_client.get_object(Bucket=Config.BUCKET_NAME,Key=s3_key)
                file_content = response["Body"].read().decode("utf-8")
                file_content_list = file_content.split("\n")[:-1]
                output_json_list = []
                for content in file_content_list:
                    output_json_list.append(json.loads(content))
                # Construct batch generate embedding dict
                batch_gen_embedding_dict = {}
                for output_json in output_json_list:
                    if "error" in output_json:
                        continue
                    batch_gen_embedding_dict[output_json["recordId"]] = {
                        "image_base64": output_json["modelInput"]["messages"][0]["content"][0]["image"]["source"]["bytes"],
                        "description": output_json["modelOutput"]["output"]["message"]["content"][0]["text"]
                    }
                # create generation invocation job
                file_prefix = output_directory.split("/")[-2].replace("-descn","")
                embedding_jobArn, output_s3_uri = embedding_generator.create_embedding_generator_invocation_job(batch_gen_embedding_dict,file_prefix)
                response_data[embedding_jobArn] = {"output": output_s3_uri, "image_s3_uris": request.batch_descn_output[jobArn]["image_s3_uris"]}
                embedding_jobArn_list.append(embedding_jobArn)
            response_data["jobArn_list"] = embedding_jobArn_list
        return APIResponse.success(
            message="Batch embedding generation successfully started",
            data=response_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in batch job creation: {str(e)}")

@app.post("/check-batch-job-state")
async def batch_descn_enrich(request: CheckBatchJobStateRequest) -> APIResponse:
    logger.info("Check batch job state")
    try:
        respond_data = {}
        client = AWSClientFactory.create_bedrock_client()
        for jobArn in request.jobArn_list:
            status = client.get_model_invocation_job(jobIdentifier=jobArn)['status']
            respond_data[jobArn] = status
        
        return APIResponse.success(
            message="Batch description enrichment successfully started",
            data=respond_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in batch job creation: {str(e)}")

# Lambda handler
# handler = Mangum(app)
