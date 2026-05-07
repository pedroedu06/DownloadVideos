from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DownloadRequest(BaseModel):
    url: str
    user_id: str
    type: str


class DownloadStatus(BaseModel):
    job_id: str
    status: str = "queued"
    progress: float
    error: Optional[str] = None


class DownloadDIR(BaseModel):
    path: str


class DownloadSettings(BaseModel):
    default_video_format: Optional[str] = None
    default_audio_format: Optional[str] = None
    video_quality: Optional[str] = None
    audio_quality: Optional[str] = None


class DownloadInfo(BaseModel):
    job_id: str
    id: Optional[str] = None
    title: Optional[str] = None
    filename: Optional[str] = None
    path: Optional[str] = None
    size: Optional[int] = None
    type: Optional[str] = None
    created_at: Optional[str] = None
    thumbnail: Optional[str] = None
    error: Optional[str] = None


class CacheEntry(BaseModel):
    data: str
    timestamp: int
