from typing import List, Dict, Union
from fastapi import HTTPException
from .embedding_generator import EmbeddingGenerator
from .opensearch_client import OpenSearchClient
from PIL import Image
import io

class ImageRetrieve:
    def __init__(self, embedding_generator: EmbeddingGenerator, opensearch_client: OpenSearchClient):
        self.embedding_generator = embedding_generator
        self.opensearch_client = opensearch_client

    def search_by_text(self, query_text: str, k: int = 5) -> List[Dict]:
        """
        Search images using text query
        
        Args:
            query_text (str): Text query to search with
            k (int): Number of results to return
            
        Returns:
            List[Dict]: List of matching images with their metadata
        """
        try:
            # Generate embedding for the query text
            embedding = self.embedding_generator.generate_embedding(query_text, mode='text')
            
            # Search OpenSearch using the embedding
            results = self.opensearch_client.query_opensearch(embedding, k)
            
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in text search: {str(e)}")

    def search_by_image(self, image_bytes: bytes, k: int = 5) -> List[Dict]:
        """
        Search images using an image query
        
        Args:
            image_bytes (bytes): Binary image data to search with
            k (int): Number of results to return
            
        Returns:
            List[Dict]: List of matching images with their metadata
        """
        try:
            # Validate image
            try:
                image = Image.open(io.BytesIO(image_bytes))
                image.verify()  # Verify it's a valid image
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid image file")

            # Generate embedding for the query image
            embedding = self.embedding_generator.generate_embedding(image_bytes, mode='image')
            
            # Search OpenSearch using the embedding
            results = self.opensearch_client.query_opensearch(embedding, k)
            
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in image search: {str(e)}")

    def search(self, query: Union[str, bytes], k: int = 5, mode: str = 'text') -> List[Dict]:
        """
        Unified search method that supports both text and image queries
        
        Args:
            query (Union[str, bytes]): Text string or image bytes to search with
            k (int): Number of results to return
            mode (str): Search mode - 'text' or 'image'
            
        Returns:
            List[Dict]: List of matching images with their metadata
        """
        if mode == 'text':
            if not isinstance(query, str):
                raise HTTPException(status_code=400, detail="Text query must be a string")
            return self.search_by_text(query, k)
        elif mode == 'image':
            if not isinstance(query, bytes):
                raise HTTPException(status_code=400, detail="Image query must be bytes")
            return self.search_by_image(query, k)
        else:
            raise HTTPException(status_code=400, detail="Invalid search mode. Use 'text' or 'image'")
