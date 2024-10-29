import boto3

from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

outputEmbeddingLength = 1024

client = boto3.client('opensearchserverless')
service = 'aoss'
region = 'us-east-1'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
collection_name = "image-collection"

host = 'qh8bnb24uqmd1bfny6h2.us-east-1.aoss.amazonaws.com'
OSSclient = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)
def create_index(index, outputEmbeddingLength) :
    if not OSSclient.indices.exists(index):
        settings = {
            "settings": {
                "index": {
                    "knn": True,
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "text"},
                    "name": {"type": "text"},
                    "color": {"type": "text"},
                    "brand": {"type": "text"},
                    "description": {"type": "text"},
                    "createtime": {"type": "text"},
                    "image_path":{"type": "text"},
                    "vector_field": {
                        "type": "knn_vector",
                        "dimension": outputEmbeddingLength,
                    },
                }
            },
        }
        res = OSSclient.indices.create(index, body=settings)
        print(res)
index_name = "retail-dataset-{}".format(outputEmbeddingLength)
create_index(index_name, outputEmbeddingLength)