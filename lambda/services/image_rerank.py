import json
import boto3
from utils.image_combiner import ImageCombiner
from utils.config import Config
import base64
from PIL import Image
from io import BytesIO
from typing import List, Dict, Optional
import uuid
from utils.config import Config

class ImageRerank:
    def __init__(self):
        session = Config.get_aws_session()
        region = session.region_name
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=region
        )
        self.s3 = boto3.client('s3')
        self.image_combiner = ImageCombiner()

    def _encode_image(self, image_bytes):
        return base64.b64encode(image_bytes).decode('utf-8')

    def _get_image_from_s3(self, object_key: str) -> Image.Image:
        """
        Retrieve an image from S3 and return it as a PIL Image object.
        
        Args:
            object_key: S3 object key
            
        Returns:
            PIL Image object
        """
        try:
            response = self.s3.get_object(Bucket=Config.BUCKET_NAME, Key=object_key)
            image_bytes = response['Body'].read()
            return Image.open(BytesIO(image_bytes))
        except Exception as e:
            print(f"Error retrieving image from S3: {e}")
            raise

    def _call_claude(self, prompt, image_base64):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        response = self.bedrock.invoke_model(
            modelId=Config.MULTIMODEL_LLM_ID,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']

    def rerank(self, 
               items_list: List[Dict], 
               query_text: str,
               query_image_base64: Optional[str] = None) -> List[Dict]:
        """
        Rerank items based on text query and optional image query.
        
        Args:
            items_list: List of dicts containing id, score, description, image_path
            query_text: Text query from user (required)
            query_image_base64: Optional query image as base64 encoded string
        
        Returns:
            Reranked list of items
        """
        # Convert image paths to S3 URIs and get Image objects
        images = []
        for item in items_list:
            # Convert relative path to S3 URI
            image_path = item['image_path']
            if not image_path.startswith('s3://'):
                s3_uri = f"s3://{Config.BUCKET_NAME}/{image_path}"
                item['image_path'] = s3_uri
            
            # Get Image object from S3
            object_key = image_path.replace(f"s3://{Config.BUCKET_NAME}/", "") if image_path.startswith('s3://') else image_path
            try:
                image = self._get_image_from_s3(object_key)
                images.append(image)
            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                return items_list  # Return original list if image processing fails
        
        # Create combined grid image from retrieved images
        grid_image = self.image_combiner.combine_images(images)
        
        # Process query image if provided
        if query_image_base64:
            query_image_bytes = base64.b64decode(query_image_base64)
            query_pil_image = Image.open(BytesIO(query_image_bytes))
            combined_image = self.image_combiner.combine_two_images_horizontally(query_pil_image, grid_image)
        else:
            combined_image = grid_image
        
        # Convert combined image to bytes
        combined_bytes = BytesIO()
        combined_image.save(combined_bytes, format='PNG')
        combined_bytes = combined_bytes.getvalue()
        # save the combined image to s3
        try:
            # generate a uuid for the key
            _key = str(uuid.uuid4())
            result_key = f'image_search_results/{_key}.png'
            self.s3.put_object(
                Bucket=Config.BUCKET_NAME,
                # set key to uuid prefix
                Key=result_key,
                Body=combined_bytes
            )
            print(f"Combined image saved to S3 successfully. the key = {result_key}")
            
        except Exception as e:
            print(f"Error saving combined image to S3: {e}")

        
        # Encode combined image
        combined_image_base64 = self._encode_image(combined_bytes)
        
        # Format prompt based on whether query image is provided
        if query_image_base64:
            prompt = f"""You are an AI assistant tasked with identifying the cell in an image that best matches a user's query. The image shows two parts: on the left is the query image, and on the right is a grid of numbered cells.

Your goal is to review the user's query ({query_text}) and both images, then identify the cell from the right grid that best matches the query image and text. You should provide your response in JSON format, with the following structure:

[
  {{
    "imageIndexNo": "the index number of the matching cell",
    "reason": "a brief explanation of why this cell is the best match"
  }}
]

To accomplish this task:

1. Carefully review the user's query ({query_text}) and the query image on the left.
2. Examine the grid on the right and identify the cell that best matches based on visual features and the query.
3. Determine the index number of the matching cell.
4. Write a brief explanation of why this cell is the best match.
5. Format your response in the JSON structure specified above.

Be as specific and accurate as possible in your response. If you are unable to identify a clear match, explain why in your response."""
        else:
            prompt = f"""You are an AI assistant tasked with identifying the cell in an image that best matches a user's query. The image shows a grid of numbered cells.

Your goal is to review the user's query ({query_text}) and identify the cell that best matches this description. You should provide your response in JSON format, with the following structure:

[
  {{
    "imageIndexNo": "the index number of the matching cell",
    "reason": "a brief explanation of why this cell is the best match for the query"
  }}
]

To accomplish this task:

1. Carefully review the user's query: {query_text}
2. Examine each cell in the grid.
3. Identify the cell that best matches the query based on visual features and the description.
4. Determine the index number of the matching cell.
5. Write a brief explanation of why this cell best matches the query.

Be as specific and accurate as possible in your response. If you are unable to identify a clear match, explain why in your response."""

        # Get response from Claude
        response = self._call_claude(prompt, combined_image_base64)
        
        try:
            # Parse Claude's response
            print(f"Claude's response: {response}")
            matches = json.loads(response)
            # Rerank items based on Claude's response
            reranked_items = []
            matched_indices = [int(match['imageIndexNo']) for match in matches]
            # Add matched items first
            for idx in matched_indices:
                if 0 <= idx - 1 < len(items_list):  # Subtract 1 since display indices start at 1
                    reranked_items.append(items_list[idx - 1])
            
            # Add remaining items
            for i, item in enumerate(items_list):
                if i + 1 not in matched_indices:  # Add 1 to match display indices
                    reranked_items.append(item)
                    
            return reranked_items
            
        except json.JSONDecodeError:
            # If response parsing fails, return original list
            print("Failed to parse Claude's response. Returning original list.")
            return items_list
