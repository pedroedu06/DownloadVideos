from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from api.redisClient import redisClient
from api.schemas import DownloadRequest, DownloadStatus, DownloadDIR, DownloadInfo
from typing import List
import json

# aqui encapsula os valores de progresso do donwload do redis, assim facilita reutilizar em outros lugares
class ProgressManager:
    def __init__(self, redis_client):
        self._r = redis_client

    def get_progress(self, job_id: str) -> float:
        raw = self._r.get(f"download:{job_id}:progress")
        try:
            return float(raw or 0)
        except Exception:
            return 0.0


progress_manager = ProgressManager(redisClient)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Aqui e o coracao do projeto (o seu intuito.)
@app.post("/downloadtask")
def create_download(data: DownloadRequest):
    job_id = str(uuid4())

    redisClient.set(f"download:{job_id}:type", data.type)
    redisClient.set(f"download:{job_id}:status", "queued")
    redisClient.set(f"download:{job_id}:progress", 0)
    redisClient.set(f"download:{job_id}:url", data.url)
    redisClient.set(f"download:{job_id}:user_id", data.user_id)

    redisClient.expire(f"download:{job_id}:status", 3600)
    redisClient.expire(f"download:{job_id}:progress", 3600)
    redisClient.expire(f"download:{job_id}:url", 3600)
    redisClient.expire(f"download:{job_id}:format", 3600)
    redisClient.expire(f"download:{job_id}:user_id", 3600)

    redisClient.sadd(f"user:{data.user_id}:jobs", job_id)

    redisClient.lpush("queue:downloads", job_id)

    return {"job_id": job_id}

#aqui ele retorna status, progresso do job_id do worker
@app.get("/downloadStatus/{job_id}", response_model=DownloadStatus)
def get_status(job_id: str):
    status = redisClient.get(f"download:{job_id}:status")
    progress = progress_manager.get_progress(job_id)

    return {
        "job_id": job_id,
        "status": status,
        "progress": progress,
    }

# aqui ele cancela o donwload e retorna o status de 'cancelled'
@app.post("/downloadCancel/{job_id}")
def cancel_download(job_id: str):
    cancel_key = f"download:{job_id}:cancel"
    redisClient.set(cancel_key, "1")
    redisClient.set(f"download:{job_id}:status", "cancelled")
    redisClient.set(f"download:{job_id}:progress", 0)
    return {"job_id": job_id, "cancelled": True}

@app.post('/downloadPath')
def downloadsetPath(data: DownloadDIR):
    redisClient.set('download:dir', data.path)
    return {"status": "ok!"} 


@app.post('/downloadSettings')
def set_download_settings(settings: dict = Body(...)):
    mapping = {
        'default_video_format': 'settings:default:video_format',
        'default_audio_format': 'settings:default:audio_format',
        'video_quality': 'settings:video:quality',
        'audio_quality': 'settings:audio:quality',
    }

    for k, v in settings.items():
        if k in mapping and v is not None:
            redisClient.set(mapping[k], str(v))

    return {"status": "ok"}


@app.get('/list_downloads', response_model=List[DownloadInfo])
def list_downloads():
    ids = redisClient.smembers('downloads:completed') or []
    results = []
    for job_id in ids:
        raw = redisClient.get(f"download:{job_id}:info")
        if raw:
            try:
                info = json.loads(raw)
            except Exception:
                info = {}
        else:
            info = {
                "job_id": job_id,
                "id": redisClient.get(f"download:{job_id}:id"),
                "title": redisClient.get(f"download:{job_id}:title"),
                "filename": None,
                "path": None,
                "size": None,
                "type": redisClient.get(f"download:{job_id}:type"),
                "created_at": None,
            }
        info["job_id"] = job_id
        results.append(info)


    return results
    
@app.get('/userDownload/{user_id}/downloads')  
def list_user_downloads(user_id: str):
    ids = redisClient.smembers(f"user:{user_id}:downloads:completed") or []
    resultsUser = []

    for job_id in ids:
        raw = redisClient.get(f"download:{job_id}:info")
        if raw:
            try:
                info = json.loads(raw)
            except Exception:
                info = {}
        else:
            info = {}
         
        info["job_id"] = job_id
        resultsUser.append(info)
    
    return resultsUser
