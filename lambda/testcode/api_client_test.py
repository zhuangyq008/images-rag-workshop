import requests
import json
import base64
from PIL import Image
import io
import os

class ImageProcessingAPITest:
    def __init__(self, base_url):
        """
        初始化API测试类
        
        Args:
            base_url: API的基础URL，例如 'https://xxxxx.execute-api.us-east-1.amazonaws.com/prod'
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json'
        }

    def encode_image(self, image_path):
        """
        将图片文件编码为base64字符串
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64编码的图片字符串
        """
        with Image.open(image_path) as img:
            # 转换图片为bytes
            img_byte_array = io.BytesIO()
            img.save(img_byte_array, format=img.format)
            img_bytes = img_byte_array.getvalue()
            
        # 编码为base64
        return base64.b64encode(img_bytes).decode('utf-8')

    def upload_image(self, image_path, description="", tags=None):
        """
        上传图片到服务
        
        Args:
            image_path: 图片文件路径
            description: 图片描述
            tags: 图片标签列表
            
        Returns:
            API响应
        """
        if tags is None:
            tags = []
            
        image_base64 = self.encode_image(image_path)
        
        payload = {
            "image": image_base64,
            "description": description,
            "tags": tags
        }
        
        response = requests.post(
            f"{self.base_url}/images",
            headers=self.headers,
            json=payload
        )
        
        return response.json()

    def update_image(self, image_id, description=None, tags=None):
        """
        更新图片元数据
        
        Args:
            image_id: 图片ID
            description: 新的图片描述
            tags: 新的标签列表
            
        Returns:
            API响应
        """
        payload = {
            "image_id": image_id
        }
        
        if description is not None:
            payload["description"] = description
        if tags is not None:
            payload["tags"] = tags
            
        response = requests.put(
            f"{self.base_url}/images",
            headers=self.headers,
            json=payload
        )
        
        return response.json()

    def search_by_image(self, image_path, k=10):
        """
        使用图片搜索相似图片
        
        Args:
            image_path: 查询图片路径
            k: 返回结果数量
            
        Returns:
            API响应
        """
        image_base64 = self.encode_image(image_path)
        
        payload = {
            "query_image": image_base64,
            "k": k
        }
        
        response = requests.post(
            f"{self.base_url}/images/search",
            headers=self.headers,
            json=payload
        )
        
        return response.json()

    def search_by_text(self, query_text, k=10):
        """
        使用文本搜索图片
        
        Args:
            query_text: 搜索文本
            k: 返回结果数量
            
        Returns:
            API响应
        """
        payload = {
            "query_text": query_text,
            "k": k
        }
        
        response = requests.post(
            f"{self.base_url}/images/search",
            headers=self.headers,
            json=payload
        )
        
        return response.json()
    def search_by_text_and_image(self, query_text, image_path, k=10):
        """
        使用文本和图片搜索相��图片

        Args:
            query_text: ���文本
            image_path: 查询图片路径
            k: 返回结果数量

        Returns:
            API��应
        """
        image_base64 = self.encode_image(image_path)

        payload = {
            "query_text": query_text,
            "query_image": image_base64,
            "k": k
        }

        response = requests.post(
            f"{self.base_url}/images/search",
            headers=self.headers,
            json=payload
        )

        return response.json()

    def delete_image(self, image_id):
        """
        删除图片
        
        Args:
            image_id: 要删除的图片ID
            
        Returns:
            API响应
        """
        response = requests.delete(
            f"{self.base_url}/images/{image_id}",
            headers=self.headers
        )
        
        return response.json()

def main():
    # API测试示例
    api_url = os.environ.get('API_URL', 'http://127.0.0.1:8000')
    api_test = ImageProcessingAPITest(api_url)
    
    # 测试上传图片
    # print("Testing image upload...")
    # upload_result = api_test.upload_image(
    #     "/Users/enginez/Downloads/blue backpack on a table.png",
    #     description="Test image",
    #     tags=["test", "demo"]
    # )
    # print("Upload result:", json.dumps(upload_result, indent=2))
    
    # if "data" in upload_result and "image_id" in upload_result["data"]:
    #     image_id = upload_result["data"]["image_id"]
        
    #     # 测试更新元数据
    #     print("\nTesting metadata update...")
    #     update_result = api_test.update_image(
    #         image_id,
    #         description="Updated description",
    #         tags=["updated", "test"]
    #     )
    #     print("Update result:", json.dumps(update_result, indent=2))
        
    #     # 测试图片搜索
    # print("\nTesting image search...")
    # search_result = api_test.search_by_image("/Users/enginez/Downloads/搜图10.19/模特款式近似/期望搜索图一.jpg", k=5)
    # print("Search result:", json.dumps(search_result, indent=2))
    #   测试文本与图片搜索
    print("\nTesting text and image search...")
    search_result = api_test.search_by_text_and_image("鼠标", "/Users/enginez/Downloads/搜图10.19/元素图相同，款式不同/1、搜索原图.jpg", k=5)    
    print("Text search result:", json.dumps(search_result, indent=2))
        # 测试文本搜索
    # print("\nTesting text search...")
    # text_search_result = api_test.search_by_text("blue backpack on a table", k=5)
    # print("Text search result:", json.dumps(text_search_result, indent=2))
        
    #     # 测试删除图片
    #     print("\nTesting image deletion...")
    #     delete_result = api_test.delete_image(image_id)
    #     print("Delete result:", json.dumps(delete_result, indent=2))

if __name__ == "__main__":
    main()
