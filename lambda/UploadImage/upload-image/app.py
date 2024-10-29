import json
import requests
from requests_aws4auth import AWS4Auth
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from requests.auth import HTTPBasicAuth
import urllib.request
import base64
from PIL import Image
import os

# global variable
host = os.environ['ENDPOINT']
service = "es"
region = os.environ['REGION']
s3_bucket = os.environ['S3_BUCKET'] # read from environment variable
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, region, 'es')
model_id = os.environ['MODEL_ID'] # read from environment variable
image_name = os.environ['IMAGE_NAME'] # read from environment variable

# client
## Initialise OpenSearch-py client
aos_client = OpenSearch(
    hosts = [{'host': host, 'port': 443}],
    http_auth = auth,
    use_ssl = True,
    connection_class = RequestsHttpConnection
)

# prompt
prompt = """
You are a professional e-commerce product editor, responsible for objectively providing detailed descriptions of products, and you can use product pictures to accurately describe its Clothing styles, Model characteristics, such as body shape, and posture ,  and description of the elements and patterns included in the product, etc.
<example>
a floor-length maxi dress with a wrap-style design. Key features include:

1. Long sleeves with slightly flared cuffs
2. Plunging V-neckline with a collared detail
3. Wrap-front closure with a tie at the waist
4. Flowing, A-line silhouette

The dress features an abstract, watercolor-like print. The color palette is predominantly composed of mint green, cream, peach, and black. The pattern has an organic, fluid quality that resembles artistic brushstrokes, creating a modern and sophisticated look.

The fabric appears to be lightweight and flowing, possibly a silk or high-quality synthetic blend that drapes elegantly on the body. This material choice enhances the dress's movement and adds to its overall luxurious appearance.

Model Characteristics:
The model has a slender, tall figure with a straight posture. She is standing in a relaxed stance, allowing the dress to fall naturally and showcase its draping qualities. Her pose effectively displays the full length of the dress and how it moves with the body.

The model's body shape and posture highlight the dress's flattering fit, particularly emphasizing how the wrap style cinches at the waist to create a defined silhouette.

Overall Style:
This dress presents a blend of elegance and artistic flair, suitable for various upscale occasions. Its unique print and flowing silhouette make it a versatile statement piece that could be styled for both formal events and more casual, sophisticated settings.

The combination of the wrap style, abstract print, and floor-length design creates a contemporary yet timeless look that would appeal to fashion-forward consumers looking for a distinctive, eye-catching garment.
</example>
"""

def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # upload to s3
    def upload_to_s3():
        s3_client = boto3.client('s3')
        with open('/tmp/'+body['filename'], "wb") as fh:
            # fh.write(base64.decodebytes(bytes(body['content'], "utf-8")))
            fh.write(base64.b64decode(body['content']))
        s3_client.upload_file('/tmp/'+body['filename'], s3_bucket, body['filename'])

    # resize image
    # def resize_image(photo, width, height)

    # generate description
    def generate_description():
        bedrock_client = boto3.client("bedrock-runtime", region_name=region)
        model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        # Start a conversation with the user message.
        user_message = prompt
        query_body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 5000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": body['content'],
                            },
                        },
                        {"type": "text", "text": user_message},
                    ],
                }
            ],
        })
        try:
            # Send the message to the model, using a basic inference configuration.
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=query_body
            )

            # Extract and print the response text.
            response_body = json.loads(response.get("body").read())['content'][0]['text']
            return(response_body)

        except (ClientError, Exception) as e:
            return(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
            exit(1)


    # parse event
    body = json.loads(event['body']) # {'filename': 'image.png', 'content': <base64 encoded image>}
    # # test only
    # body = event

    # upload to S3
    upload_to_s3()

    # construct payload
    payload = {}
    payload["image_binary"] = body['content']
    payload["image_description"] = generate_description()

    # index
    response = aos_client.index(
        index = 'multi-index',
        body = payload
    )

    print(response)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world",
            # "location": ip.text.replace("\n", "")
        }),
    }
