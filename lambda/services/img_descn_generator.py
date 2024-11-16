import boto3
from io import BytesIO
import base64
import json
from botocore.exceptions import ClientError
from utils.config import Config
from PIL import Image
from fastapi import HTTPException

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
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": user_message},
                    ],
                }
            ],
        }
    )
    try:
        # Send the message to the model, using a basic inference configuration.
        response = client.invoke_model(
            modelId=model_id,
            body=body
        )

        # Extract and print the response text.
        response_body = json.loads(response.get("body").read())['content'][0]['text']
        return(response_body)

    except (ClientError, Exception) as e:
        # return(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        # exit(1)
        raise HTTPException(status_code=500, detail=f"Error in resize image: {str(e)}")
