import boto3
from io import BytesIO
import base64
import json
from botocore.exceptions import ClientError
from utils.config import Config
from PIL import Image
from fastapi import HTTPException
from utils.aws_client_factory import AWSClientFactory
import uuid
import jsonlines
import logging

def image_resize(base64_image_data,width,height):
        try:
            image_data = base64.b64decode(base64_image_data)
            # 将二进制数据转换为 Pillow 支持的 Image 对象
            image = Image.open(BytesIO(image_data))
            # 调整图片大小到 320x320
            resized_image = image.resize((width, height))

            # 将调整后的图片直接转换为 Base64 编码
            buffer = BytesIO()
            resized_image.save(buffer, format=image.format)  # 使用原始格式保存到内存
            resized_base64_data = base64.b64encode(buffer.getvalue()).decode()  # 转为 Base64 字符串
            return resized_base64_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in resize image: {str(e)}")

# 描述信息生成函数
def enrich_image_desc(image_base64):
    client = boto3.client("bedrock-runtime")

    # Set the model ID, e.g., Titan Text Premier.
    # anthropic.claude-3-haiku-20240307-v1:0
    # anthropic.claude-3-5-sonnet-20240620-v1:0
    model_id = Config.MULTIMODEL_LLM_ID

    # Start a conversation with the user message.
    user_message = Config.IMG_DESCN_PROMPT

    
    image_base64 = image_resize(image_base64,320,320)

    body = json.dumps(
        {
            "schemaVersion": "messages-v1",
            "inferenceConfig": {"max_new_tokens": 5000},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "jpg",
                                "source": {"bytes": image_base64},
                            }
                        },
                        {
                            "text": user_message
                        }
                    ],
                }
            ]
        }
    )

    try:
        # Send the message to the model, using a basic inference configuration.
        response = client.invoke_model(
            modelId=model_id,
            body=body
        )

        # Extract and print the response text.
        response_body = json.loads(response.get("body").read())['output']['message']['content'][0]['text']
        return(response_body)

    except (ClientError, Exception) as e:
        # return(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        # exit(1)
        raise HTTPException(status_code=500, detail=f"Error in resize image: {str(e)}")

def description_generator_invocation_job(image_base64_list, batch_num):
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.info(f'Start generating invocation job')

    # Get uuid
    uuid_str = str(uuid.uuid4())
    
    # Initialization: Initialize an S3 client
    s3_client = AWSClientFactory.create_s3_client()
    # Initialization: Initialize a bedrock client
    bedrock_client = AWSClientFactory.create_bedrock_client()
    # Initialization: Invocation job configuration
    description_payload_file_name = f"{uuid_str}-{str(batch_num)}-descn.jsonl"
    discriptionGeneratorInputDataConfig=({
        "s3InputDataConfig": {
            "s3Uri": f"s3://{Config.BUCKET_NAME}/INVOCATION-INPUT-NO-IMAGE/{description_payload_file_name}"
        }
    })
    description_output_folder_name = f"{uuid_str}-{str(batch_num)}-descn/"
    output_directory = f"s3://{Config.BUCKET_NAME}/INVOCATION-OUTPUT-NO-IMAGE/{description_output_folder_name}"
    discriptionGeneratorOutputDataConfig=({
        "s3OutputDataConfig": {
            "s3Uri": output_directory
        }
    })

    try:
        # Construct description generation payload
        descn_gen_batch_inference_data = []
        s3_uri_json = {}
        count = 0
        for s3_uri in image_base64_list:
            # Get base64 string
            image_base64 = image_base64_list[s3_uri]["base64"]
            mime_type = image_base64_list[s3_uri]["mime_type"]
            if mime_type == "image/jpeg":
                format = "jpeg"
            elif mime_type == "image/png":
                format = "png"
            elif mime_type == "image/webp":
                format = "webp"
            elif mime_type == "image/gif":
                format = "gif"
            else:
                raise HTTPException(status_code=500, detail=f"Only support MIME type of image/jpeg, image/png, image/webp, image/gif. Got {mime_type} which is not supported.")
            # Get current time
            record_id = str(count).zfill(11)
            descn_gen_payload = {
                "recordId": record_id, 
                "modelInput": {
                    "schemaVersion": "messages-v1",
                    "inferenceConfig": {"max_new_tokens": 5000},
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "image": {
                                        "format": format,
                                        "source": {"bytes": image_base64},
                                    }
                                },
                                {
                                    "text": "Generate description for the image"
                                }
                            ],
                        }
                    ]
                }
            }
            descn_gen_batch_inference_data.append(descn_gen_payload)
            s3_uri_json[record_id] = s3_uri
            count += 1
        # Write to local jsonl file
        with jsonlines.open(f'/tmp/{description_payload_file_name}', 'w') as writer:
            logger.info(f"payload length {len(description_payload_file_name)}")
            writer.write_all(descn_gen_batch_inference_data)
            s3_client.upload_file(f'/tmp/{description_payload_file_name}', Config.BUCKET_NAME, 'INVOCATION-INPUT-NO-IMAGE/'+description_payload_file_name)
        # Create and start invocation job
        descn_gen_response = bedrock_client.create_model_invocation_job(
            roleArn=Config.BEDROCK_INVOKE_JOB_ROLE,
            modelId=Config.MULTIMODEL_LLM_ID,
            jobName=f"generate-description-{uuid_str}",
            inputDataConfig=discriptionGeneratorInputDataConfig,
            outputDataConfig=discriptionGeneratorOutputDataConfig
        )
        jobArn = descn_gen_response.get('jobArn')
        # Write all base64 images to a json file
        s3uri_file_name = f"{uuid_str}-{str(batch_num)}-s3uri.json"
        with open("/tmp/"+s3uri_file_name, "w") as file:
            logger.info(f"s3 uri json length: {len(s3_uri_json)}")
            s3_uri_jsonstr = json.dumps(s3_uri_json, indent=len(s3_uri_json))
            file.write(s3_uri_jsonstr)
            s3_client.upload_file("/tmp/"+s3uri_file_name, Config.BUCKET_NAME, 'S3-URI-NO-IMAGE/'+s3uri_file_name)
            file.close()

        return jobArn, output_directory, f"s3://{Config.BUCKET_NAME}/S3-URI-NO-IMAGE/{s3uri_file_name}"
    except (ClientError, Exception) as e:
        raise HTTPException(status_code=500, detail=f"Error when creating invocation job: {str(e)}")
