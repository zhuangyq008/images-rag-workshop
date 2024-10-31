import boto3
import base64
from PIL import Image
import io
import json
import os
import numpy as np
from utils.config import Config

class EmbeddingGeneratorTest:
    def __init__(self):
        """初始化Bedrock客户端"""
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1"
        )

    def encode_image(self, image_path):
        """
        将图片编码为base64字符串
        
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

    def generate_text_embedding(self, text):
        """
        生成文本的embedding向量
        
        Args:
            text: 输入文本
            
        Returns:
            embedding向量
        """
        try:
            # 准备请求体
            request_body = {
                "inputText": text,
                "embeddingConfig": {
                    "outputEmbeddingLength": Config.VECTOR_TEXT_DIMENSION
                }
            }
            
            # 调用Bedrock API
            response = self.bedrock_runtime.invoke_model(
                modelId="amazon.titan-embed-text-v1",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # 解析响应
            response_body = json.loads(response.get('body').read())
            embedding = response_body.get('embedding')
            
            # 验证embedding维度
            if len(embedding) != Config.VECTOR_TEXT_DIMENSION:
                raise ValueError(f"Invalid text embedding dimension. Expected {Config.VECTOR_TEXT_DIMENSION}, got {len(embedding)}")
                
            return embedding
            
        except Exception as e:
            print(f"Error generating text embedding: {str(e)}")
            raise

    def generate_image_embedding(self, image_path):
        """
        生成图片的embedding向量
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            embedding向量
        """
        try:
            # 编码图片
            image_base64 = self.encode_image(image_path)
            
            # 准备请求体
            request_body = {
                "inputImage": image_base64,
                "embeddingConfig": {
                    "outputEmbeddingLength": Config.VECTOR_DIMENSION
                }
            }
            
            # 调用Bedrock API
            response = self.bedrock_runtime.invoke_model(
                modelId="amazon.titan-embed-image-v1",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # 解析响应
            response_body = json.loads(response.get('body').read())
            embedding = response_body.get('embedding')
            
            # 验证embedding维度
            if len(embedding) != Config.VECTOR_DIMENSION:
                raise ValueError(f"Invalid image embedding dimension. Expected {Config.VECTOR_DIMENSION}, got {len(embedding)}")
                
            return embedding
            
        except Exception as e:
            print(f"Error generating image embedding: {str(e)}")
            raise

    def calculate_similarity(self, embedding1, embedding2):
        """
        计算两个embedding向量的余弦相似度
        
        Args:
            embedding1: 第一个embedding向量
            embedding2: 第二个embedding向量
            
        Returns:
            相似度分数 (0-1)
        """
        # 转换为numpy数组
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # 计算余弦相似度
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return similarity

def main():
    # 创建测试实例
    test = EmbeddingGeneratorTest()
    
    try:
        # 测试文本embedding
        print("\nTesting text embedding generation...")
        text = "这是一件蓝色的连衣裙"
        text_embedding = test.generate_text_embedding(text)
        print(f"Text embedding dimension: {len(text_embedding)}")
        print(f"First 5 values: {text_embedding[:5]}")
        
        # 测试图片embedding
        print("\nTesting image embedding generation...")
        image_path = "testcode/combined_local_image.jpg"  # 确保这个路径存在
        image_embedding = test.generate_image_embedding(image_path)
        print(f"Image embedding dimension: {len(image_embedding)}")
        print(f"First 5 values: {image_embedding[:5]}")
        
        # 测试相似文本
        print("\nTesting text similarity...")
        text1 = "蓝色连衣裙"
        text2 = "蓝色的裙子"
        embedding1 = test.generate_text_embedding(text1)
        embedding2 = test.generate_text_embedding(text2)
        similarity = test.calculate_similarity(embedding1, embedding2)
        print(f"Similarity between '{text1}' and '{text2}': {similarity:.4f}")
        
        # 测试错误处理
        print("\nTesting error handling...")
        try:
            test.generate_image_embedding("nonexistent_image.jpg")
        except Exception as e:
            print(f"Successfully caught error: {str(e)}")
            
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    main()
