import os
import boto3

class Config:
    # OpenSearch配置
    OPENSEARCH_ENDPOINT = os.getenv('OPENSEARCH_ENDPOINT', '')
    COLLECTION_INDEX_NAME = os.getenv('COLLECTION_INDEX_NAME', 'amazon-products')
    
    # Bedrock配置
    EMVEDDINGMODEL_ID = "amazon.titan-embed-text-v1"
    TEXT_VECTOR_DIMENSION = 1536  # Text embedding dimension
    IMAGE_VECTOR_DIMENSION = 1024  # Image embedding dimension
    
    # AWS配置
    AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
    
    @staticmethod
    def get_aws_session():
        """获取AWS会话"""
        return boto3.Session(region_name=Config.AWS_REGION)
    
    @staticmethod
    def validate_config():
        """验证配置是否完整"""
        if not Config.OPENSEARCH_ENDPOINT:
            raise ValueError("OPENSEARCH_ENDPOINT environment variable is not set")
        
        # 验证AWS凭证
        session = Config.get_aws_session()
        credentials = session.get_credentials()
        if not credentials:
            raise ValueError("AWS credentials not found. Please configure AWS credentials")
