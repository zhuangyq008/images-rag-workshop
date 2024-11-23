from config import Config
from opensearch_client import OpenSearchClient
import boto3

def main():
    try:
        # 验证配置
        Config.validate_config()
        
        # 初始化AWS会话
        aws_session = Config.get_aws_session()
        
        # 初始化OpenSearch客户端
        opensearch_client = OpenSearchClient(aws_session)
        
        # 删除索引
        opensearch_client.delete_index()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
