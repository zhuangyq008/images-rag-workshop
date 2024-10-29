from fastapi import HTTPException

class ImageProcessingError(HTTPException):
    def __init__(self, status_code: int, error_code: str, message: str, details: dict = None):
        super().__init__(status_code=status_code, detail={
            "error_code": error_code,
            "message": message,
            "details": details
        })

class ImageUploadError(ImageProcessingError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            status_code=400,
            error_code="IMAGE_UPLOAD_ERROR",
            message=message,
            details=details
        )

class ImageNotFoundError(ImageProcessingError):
    def __init__(self, image_id: str):
        super().__init__(
            status_code=404,
            error_code="IMAGE_NOT_FOUND",
            message=f"Image with ID {image_id} not found",
            details={"image_id": image_id}
        )

class InvalidRequestError(ImageProcessingError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            status_code=400,
            error_code="INVALID_REQUEST",
            message=message,
            details=details
        )

class OpenSearchError(ImageProcessingError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            status_code=500,
            error_code="OPENSEARCH_ERROR",
            message=message,
            details=details
        )
