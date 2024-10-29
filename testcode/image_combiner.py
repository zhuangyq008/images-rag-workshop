import os
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import math
from typing import List, Tuple
import base64
import base64
import base64

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

    def _download_image(self, url: str) -> Image.Image:
        response = requests.get(url)
        return Image.open(BytesIO(response.content))

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
    
# generate a base64 string for a image
def image_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')
# generate image_to_base64 test case
def test_image_to_base64():
    # read image from local file
    image = Image.open("/Users/enginez/Downloads/搜图10.19/模特款式近似/期望搜索图一.jpg")
    base64_string = image_to_base64(image)
    print(base64_string)

def main():
    combiner = ImageCombiner(target_size=(300, 300), max_columns=3)

    # Example with local directory
    local_directory = "/Users/enginez/Downloads/搜图10.19/模特款式近似"  # Update this path to your local image directory
    if os.path.exists(local_directory):
        local_images = combiner.get_images_from_directory(local_directory)
        combined_local_image = combiner.combine_images(local_images)
        combined_local_image.save("combined_local_image.png", format="PNG")
        print("Combined image from local directory saved as 'combined_local_image.png'")
    else:
        print(f"Local directory '{local_directory}' not found.")

if __name__ == "__main__":
    test_image_to_base64()
