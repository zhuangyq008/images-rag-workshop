import pylibmagic
import magic

def get_image_mime_type(image_path):
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(image_path) # 'application/pdf'
    return mime_type
