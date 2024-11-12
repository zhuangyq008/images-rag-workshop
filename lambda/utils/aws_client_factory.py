import boto3

class AWSClientFactory:
    @staticmethod
    def create_s3_client():
        return boto3.client('s3')

    @staticmethod
    def create_bedrock_runtime_client():
        return boto3.client('bedrock-runtime')

    @staticmethod
    def create_opensearch_client():
        return boto3.client('opensearch')
