from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.configYt import getvideos
from api.configrecomendedvideos import recommendVideos
from api.extractIdVideo import extractVideoId
from api.getVideos import getInfosVideo
from api.schemas import DownloadDIR, DownloadInfo, DownloadRequest, DownloadSettings, DownloadStatus
from api.sqliteClient import clear_settings, create_table, get_db, set_setting
CACHE_TTL_MS = 5 * 60 * 1000
VIDEO_CACHE_TTL_MS = 30 * 60 * 1000


def _utc_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _progress_payload(row: Any, job_id: Optional[str] = None) -> dict[str, Any]:
    if row is None:
        return {
            "job_id": job_id,
            "status": "queued",
            "progress": 0.0,
            "error": None,
            "title": None,
        }

    return {
        "job_id": row["job_id"],
        "status": row["status"],
        "progress": float(row["progress"] or 0),
        "error": row["error"],
        "title": row["title"],
    }


class ProgressManager:
    def __init__(self, poll_interval: float = 0.35):
        self._connections: dict[str, set[WebSocket]] = {}
        self._last_payloads: dict[str, dict[str, Any]] = {}
        self._poll_interval = poll_interval
        self._watcher: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        if self._watcher is None or self._watcher.done():
            self._watcher = asyncio.create_task(self._watch())

    async def stop(self) -> None:
        if self._watcher is None:
            return

        self._watcher.cancel()
        with suppress(asyncio.CancelledError):
            await self._watcher
        self._watcher = None

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(job_id, set()).add(websocket)

        row = get_db().execute(
            """
            SELECT job_id, status, progress, error, title
            FROM downloads
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

        payload = _progress_payload(row, job_id)
        self._last_payloads[job_id] = payload
        await websocket.send_json(payload)

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(job_id)
        if not sockets:
            return

        sockets.discard(websocket)

        if not sockets:
            self._connections.pop(job_id, None)
            self._last_payloads.pop(job_id, None)

    async def _broadcast(self, job_id: str, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []

        for websocket in list(self._connections.get(job_id, set())):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)

        for websocket in stale:
            self.disconnect(job_id, websocket)

    async def _watch(self) -> None:
        while True:
            await asyncio.sleep(self._poll_interval)

            job_ids = list(self._connections.keys())
            if not job_ids:
                continue

            placeholders = ",".join("?" for _ in job_ids)
            rows = get_db().execute(
                f"""
                SELECT job_id, status, progress, error, title
                FROM downloads
                WHERE job_id IN ({placeholders})
                """,
                job_ids,
            ).fetchall()

            payloads = {
                row["job_id"]: _progress_payload(row)
                for row in rows
            }

            for job_id in job_ids:
                payload = payloads.get(job_id, _progress_payload(None, job_id))
                previous = self._last_payloads.get(job_id)

                if previous != payload:
                    self._last_payloads[job_id] = payload
                    await self._broadcast(job_id, payload)


app = FastAPI()
progress_manager = ProgressManager()
feed_cache: Optional[dict[str, Any]] = None
video_info_cache: dict[str, dict[str, Any]] = {}


def require_db():
    try:
        db = get_db()
        db.execute("SELECT 1")
        return db
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Banco indisponivel: {error}") from error


async def trim_video_info_cache() -> None:
    while True:
        await asyncio.sleep(10 * 60)
        now = _utc_ms()

        stale_keys = [
            key for key, entry in video_info_cache.items()
            if (now - entry["timestamp"]) > VIDEO_CACHE_TTL_MS
        ]

        for key in stale_keys:
            video_info_cache.pop(key, None)


def _download_row_to_info(row: Any) -> DownloadInfo:
    created_at = row["completed_at"] or row["created_at"]
    return DownloadInfo(
        job_id=row["job_id"],
        id=row["source_id"],
        title=row["title"],
        filename=row["filename"],
        path=row["filepath"],
        size=row["size"],
        type=row["type"],
        created_at=created_at,
        thumbnail=row["thumbnail"],
        error=row["error"],
    )


@app.on_event("startup")
async def startup() -> None:
    db = get_db()
    create_table(db)
    await progress_manager.start()
    app.state.cache_cleanup_task = asyncio.create_task(trim_video_info_cache())
    print("[API] SQLite conectado com sucesso.")


@app.on_event("shutdown")
async def shutdown() -> None:
    cache_cleanup_task = getattr(app.state, "cache_cleanup_task", None)
    if cache_cleanup_task is not None:
        cache_cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cache_cleanup_task

    await progress_manager.stop()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/feed")
async def get_feed():
    global feed_cache

    try:
        now = _utc_ms()
        if feed_cache and (now - feed_cache["timestamp"]) < CACHE_TTL_MS:
            return feed_cache["data"]

        recommended_videos = recommendVideos(await getvideos())
        feed_cache = {
            "data": [video.__dict__ for video in recommended_videos],
            "timestamp": now,
        }
        return feed_cache["data"]
    except Exception as error:
        print(f"log error: {error}")
        raise HTTPException(status_code=500, detail="erro ao buscar os videos") from error


@app.post("/getInfoVideo")
async def get_info_video(request: Request):
    try:
        body = await request.json()
        url = body.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="url nao e valida")

        video_id = extractVideoId(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="URL invalida")

        now = _utc_ms()
        cached = video_info_cache.get(video_id)
        if cached and (now - cached["timestamp"]) < VIDEO_CACHE_TTL_MS:
            return cached["data"]

        preview_info = await getInfosVideo(video_id)
        video_info_cache[video_id] = {
            "data": preview_info,
            "timestamp": now,
        }
        return preview_info
    except HTTPException:
        raise
    except Exception as error:
        if hasattr(error, "response") and error.response.status_code == 403:
            print("YouTube bloqueou a requisicao")
        else:
            print(f"Erro no /getInfoVideo: {error}")
        raise HTTPException(status_code=500, detail="Falha ao obter as informacoes do video") from error


@app.post("/downloadtask")
def create_download(data: DownloadRequest, db=Depends(require_db)):
    job_type = data.type.strip().lower()
    if job_type not in {"video", "audio"}:
        raise HTTPException(status_code=400, detail="tipo de download invalido")

    job_id = str(uuid4())
    db.execute(
        """
        INSERT INTO downloads (
            job_id,
            url,
            user_id,
            type,
            status,
            progress,
            next_attempt_at
        )
        VALUES (?, ?, ?, ?, 'queued', 0, CURRENT_TIMESTAMP)
        """,
        (job_id, data.url, data.user_id, job_type),
    )
    return {"job_id": job_id}


@app.get("/downloadStatus/{job_id}", response_model=DownloadStatus)
def get_status(job_id: str, db=Depends(require_db)):
    row = db.execute(
        """
        SELECT job_id, status, progress, error
        FROM downloads
        WHERE job_id = ?
        """,
        (job_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Job nao encontrado")

    return DownloadStatus(
        job_id=row["job_id"],
        status=row["status"],
        progress=float(row["progress"] or 0),
        error=row["error"],
    )


@app.websocket("/ws/downloads/{job_id}")
async def download_progress_socket(websocket: WebSocket, job_id: str):
    await progress_manager.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        progress_manager.disconnect(job_id, websocket)
    except Exception:
        progress_manager.disconnect(job_id, websocket)
        raise


@app.post("/downloadCancel/{job_id}")
def cancel_download(job_id: str, db=Depends(require_db)):
    row = db.execute(
        "SELECT status FROM downloads WHERE job_id = ?",
        (job_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Job nao encontrado")

    db.execute(
        """
        UPDATE downloads
        SET
            cancel_requested = 1,
            status = CASE
                WHEN status IN ('done', 'failed', 'cancelled') THEN status
                ELSE 'cancelled'
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE job_id = ?
        """,
        (job_id,),
    )
    return {"job_id": job_id, "cancelled": True}


@app.post("/downloadPath")
def set_download_path(data: DownloadDIR, db=Depends(require_db)):
    set_setting("download_path", data.path, db)
    return {"status": "ok"}


@app.post("/downloadSettings")
def set_download_settings(settings: DownloadSettings, db=Depends(require_db)):
    payload = settings.model_dump(exclude_none=True)
    for key, value in payload.items():
        set_setting(key, str(value), db)
    return {"status": "ok"}


@app.get("/list_downloads", response_model=list[DownloadInfo])
def list_downloads(db=Depends(require_db)):
    rows = db.execute(
        """
        SELECT job_id, source_id, title, filename, filepath, size, type, thumbnail, error, created_at, completed_at
        FROM downloads
        WHERE status = 'done'
        ORDER BY datetime(COALESCE(completed_at, created_at)) DESC
        """
    ).fetchall()
    return [_download_row_to_info(row) for row in rows]


@app.get("/userDownload/{user_id}/downloads", response_model=list[DownloadInfo])
def list_user_downloads(user_id: str, db=Depends(require_db)):
    rows = db.execute(
        """
        SELECT job_id, source_id, title, filename, filepath, size, type, thumbnail, error, created_at, completed_at
        FROM downloads
        WHERE user_id = ? AND status = 'done'
        ORDER BY datetime(COALESCE(completed_at, created_at)) DESC
        """,
        (user_id,),
    ).fetchall()
    return [_download_row_to_info(row) for row in rows]


@app.post("/deletCache")
def clear_runtime_cache():
    global feed_cache
    feed_cache = None
    video_info_cache.clear()
    return {"status": "ok"}


@app.post("/deletuserSettings")
def delete_user_settings(db=Depends(require_db)):
    clear_settings(db)
    return {"status": "ok"}
