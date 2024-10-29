from typing import Optional, Dict, Any
from pydantic import BaseModel

class APIResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]]
    timestamp: str
