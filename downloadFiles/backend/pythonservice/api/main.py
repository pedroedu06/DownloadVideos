from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from api.redisClient import redisClient
from api.schemas import DownloadRequest, DownloadStatus, DownloadDIR, DownloadInfo
from typing import List
import json

# aqui encapsula os valores de progresso do download do redis, assim facilita reutilizar em outros lugares
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

# Aqui é o coração do projeto (o seu intuito.)
@app.post("/downloadtask")
def create_download(data: DownloadRequest):
    job_id = str(uuid4())

    # Usa pipeline para agrupar todas as operações em um único round-trip
    pipe = redisClient.pipeline(transaction=False)
    pipe.set(f"download:{job_id}:type", data.type)
    pipe.set(f"download:{job_id}:status", "queued")
    pipe.set(f"download:{job_id}:progress", 0)
    pipe.set(f"download:{job_id}:url", data.url)
    pipe.set(f"download:{job_id}:user_id", data.user_id)
    
    # Todas as expirações juntas
    pipe.expire(f"download:{job_id}:status", 3600)
    pipe.expire(f"download:{job_id}:progress", 3600)
    pipe.expire(f"download:{job_id}:url", 3600)
    pipe.expire(f"download:{job_id}:format", 3600)
    pipe.expire(f"download:{job_id}:user_id", 3600)
    
    pipe.sadd(f"user:{data.user_id}:jobs", job_id)
    pipe.lpush("queue:downloads", job_id)
    pipe.execute()

    return {"job_id": job_id}

# aqui ele retorna status, progresso do job_id do worker
@app.get("/downloadStatus/{job_id}", response_model=DownloadStatus)
def get_status(job_id: str):
    # Pipeline: busca status e progresso em um único round-trip
    pipe = redisClient.pipeline(transaction=False)
    pipe.get(f"download:{job_id}:status")
    pipe.get(f"download:{job_id}:progress")
    results = pipe.execute()
    
    status = results[0]
    try:
        progress = float(results[1] or 0)
    except Exception:
        progress = 0.0

    return {
        "job_id": job_id,
        "status": status,
        "progress": progress,
    }

# aqui ele cancela o download e retorna o status de 'cancelled'
@app.post("/downloadCancel/{job_id}")
def cancel_download(job_id: str):
    pipe = redisClient.pipeline(transaction=False)
    pipe.set(f"download:{job_id}:cancel", "1")
    pipe.set(f"download:{job_id}:status", "cancelled")
    pipe.set(f"download:{job_id}:progress", 0)
    pipe.execute()
    return {"job_id": job_id, "cancelled": True}

@app.post('/downloadPath')
def downloadsetPath(data: DownloadDIR):
    redisClient.set('download:dir', data.path)
    return {"status": "ok"} 


@app.post('/downloadSettings')
def set_download_settings(settings: dict = Body(...)):
    mapping = {
        'default_video_format': 'settings:default:video_format',
        'default_audio_format': 'settings:default:audio_format',
        'video_quality': 'settings:video:quality',
        'audio_quality': 'settings:audio:quality',
    }

    # Pipeline para salvar todas as configurações de uma vez
    pipe = redisClient.pipeline(transaction=False)
    for k, v in settings.items():
        if k in mapping and v is not None:
            pipe.set(mapping[k], str(v))
    pipe.execute()

    return {"status": "ok"}


@app.get('/list_downloads', response_model=List[DownloadInfo])
def list_downloads():
    ids = redisClient.smembers('downloads:completed') or []
    if not ids:
        return []
    
    # Pipeline: buscar todas as infos de uma vez
    pipe = redisClient.pipeline(transaction=False)
    for job_id in ids:
        pipe.get(f"download:{job_id}:info")
    raw_results = pipe.execute()
    
    results = []
    for job_id, raw in zip(ids, raw_results):
        if raw:
            try:
                info = json.loads(raw)
            except Exception:
                info = {"job_id": job_id, "title": "Error parsing metadata"}
        else:
            # Fallback: buscar campos individuais via pipeline
            fb_pipe = redisClient.pipeline(transaction=False)
            fb_pipe.get(f"download:{job_id}:id")
            fb_pipe.get(f"download:{job_id}:title")
            fb_pipe.get(f"download:{job_id}:type")
            fb_results = fb_pipe.execute()
            
            info = {
                "job_id": job_id,
                "id": fb_results[0],
                "title": fb_results[1],
                "filename": None,
                "path": None,
                "size": None,
                "type": fb_results[2],
                "created_at": None,
            }
        results.append(info)

    return results
    
@app.get('/userDownload/{user_id}/downloads')  
def list_user_downloads(user_id: str):
    ids = redisClient.smembers(f"user:{user_id}:downloads:completed") or []
    if not ids:
        return []
    
    # Pipeline: buscar todas as infos de uma vez
    pipe = redisClient.pipeline(transaction=False)
    for job_id in ids:
        pipe.get(f"download:{job_id}:info")
    raw_results = pipe.execute()
    
    resultsUser = []
    for job_id, raw in zip(ids, raw_results):
        if raw:
            try:
                info = json.loads(raw)
            except Exception:
                info = {"job_id": job_id, "title": "Error parsing metadata"}
        else:
            info = {"job_id": job_id}
         
        resultsUser.append(info)
    
    return resultsUser

@app.post('/deletCache')
def clear_cache():
    keys = redisClient.keys("cache:*")
    if keys:
        redisClient.delete(*keys)

    return {"status": "ok"}

@app.post('/deletuserSettings')
def clear_settings():
    keys = redisClient.keys("settings:*")
    if keys:
        redisClient.delete(*keys)

    return {"status": "ok"}
