from typing import List, Optional
from pydantic import BaseModel

class ImageUploadRequest(BaseModel):
    image: str
    description: Optional[str] = ""
    tags: List[str] = []

class ImageUpdateRequest(BaseModel):
    image_id: str
    description: Optional[str]
    tags: Optional[List[str]]

class ImageSearchRequest(BaseModel):
    query_image: Optional[str]
    query_text: Optional[str]
    rerank: Optional[bool] = False
    k: Optional[int] = 10

class BatchUploadRequest(BaseModel):
    batch_embedding_output: dict

class BatchDescnEnrichRequest(BaseModel):
    s3_folder_prefix: str
    batch_size: Optional[int] = 500

class BatchEmbeddingRequest(BaseModel):
    generated_descn: bool
    batch_descn_output: Optional[dict] = {}
    s3_folder_prefix: Optional[str] = ""

class CheckBatchJobStateRequest(BaseModel):
    jobArn_list: List[str]