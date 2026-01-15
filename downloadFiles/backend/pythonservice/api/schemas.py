from pydantic import BaseModel
from typing import Optional

class DownloadRequest(BaseModel):
    url: str
    type: str

class DownloadStatus(BaseModel):
    job_id: str
    status: Optional[str] = "queued"
    progress: float    

class DownloadDIR(BaseModel):
    path: str