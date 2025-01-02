import os
import sys
import base64
from pathlib import Path

# Add lambda directory to Python path
lambda_path = str(Path(__file__).parent.parent)
if lambda_path not in sys.path:
    sys.path.insert(0, lambda_path)

from services.image_rerank import ImageRerank
from testcode.api_client_test import ImageProcessingAPITest
from models.api_response import APIResponse
import json
import json

class ImageRerankTest:
    def __init__(self):
        api_url = os.environ.get('API_URL', 'http://127.0.0.1:8000')
        self.api_client = ImageProcessingAPITest(api_url)
        self.reranker = ImageRerank()

    def test_rerank_with_text_and_image(self, image_path: str):
        """
        Test reranking with both text and image query
        
        Args:
            image_path: Path to the query image file
        """
        # Test query
        query_text = "Former President of the United States"
        
        try:
            # Get initial search results
            search_response = self.api_client.search_by_text_and_image(query_text, image_path)
            
            # Extract items from response data
            if not isinstance(search_response, dict) or 'data' not in search_response:
                print("Error: Unexpected response format")
                return False
                
            search_results = search_response['data']['results']
            # Rerank the results
            reranked_results = self.reranker.rerank(
                items_list=search_results,
                query_text=query_text,
                query_image_base64=self.api_client.encode_image(image_path)
            )
            
            # Print results for comparison
            print("\nOriginal Search Results:")
            for idx, item in enumerate(search_results):
                print(f"{idx + 1}. Score: {item.get('score', 'N/A')}, image key: {item.get('image_path', 'N/A')}")
            
            print("\nReranked Results:")
            for idx, item in enumerate(reranked_results):
                print(f"{idx + 1}. Score: {item.get('score', 'N/A')}, image key: {item.get('image_path', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"Error during reranking test: {e}")
            return False

    def test_rerank_with_text_only(self):
        """
        Test reranking with only text query
        """
        # Test query
        query_text = " a woman's torso wearing a tight-fitting black bodysuit or lingerie piece with thin straps."
        
        try:
            # Get initial search results
            search_response = self.api_client.search_by_text(query_text)
            
            # Extract items from response data
            if not isinstance(search_response, dict) or 'data' not in search_response:
                print("Error: Unexpected response format")
                return False
                
            search_results = search_response['data']['results']
            
            # Rerank the results
            reranked_results = self.reranker.rerank(
                items_list=search_results,
                query_text=query_text
            )
            
            # Print results for comparison
            print("\nOriginal Search Results (Text Only):")
            for idx, item in enumerate(search_results):
                print(f"{idx + 1}. Score: {item.get('score', 'N/A')}, image key: {item.get('image_path', 'N/A')}")
            
            print("\nReranked Results (Text Only):")
            for idx, item in enumerate(reranked_results):
                print(f"{idx + 1}. Score: {item.get('score', 'N/A')}, image key: {item.get('image_path', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"Error during text-only reranking test: {e}")
            return False

def main():
    # Create test instance
    test = ImageRerankTest()
    
    # Test image path
    test_image_path = "/Users/enginez/Downloads/us-flag.jpeg"  # Update with actual test image path
    
    # Run tests
    # print("Running rerank test with text and image...")
    text_and_image_result = test.test_rerank_with_text_and_image(test_image_path)
    print(f"Text and image test {'succeeded' if text_and_image_result else 'failed'}\n")
    
    # print("Running rerank test with text only...")
    # text_only_result = test.test_rerank_with_text_only()
    # print(f"Text only test {'succeeded' if text_only_result else 'failed'}")

if __name__ == "__main__":
    main()
