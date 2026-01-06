from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from api.redisClient import redisClient
from api.schemas import DownloadRequest, DownloadStatus


# ProgressManager: classe simples que encapsula a leitura do progresso do Redis.
# Isso facilita testes e futuras adaptações (por exemplo, cache local, agregações).
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/downloadtask")
def create_download(data: DownloadRequest):
    job_id = str(uuid4())

    redisClient.set(f"download:{job_id}:status", "queued")
    redisClient.set(f"download:{job_id}:progress", 0)
    redisClient.set(f"download:{job_id}:url", data.url)

    redisClient.expire(f"download:{job_id}:status", 3600)
    redisClient.expire(f"download:{job_id}:progress", 3600)
    redisClient.expire(f"download:{job_id}:url", 3600)

    redisClient.lpush("queue:downloads", job_id)

    return {"job_id": job_id}

@app.get("/downloadStatus/{job_id}", response_model=DownloadStatus)
def get_status(job_id: str):
    status = redisClient.get(f"download:{job_id}:status")
    progress = progress_manager.get_progress(job_id)

    return {
        "job_id": job_id,
        "status": status,
        "progress": progress,
    }


@app.post("/downloadCancel/{job_id}")
def cancel_download(job_id: str):
    """Marca um job como cancelado para que workers respeitem essa sinalização.

    O endpoint define uma chave de cancelamento em Redis e atualiza o status
    para `cancelled`. O worker verifica essa chave e aborta o processamento.
    """
    cancel_key = f"download:{job_id}:cancel"
    redisClient.set(cancel_key, "1")
    redisClient.set(f"download:{job_id}:status", "cancelled")
    redisClient.set(f"download:{job_id}:progress", 0)
    return {"job_id": job_id, "cancelled": True}
