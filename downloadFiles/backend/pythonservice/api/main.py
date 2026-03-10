from datetime import datetime, timezone
from fastapi import FastAPI, Body, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from api.redisClient import redisClient, get_redis
from api.schemas import DownloadRequest, DownloadStatus, DownloadDIR, DownloadInfo, CacheEntry
from typing import List, Optional
import json
from api.configYt import getvideos
from api.configrecomendedvideos import recommendVideos
from api.extractIdVideo import extractVideoId
from api.getVideos import getInfosVideo
import asyncio

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


app = FastAPI()


# Garante que o Redis esteja disponível antes de cada request
def require_redis():
    r = get_redis()
    if r is None:
        raise HTTPException(status_code=503, detail="Redis não está disponível. Verifique se o Docker está rodando.")
    return r

@app.on_event("startup")
async def startup_reconnect():
    global redisClient
    if redisClient is None:
        print("[API] Redis não conectado na inicialização, tentando novamente...")
        from api.redisClient import get_redis as _get
        redisClient = _get()
        if redisClient:
            print("[API] Redis reconectado com sucesso no startup!")
        else:
            print("[API] AVISO: Redis ainda não disponível. As rotas retornarão 503 até que o Redis esteja pronto.")


progress_manager = None

@app.on_event("startup")
async def init_progress_manager():
    global progress_manager
    r = get_redis()
    if r:
        progress_manager = ProgressManager(r)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_TTL_MS = 5 * 60 * 1000

feed_cache: Optional[dict] = None

@app.get("/feed")
async def getFeed():
    global feed_cache
    try:
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        if feed_cache and (now - feed_cache["timestamp"]) < CACHE_TTL_MS:
            return feed_cache["data"]
        
        videoInfo = await getvideos()
        recomendedVideos = recommendVideos(videoInfo)

        feed_cache = {"data": [v.__dict__ for v in recomendedVideos], "timestamp": now}

        return feed_cache["data"]

    except Exception as error:
        print(f"log error: {error}")
        raise HTTPException(status_code=500, detail="erro ao buscar os videos")


VIDEO_CACHE_TTL_MS = 30 * 60 * 1000
videoInfoCache: dict = {}

async def clear_cache():
    while True:
        await asyncio.sleep(10 * 60)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)

        keys_to_delete = [
            key for key, entry in videoInfoCache.items()
            if (now - entry["timestamp"]) > VIDEO_CACHE_TTL_MS
        ]

        for key in keys_to_delete:
            del videoInfoCache[key]

@app.post('/getInfoVideo')
async def getinfoVideo(request: Request):
    try:
        body = await request.json()
        url = body.get('url')

        if not url:
            raise HTTPException(status_code=400, detail="url nao e valida")

        videoId = extractVideoId(url)
        if not videoId:
            raise HTTPException(status_code=400, detail="URL inválida")

        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        cached = videoInfoCache.get(videoId)
        if cached and (now - cached["timestamp"]) < VIDEO_CACHE_TTL_MS:
            return cached["data"]

        previwInfo = await getInfosVideo(videoId)

        videoInfoCache[videoId] = {"data": previwInfo, "timestamp": now}

        return previwInfo

    except HTTPException:
        raise
    except Exception as error:
        if hasattr(error, 'response') and error.response.status_code == 403:
            print("YouTube bloqueou a requisição (provável limite de API ou IP)")
        else:
            print(f"Erro no /getInfoVideo: {error}")
            
        raise HTTPException(status_code=500, detail="Falha ao obter as informações do vídeo")

# Aqui é o coração do projeto
@app.post("/downloadtask")
def create_download(data: DownloadRequest, r = Depends(require_redis)):
    job_id = str(uuid4())

    # Usa pipeline para agrupar todas as operações em um único round-trip
    pipe = r.pipeline(transaction=False)
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
def get_status(job_id: str, r = Depends(require_redis)):
    # Pipeline: busca status e progresso em um único round-trip
    pipe = r.pipeline(transaction=False)
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
def cancel_download(job_id: str, r = Depends(require_redis)):
    pipe = r.pipeline(transaction=False)
    pipe.set(f"download:{job_id}:cancel", "1")
    pipe.set(f"download:{job_id}:status", "cancelled")
    pipe.set(f"download:{job_id}:progress", 0)
    pipe.execute()
    return {"job_id": job_id, "cancelled": True}

@app.post('/downloadPath')
def downloadsetPath(data: DownloadDIR, r = Depends(require_redis)):
    r.set('download:dir', data.path)
    return {"status": "ok"} 


@app.post('/downloadSettings')
def set_download_settings(r = Depends(require_redis), settings: dict = Body(...)):
    mapping = {
        'default_video_format': 'settings:default:video_format',
        'default_audio_format': 'settings:default:audio_format',
        'video_quality': 'settings:video:quality',
        'audio_quality': 'settings:audio:quality',
    }

    # Pipeline para salvar todas as configurações de uma vez
    pipe = r.pipeline(transaction=False)
    for k, v in settings.items():
        if k in mapping and v is not None:
            pipe.set(mapping[k], str(v))
    pipe.execute()

    return {"status": "ok"}


@app.get('/list_downloads', response_model=List[DownloadInfo])
def list_downloads(r = Depends(require_redis)):
    ids = r.smembers('downloads:completed') or []
    if not ids:
        return []
    
    # Pipeline: buscar todas as infos de uma vez
    pipe = r.pipeline(transaction=False)
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
            fb_pipe = r.pipeline(transaction=False)
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
def list_user_downloads(user_id: str, r = Depends(require_redis)):
    ids = r.smembers(f"user:{user_id}:downloads:completed") or []
    if not ids:
        return []
    
    # Pipeline: buscar todas as infos de uma vez
    pipe = r.pipeline(transaction=False)
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
def clear_cache(r = Depends(require_redis)):
    keys = r.keys("cache:*")
    if keys:
        r.delete(*keys)

    return {"status": "ok"}

@app.post('/deletuserSettings')
def clear_settings(r = Depends(require_redis)):
    keys = r.keys("settings:*")
    if keys:
        r.delete(*keys)

    return {"status": "ok"}
