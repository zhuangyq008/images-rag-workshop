import boto3

from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from PIL import Image
import base64
import json
import os
import uuid
import io
import matplotlib.pyplot as plt
import datetime
import multimodel_test 

outputEmbeddingLength = 1024

client = boto3.client('opensearchserverless')
bedrock_runtime = boto3.client(service_name="bedrock-runtime")
s3_client = boto3.client('s3')
service = 'aoss'
region = 'us-east-1'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
collection_name = "image-collection"
bucket_name = 'imagebucket-284367710968-us-east-1'
index_name = 'image-collection-index-multi'
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
                    "description": {"type": "text"},
                    "createtime": {"type": "text"},
                    "image_path":{"type": "text"},
                    "image_embedding": {
                        "type": "knn_vector",
                        "dimension": outputEmbeddingLength,
                    },
                    "description_embedding": {
                        "type": "knn_vector",
                        "dimension": 1536,
                    }                    
                }
            },
        }
        res = OSSclient.indices.create(index, body=settings)
        print(res)
# create_index(index_name, outputEmbeddingLength)
def delete_index(index):
    if OSSclient.indices.exists(index):
        res = OSSclient.indices.delete(index)
        print(res)


def encode_image(image_path):
    # Open and resize the image
    with Image.open(image_path) as img:
        # Convert the resized image to bytes
        img_byte_array = io.BytesIO()
        img.save(img_byte_array, format=img.format)
        img_bytes = img_byte_array.getvalue()

    # Encode the resized image to base64
    image_encoded = base64.b64encode(img_bytes).decode('utf8')
    return image_encoded

def create_embeddings_from_image(image_encoded, outputEmbeddingLength):
    # Prepare the request body
    body = json.dumps(
        {
            "inputImage": image_encoded,
            "embeddingConfig": {
                "outputEmbeddingLength": outputEmbeddingLength
            }
        }
    )

    # Make the API call to the bedrock_runtime
    response = bedrock_runtime.invoke_model(
        body=body,
        modelId="amazon.titan-embed-image-v1",
        accept="application/json",
        contentType="application/json"
    )

    # Parse and return the vector
    vector = json.loads(response['body'].read().decode('utf8'))
    return vector

def generate_text_embedding(text: str) -> list:
    """
    使用 Titan Embedding 模型生成文本嵌入向量
    
    Args:
        text: 输入文本
        
    Returns:
        embedding_vector: 1536维的嵌入向量
    """
    
    # 准备请求体
    request_body = {
        "inputText": text
    }
    
    try:
        # 调用 Titan Embedding 模型
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # 解析响应
        response_body = json.loads(response.get('body').read())
        embedding = response_body.get('embedding')
        
        return embedding
        
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise

def create_dataset_from_dir(parent_dir):
    for subdir, dirs, files in os.walk(parent_dir):
        for file in files:
            if file.endswith(".jpg") or file.endswith(".png"):
                image_path = os.path.join(subdir, file)
                print(f"Processing image: {image_path}")
                image_encoded = encode_image(image_path)
                image_id = str(uuid.uuid4())
                s3_key = f'images/{image_id}'
                with open(image_path, 'rb') as image_file:
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=s3_key,
                        Body=image_file,
                        ContentType='image/jpeg'
                    )
                dt = datetime.datetime.now().isoformat()
                image_vector = create_embeddings_from_image(image_encoded, outputEmbeddingLength)
                descirption = multimodel_test.enrich_image_desc(image_path)
                descirption_embedding = generate_text_embedding(descirption)
                document = {
                    'id': image_id,
                    'description': descirption,
                    'image_embedding': image_vector["embedding"],
                    'description_embedding': descirption_embedding,
                    'createtime': dt,
                    'image_path': s3_key
                }                
                OSSclient.index(index=index_name, body=document)


# create_dataset_from_dir('/Users/enginez/Downloads/搜图10.19')



def get_embedding_for_text(text, outputEmbeddingLength):
    body = json.dumps(
        {"inputText": text, 
         "embeddingConfig": { 
                "outputEmbeddingLength": outputEmbeddingLength
            }
        }
    )

    response = bedrock_runtime.invoke_model(
        body=body, 
        modelId="amazon.titan-embed-image-v1", 
        accept="application/json", 
        contentType="application/json"       
    )

    vector_json = json.loads(response['body'].read().decode('utf8'))

    return vector_json, text

def query_the_database_with_text(text, index, outputEmbeddingLength, k):
    embedding = generate_text_embedding(text)
    query = {
      'query': {
        'bool': {
            "must": [
                {
                    "knn":{
                       'description_embedding':{
                           "vector": embedding,
                           "k": k
                       } 
                    }
                }
            ]
        }
      }
    }
    
    response = OSSclient.search(
        body = query,
        index = index
    )
    
    return response
    
def display_images(image_data):
    # Create a subplot with 1 row and the number of images as columns
    num_images = len(image_data)
    fig, axes = plt.subplots(1, num_images, figsize=(15, 5))

    # Iterate over each image data entry and display the image and description
    for i, entry in enumerate(image_data):
        image_path = "images/{}".format(entry['_source']['image_path'])
        #description = entry['metadata']['description']
        image_name = entry['_source']['id']
        # print the fields: id,score,description
        print(f"id: {image_name}, score: {entry['_score']}")


def query_the_database_with_image(image, index, outputEmbeddingLength, k):
    o_vector_json = create_embeddings_from_image(image, outputEmbeddingLength)
    query = {
      'query': {
        'bool': {
            "must": [
                {
                    "knn":{
                       'vector_field':{
                           "vector":o_vector_json["embedding"],
                           "k": k
                       } 
                    }
                }
            ]
        }
      }
    }
    
    response = OSSclient.search(
        body = query,
        index = index
    )
    
    return response

# 
def query_the_database_with_image_and_text(image, text, index, outputEmbeddingLength, k):
    o_vector_json = create_embeddings_from_image(image, outputEmbeddingLength)
    embedding = generate_text_embedding(text)
    query = {
      'query': {
        'bool': {
            "must": [
                {
                    "knn":{
                       'image_embedding':{
                           "vector":o_vector_json["embedding"],
                           "k": k
                       }
                    }
                },
                {
                    "knn":{
                       'description_embedding':{
                           "vector": embedding,
                           "k": k
                       }
                    }
                }
            ]
        }
      }
    }

    response = OSSclient.search(
        body = query,
        index = index
    )

    return response

image_encode_str = encode_image('/Users/enginez/Downloads/搜图10.19/模特款式近似/期望搜索图二.jpg')
results = query_the_database_with_image_and_text(image_encode_str, "The woman's posture and expression convey confidence and poise.", index_name, outputEmbeddingLength, k=10)

# results_text = query_the_database_with_text("Bikini", index_name, 1536, k=10)
# #Iterate over the elements in the result set and print each element
print("Text search results:")
for hit in results['hits']['hits']:
    print(hit['_source']['id'], hit['_score'])


