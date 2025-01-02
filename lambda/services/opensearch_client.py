from fastapi import HTTPException
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from utils.config import Config
import json

class OpenSearchClient:
    def __init__(self):
        session = Config.get_aws_session()
        credentials = session.get_credentials()
        region = session.region_name
        service = 'es'
        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            service,
            session_token=credentials.token
        )

        self.client = OpenSearch(
            hosts=[{'host': Config.OPENSEARCH_ENDPOINT.replace('https://', ''), 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=300
        )

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
                        "id": {"type": "text"},
                        "name": {"type": "text"},
                        "description": {"type": "text"},
                        "createtime": {"type": "text"},
                        "image_path":{"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": Config.VECTOR_DIMENSION,
                        }                  
                    }
                },
            }
            try:
                self.client.indices.create(index=index_name, body=settings)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error creating index: {str(e)}")

    def index_document(self, document):
        index_name = Config.COLLECTION_INDEX_NAME
        try:
            print(f"Indexing document: {document['id']}")
            response = self.client.index(
                index=index_name,
                body=document
            )
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error indexing document: {str(e)}")
        
    def bulk_upload(self, documents):
        try:
            action = json.dumps({ 'index': { '_index': Config.COLLECTION_INDEX_NAME} })
            body_ = ''
            for document in documents:
                body_ = body_ + action + "\n" + json.dumps(document) + "\n"
            response = self.client.bulk(
                index = Config.COLLECTION_INDEX_NAME,
                body = body_
            )
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error indexing document: {str(e)}")
    
    def update_document(self, image_id, description, tags):
        index_name = Config.COLLECTION_INDEX_NAME
        try:
            response = self.client.update(
                index=index_name,
                id=image_id,
                body={
                    "doc": {
                        'description': description,
                        'tags': tags
                    }
                }
            )
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating document: {str(e)}")

    def delete_document(self, image_id):
        index_name = Config.COLLECTION_INDEX_NAME
        try:
            response = self.client.delete(
                index=index_name,
                id=image_id
            )
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
    # default type is image embedding
    def query(self, embedding, k):
        index_name = Config.COLLECTION_INDEX_NAME
        query = {
            'size': k,
            'query': {
                'knn': {
                    'embedding': {
                        'vector': embedding,
                        'k': k
                    }
                }
            }
        }
        try:
            response = self.client.search(
                index=index_name,
                body=query
            )
            hits = response['hits']['hits']
            return [
                {
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'description': hit['_source']['description'],
                    'image_path': hit['_source']['image_path']
                }
                for hit in hits
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error querying OpenSearch: {str(e)}")