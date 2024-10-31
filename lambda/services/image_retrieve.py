from typing import List, Dict, Union
from fastapi import HTTPException
from .embedding_generator import EmbeddingGenerator
from .opensearch_client import OpenSearchClient
import io

class ImageRetrieve:
    def __init__(self, embedding_generator: EmbeddingGenerator, opensearch_client: OpenSearchClient):
        self.embedding_generator = embedding_generator
        self.opensearch_client = opensearch_client

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
            image_embedding = self.embedding_generator.generate_embedding(image_encode, mode='image')

            # Search OpenSearch using the embeddings
            results = self.opensearch_client.query_by_text_and_image(text_embedding, image_embedding, k)

            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in text and image search: {str(e)}")


