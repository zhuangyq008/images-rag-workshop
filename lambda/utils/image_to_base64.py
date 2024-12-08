import base64
from PIL import Image
from io import BytesIO

# image to base64
def image_to_base64(image_path):
    with Image.open(image_path) as img:
        # 创建一个字节流对象
        buffered = BytesIO()
        # 将图片保存到字节流中，并指定格式 (例如 'JPEG', 'PNG')
        img.save(buffered, format=img.format)
        # 获取字节数据并进行 Base64 编码
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_base64