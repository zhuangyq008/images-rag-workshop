import requests
import json
import base64
from PIL import Image
import io
import os
from typing import List
import mimetypes

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
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

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
        使用文本和图片搜索相似图片

        Args:
            query_text: 搜索文本
            image_path: 查询图片路径
            k: 返回结果数量

        Returns:
            API响应
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

    def is_image_file(self, file_path: str) -> bool:
        """
        Check if a file is an image based on its extension and content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if file is a valid image, False otherwise
        """
        try:
            extension = os.path.splitext(file_path)[1].lower()
            if extension not in self.supported_formats:
                return False
                
            # Try to open the file as an image
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    def find_all_images(self, directory: str) -> List[str]:
        """
        Recursively find all image files in a directory and its subdirectories.
        
        Args:
            directory: Root directory to search
            
        Returns:
            List of image file paths
        """
        image_files = []
        directory = os.path.abspath(directory)
        
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if self.is_image_file(file_path):
                    image_files.append(file_path)
        
        print(f"Found {len(image_files)} images in {directory}")
        return image_files

    def upload_directory(self, directory: str) -> dict:
        """
        Upload all images from a directory and its subdirectories.
        
        Args:
            directory: Directory containing images
            
        Returns:
            dict: Upload results summary
        """
        results = {
            'total_images': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'failed_files': []
        }
        
        # Find all images
        image_files = self.find_all_images(directory)
        results['total_images'] = len(image_files)
        
        # Upload each image
        for image_path in image_files:
            try:
                upload_result = self.upload_image(
                    image_path,
                    description=f"Image: {os.path.basename(image_path)}"
                )
                
                if isinstance(upload_result, dict) and upload_result.get('code') == 200:
                    results['successful_uploads'] += 1
                else:
                    results['failed_uploads'] += 1
                    results['failed_files'].append(image_path)
                    print(f"Failed to upload {image_path}: {upload_result}")
                    
            except Exception as e:
                results['failed_uploads'] += 1
                results['failed_files'].append(image_path)
                print(f"Error uploading {image_path}: {e}")
        
        return results

def main():
    # API测试示例
    api_url = os.environ.get('API_URL', 'http://127.0.0.1:8000')
    api_test = ImageProcessingAPITest(api_url)
    
    # Test directory upload
    directory = input("Enter the path to the image directory: ").strip()
    
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return
        
    print(f"\nStarting image upload from directory: {directory}")
    results = api_test.upload_directory(directory)
    
    print("\nUpload Summary:")
    print(f"Total images found: {results['total_images']}")
    print(f"Successfully uploaded: {results['successful_uploads']}")
    print(f"Failed uploads: {results['failed_uploads']}")
    
    if results['failed_files']:
        print("\nFailed uploads:")
        for file in results['failed_files']:
            print(f"- {file}")

if __name__ == "__main__":
    main()
