import os
import boto3

class Config:
    BUCKET_NAME = os.environ['BUCKET_NAME']
    COLLECTION_NAME = os.environ['COLLECTION_NAME']
    VECTOR_DIMENSION = 1024
    OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']

    @staticmethod
    def get_aws_session():
        return boto3.Session()
