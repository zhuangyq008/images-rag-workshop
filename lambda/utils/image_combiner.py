import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import math
from typing import List, Tuple
import boto3

class ImageCombiner:
    def __init__(self, target_size: Tuple[int, int] = (300, 300), max_columns: int = 3):
        self.target_size = target_size
        self.max_columns = max_columns

    def get_images_from_urls(self, image_urls: List[str]) -> List[Image.Image]:
        return [self._download_image(url) for url in image_urls]

    def get_images_from_directory(self, directory_path: str) -> List[Image.Image]:
        image_files = [f for f in os.listdir(directory_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        return [Image.open(os.path.join(directory_path, img)) for img in image_files]

    def combine_images(self, images: List[Image.Image]) -> Image.Image:
        resized_images = [self._resize_image(img) for img in images]

        num_images = len(resized_images)
        num_columns = min(self.max_columns, num_images)
        print(f"Number of images: {num_images}, Number of columns: {num_columns}")
        num_rows = math.ceil(num_images / num_columns)

        combined_width = num_columns * self.target_size[0]
        combined_height = num_rows * self.target_size[1]

        combined_image = Image.new('RGBA', (combined_width, combined_height), (255, 255, 255, 0))

        for index, image in enumerate(resized_images):
            row = index // num_columns
            col = index % num_columns
            x_offset = col * self.target_size[0]
            y_offset = row * self.target_size[1]
            
            # Add sequence number to the image
            image_with_number = self._add_sequence_number(image, index + 1)
            
            combined_image.paste(image_with_number, (x_offset, y_offset), image_with_number if image_with_number.mode == 'RGBA' else None)

        return combined_image

    def combine_two_images_horizontally(self, image1: Image.Image, image2: Image.Image, target_height: int = 320) -> Image.Image:
        """
        Combines two images horizontally (side by side) while maintaining aspect ratio.
        
        Args:
            image1: First image (left side)
            image2: Second image (right side)
            target_height: Target height for both images (default 320px)
            
        Returns:
            Combined image with both images side by side
        """
        # Convert images to RGBA if they aren't already
        if image1.mode != 'RGBA':
            image1 = image1.convert('RGBA')
        if image2.mode != 'RGBA':
            image2 = image2.convert('RGBA')
        
        # Calculate new dimensions while maintaining aspect ratio
        ratio1 = image1.width / image1.height
        ratio2 = image2.width / image2.height
        
        new_height = target_height
        new_width1 = int(target_height * ratio1)
        new_width2 = int(target_height * ratio2)
        
        # Resize images
        image1_resized = image1.resize((new_width1, new_height), Image.LANCZOS)
        image2_resized = image2.resize((new_width2, new_height), Image.LANCZOS)
        
        # Create new image to hold both images
        total_width = new_width1 + new_width2
        combined_image = Image.new('RGBA', (total_width, new_height), (255, 255, 255, 0))
        
        # Paste images side by side
        combined_image.paste(image1_resized, (0, 0), image1_resized)
        combined_image.paste(image2_resized, (new_width1, 0), image2_resized)
        
        return combined_image

    def _download_image(self, url: str) -> Image.Image:
        response = requests.get(url)
        return Image.open(BytesIO(response.content))

    def _download_image_from_s3(self, s3_url: str) -> Image.Image:
        # Assuming s3_url is in the format 's3://bucket-name/path/to/image.jpg'
        bucket_name, key = s3_url.replace("s3://", "").split("/", 1)
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket_name, Key=key)
        return Image.open(BytesIO(response['Body'].read()))

    def _resize_image(self, image: Image.Image) -> Image.Image:
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        return image.resize(self.target_size, Image.LANCZOS)

    def _add_sequence_number(self, image: Image.Image, number: int) -> Image.Image:
        draw = ImageDraw.Draw(image)
        font_size = min(self.target_size) // 10
        try:
            font = ImageFont.truetype("Arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        text = str(number)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width = right - left
        text_height = bottom - top
        position = (5, 5)  # Top-left corner with a small margin

        # Add a semi-transparent background for better visibility
        text_bg_size = (text_width + 10, text_height + 10)
        text_bg = Image.new('RGBA', text_bg_size, (0, 0, 0, 128))
        image.paste(text_bg, position, text_bg)

        # Draw the text
        draw.text((position[0] + 5, position[1] + 5), text, font=font, fill=(255, 255, 255, 255))

        return image
