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
    s3_folder_prefix: str

class BatchDescnEnrichRequest(BaseModel):
    s3_folder_prefix: str

class CheckBatchJobStateRequery(BaseModel):
    jobArn_list: List[str]