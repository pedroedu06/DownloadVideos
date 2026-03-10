from pydantic import BaseModel
from typing import Optional

class DownloadRequest(BaseModel):
    url: str
    user_id: str
    type: str

class DownloadStatus(BaseModel):
    job_id: str
    status: Optional[str] = "queued"
    progress: float    

class DownloadDIR(BaseModel):
    path: str


class DownloadInfo(BaseModel):
    job_id: str
    id: Optional[str] = None
    title: Optional[str] = None
    filename: Optional[str] = None
    path: Optional[str] = None
    size: Optional[int] = None
    type: Optional[str] = None
    created_at: Optional[str] = None

class CacheEntry(BaseModel):
    data: str
    timestamp: int