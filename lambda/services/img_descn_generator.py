import boto3
from PIL import Image
from io import BytesIO
import base64
import json
from botocore.exceptions import ClientError

def image_to_base64(image_path):
    # 打开图片
    with Image.open(image_path) as img:
        # 创建一个字节流对象
        buffered = BytesIO()
        # 将图片保存到字节流中，并指定格式 (例如 'JPEG', 'PNG')
        img.save(buffered, format=img.format)
        # 获取字节数据并进行 Base64 编码
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_base64
# 描述信息生成函数
def enrich_image_desc(image_base64):
    client = boto3.client("bedrock-runtime", region_name="us-west-2")

    # Set the model ID, e.g., Titan Text Premier.
    # anthropic.claude-3-haiku-20240307-v1:0
    # anthropic.claude-3-5-sonnet-20240620-v1:0
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"

    # Start a conversation with the user message.
    user_message = """
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
        return(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
