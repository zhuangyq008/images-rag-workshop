from typing import Optional, Dict, Any, Union
from pydantic import BaseModel
from datetime import datetime

class APIResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]]
    timestamp: str

    @classmethod
    def success(cls, message: str = "Success", data: Optional[Dict[str, Any]] = None) -> 'APIResponse':
        return cls(
            code=200,
            message=message,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )

    @classmethod
    def error(cls, code: int, message: str, data: Optional[Dict[str, Any]] = None) -> 'APIResponse':
        return cls(
            code=code,
            message=message,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )

class ErrorDetail(BaseModel):
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
