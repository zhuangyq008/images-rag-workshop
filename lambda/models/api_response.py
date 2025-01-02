from typing import Optional, Dict, Any, Union
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import JSONResponse

class APIResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]]
    timestamp: str

    @classmethod
    def success(cls, message: str = "Success", data: Optional[Dict[str, Any]] = None) -> JSONResponse:
        # 构造 API 响应
        api_response = cls(
            code=200,
            message=message,
            data=data,
            timestamp=datetime.utcnow().isoformat(),
        )

        # 构建 JSONResponse 并添加 CORS 头部
        response = JSONResponse(content=api_response.dict())
        
        return response

    @classmethod
    def error(cls, code: int, message: str, data: Optional[Dict[str, Any]] = None) -> JSONResponse:
        # 构造 API 响应
        api_response = cls(
            code=code,
            message=message,
            data=data,
            timestamp=datetime.utcnow().isoformat(),
        )

        # 构建 JSONResponse 并添加 CORS 头部
        response = JSONResponse(content=api_response.dict())

        return response


class ErrorDetail(BaseModel):
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
