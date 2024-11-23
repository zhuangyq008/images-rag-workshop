from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from config import Config
import json
import numpy as np

class OpenSearchClient:
    def __init__(self, aws_session):
        credentials = aws_session.get_credentials()
        region = aws_session.region_name
        service = 'es'
        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            service,
            session_token=credentials.token if hasattr(credentials, 'token') else None
        )

        self.client = OpenSearch(
            hosts=[{'host': Config.OPENSEARCH_ENDPOINT.replace('https://', ''), 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=300
        )

    def delete_index(self):
        """删除索引"""
        index_name = Config.COLLECTION_INDEX_NAME
        if self.client.indices.exists(index=index_name):
            try:
                self.client.indices.delete(index=index_name)
                print(f"Index {index_name} deleted")
            except Exception as e:
                raise Exception(f"Error deleting index: {str(e)}")
        else:
            print(f"Index {index_name} does not exist")

    def ensure_index_exists(self):
        index_name = Config.COLLECTION_INDEX_NAME
        if not self.client.indices.exists(index=index_name):
            settings = {
                "settings": {
                    "index": {
                        "knn": True,
                    }
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "title": {"type": "text"},
                        "main_category": {"type": "keyword"},
                        "categories": {"type": "keyword"},
                        "features": {"type": "text"},
                        "description": {"type": "text"},
                        "price": {"type": "float"},
                        "average_rating": {"type": "float"},
                        "rating_number": {"type": "integer"},
                        "store": {"type": "keyword"},
                        "image_url": {"type": "keyword"},
                        "image_embedding": {
                            "type": "knn_vector",
                            "dimension": 1024,
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 16
                                }
                            }
                        },
                        "description_embedding": {
                            "type": "knn_vector",
                            "dimension": 1536,
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 16
                                }
                            }
                        }
                    }
                }
            }
            try:
                self.client.indices.create(index=index_name, body=settings)
            except Exception as e:
                raise Exception(f"Error creating index: {str(e)}")

    def index_document(self, document):
        index_name = Config.COLLECTION_INDEX_NAME
        try:
            if 'description_embedding' in document:
                embedding = document['description_embedding']
                if len(embedding) != 1536:
                    raise ValueError(f"Description embedding dimension mismatch. Expected 1536, got {len(embedding)}")
                document['description_embedding'] = np.array(embedding, dtype=np.float32).tolist()
            
            if 'image_embedding' in document:
                embedding = document['image_embedding']
                if len(embedding) != 1024:
                    raise ValueError(f"Image embedding dimension mismatch. Expected 1024, got {len(embedding)}")
                document['image_embedding'] = np.array(embedding, dtype=np.float32).tolist()

            document_json = json.dumps(document)
            document = json.loads(document_json)
            
            response = self.client.index(
                index=index_name,
                body=document,
                id=document['id']
            )
            return response
        except Exception as e:
            raise Exception(f"Error indexing document: {str(e)}")
