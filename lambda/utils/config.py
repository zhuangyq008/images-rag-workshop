import os
import boto3

class Config:
    BUCKET_NAME = os.environ['BUCKET_NAME']
    DDSTRIBUTION_DOMAIN = os.environ['DDSTRIBUTION_DOMAIN']
    VECTOR_DIMENSION = 1024
    VECTOR_TEXT_DIMENSION = 1024
    OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
    COLLECTION_INDEX_NAME = 'image-index-multi-1024'
    MULTIMODEL_LLM_ID = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
    IMG_DESCN_PROMPT = """
        You will be analyzing an image and extracting its key features, including tags, and providing a brief summary of the image content.

        First, carefully examine the image provided in {$IMAGE}.

        Then, in Markdown format, provide the following:

        1. **Tags**: List the key tags that describe the main elements and subjects in the image.
        2. **Summary**: Write a concise 1-2 sentence summary describing the overall content and meaning of the image.

        Format your response as follows:

        # Image Analysis

        ## Tags
        - Tag 1
        - Tag 2
        - Tag 3

        ## Summary
        A brief 1-2 sentence summary of the image content.

        Provide your response within <result> tags.
    """ 

    @staticmethod
    def get_aws_session():
        return boto3.Session()
