import json
import signal
import time
import uuid
import logging
import os
from pathlib import Path
from typing import Optional

import redis
from yt_dlp import YoutubeDL


# redis client, no config dos lock necessita.
REDIS_CLIENT = os.getenv('REDIS_HOST', 'localhost')
r = redis.Redis(host=REDIS_CLIENT, port=6379, decode_responses=True)

# Diretório padrão de download 
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_PATH', '/downloads'))

# Worker configuration
MAX_RETRIES = 3
LOCK_TTL = 60 * 60  # 1 hora
RETRY_BACKOFF = 5  # segundos entre tentativas (poderia ser exponencial)

# Worker identity used for lock ownership
WORKER_ID = str(uuid.uuid4())

# Setup logging: logs estruturados em JSON para facilitar parsing
logger = logging.getLogger("download_worker")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _log_structured(event: str, extra: dict):
    payload = {"event": event, **extra}
    logger.info(json.dumps(payload, ensure_ascii=False))


def acquire_lock(job_id: str) -> bool:
    lock_key = f"download:{job_id}:lock"
    # tentativa de setar lock com NX (apenas se não existir)
    return r.set(lock_key, WORKER_ID, nx=True, ex=LOCK_TTL)


def release_lock(job_id: str) -> None:
    lock_key = f"download:{job_id}:lock"
    try:
        val = r.get(lock_key)
        if val == WORKER_ID:
            r.delete(lock_key)
    except Exception:
        pass


shutdown_requested = False


def _signal_handler(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    _log_structured("shutdown_request", {"signal": signum})


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def process_job(job_id: str, url: Optional[str]):
    """Processa um job de download.

    Implementa estados claros, retries e DLQ. Usa lock distribuído para evitar
    processamento concorrente do mesmo job por múltiplos workers.
    """

    if not url:
        r.set(f"download:{job_id}:status", "error")
        r.set(f"download:{job_id}:error", "url nao encontrada")
        _log_structured("job_error", {"job_id": job_id, "reason": "url not found"})
        return

    # se já existe sinal de cancelamento antes de começar, aborta
    cancel_key = f"download:{job_id}:cancel"
    if r.get(cancel_key):
        r.set(f"download:{job_id}:status", "cancelled")
        _log_structured("job_cancelled_pre", {"job_id": job_id})
        return

    # tenta adquirir lock; se não conseguir, outro worker já está processando
    locked = acquire_lock(job_id)
    if not locked:
        _log_structured("lock_skip", {"job_id": job_id})
        # re-enfileira para tentar depois (curto retorno) ou simplesmente retorna
        return

    # marca que estamos processando
    r.set(f"download:{job_id}:status", "downloading")
    r.set(f"download:{job_id}:progress", 0)

    def hook(d):
        status = d.get("status")
        # respeitar cancelamento durante o download
        if r.get(cancel_key):
            raise Exception("cancelled by user")
        if status == "downloading":
            # yt_dlp fornece uma string como "12.3%" em _percent_str
            percent_raw = d.get("_percent_str") or d.get("percent") or "0%"
            try:
                percent = float(str(percent_raw).replace("%", "").strip())
            except Exception:
                percent = 0.0
            # armazena progresso como número (0-100)
            r.set(f"download:{job_id}:progress", percent)
            r.set(f"download:{job_id}:status", "downloading")
            _log_structured("progress", {"job_id": job_id, "progress": percent})

        elif status == "finished":
            # quando finalizado, marcamos processamento
            r.set(f"download:{job_id}:progress", 100)
            r.set(f"download:{job_id}:status", "processing")
            _log_structured("download_finished", {"job_id": job_id})

    ydl_opts = {
        "progress_hooks": [hook],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s-%(id)s.%(ext)s"),
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "js-runtimes": ["node"],
        "quiet": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # processamento pós-download (se necessário)
        r.set(f"download:{job_id}:status", "done")
        r.set(f"download:{job_id}:progress", 100)
        _log_structured("job_done", {"job_id": job_id})

    except Exception as e:
        # registra erro estruturado
        _log_structured("job_exception", {"job_id": job_id, "error": str(e)})

        # se foi cancelado explicitamente, marcar como cancelled e não re-enfileirar
        if r.get(cancel_key):
            r.set(f"download:{job_id}:status", "cancelled")
            r.set(f"download:{job_id}:error", "cancelled by user")
            r.lpush("queue:downloads:dead", job_id)
            _log_structured("job_cancelled", {"job_id": job_id})
            return

        # contador de tentativas
        attempts_key = f"download:{job_id}:attempts"
        attempts = int(r.get(attempts_key) or 0) + 1
        r.set(attempts_key, attempts)

        if attempts >= MAX_RETRIES:
            # excedeu tentativas: enviar para Dead Letter Queue e marcar failed
            r.set(f"download:{job_id}:status", "failed")
            r.set(f"download:{job_id}:error", str(e))
            r.lpush("queue:downloads:dead", job_id)
            _log_structured("job_failed", {"job_id": job_id, "attempts": attempts})
        else:
            # re-enfileira para retry com backoff
            r.set(f"download:{job_id}:status", "queued")
            _log_structured("job_retry", {"job_id": job_id, "attempts": attempts})
            time.sleep(RETRY_BACKOFF * attempts)
            r.lpush("queue:downloads", job_id)

    finally:
        # garantir liberação do lock
        release_lock(job_id)


def _main_loop():
    _log_structured("worker_start", {"worker_id": WORKER_ID})
    while not shutdown_requested:
        try:
            # blpop com timeout para poder checar shutdown_requested
            item = r.blpop("queue:downloads", timeout=5)
            if item:
                _, job_id = item
                url = r.get(f"download:{job_id}:url")
                process_job(job_id, url)
        except Exception as e:
            _log_structured("loop_exception", {"error": str(e)})
            time.sleep(1)

    _log_structured("worker_stopping", {"worker_id": WORKER_ID})


if __name__ == "__main__":
    _main_loop()