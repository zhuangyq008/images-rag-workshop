from typing import List, Dict, Union
from fastapi import HTTPException
from .embedding_generator import EmbeddingGenerator
from .opensearch_client import OpenSearchClient
import io
from PIL import Image
from io import BytesIO
import base64

class ImageRetrieve:
    def __init__(self, embedding_generator: EmbeddingGenerator, opensearch_client: OpenSearchClient):
        self.embedding_generator = embedding_generator
        self.opensearch_client = opensearch_client

    def image_resize(self,base64_image_data,width,height):
        try:
            image_data = base64.b64decode(base64_image_data)
            # 将二进制数据转换为 Pillow 支持的 Image 对象
            image = Image.open(BytesIO(image_data))
            # 调整图片大小到 320x320
            resized_image = image.resize((width, height))

            # 将调整后的图片直接转换为 Base64 编码
            buffer = BytesIO()
            resized_image.save(buffer, format=image.format)  # 使用原始格式保存到内存
            resized_base64_data = base64.b64encode(buffer.getvalue()).decode()  # 转为 Base64 字符串
            return resized_base64_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in resize image: {str(e)}")

    def search_by_text(self, query_text: str, k: int = 5) -> List[Dict]:
        try:
            # Generate embedding for the query text
            embedding = self.embedding_generator.generate_embedding(query_text, mode='text')

            # Search OpenSearch using the embedding
            results = self.opensearch_client.query_by_text(embedding, k)
            
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in text search: {str(e)}")

    def search_by_image(self, image_encode, k: int = 5) -> List[Dict]:
        try:
            # Generate embedding for the query image
            image_encode = self.image_resize(image_encode,320,320)
            embedding = self.embedding_generator.generate_embedding(image_encode, mode='image')
            
            # Search OpenSearch using the embedding
            results = self.opensearch_client.query_by_image(embedding, k)
            
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in image search: {str(e)}")
    def search_by_text_and_image(self, query_text: str, image_encode, k: int = 5) -> List[Dict]:
        try:
            # Generate embeddings for the query text and image
            text_embedding = self.embedding_generator.generate_embedding(query_text, mode='text')
            image_encode = self.image_resize(image_encode,320,320)
            image_embedding = self.embedding_generator.generate_embedding(image_encode, mode='image')

            # Search OpenSearch using the embeddings
            results = self.opensearch_client.query_by_text_and_image(text_embedding, image_embedding, k)

            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in text and image search: {str(e)}")


