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


# redis client, no config dos locks necessita.
REDIS_CLIENT = os.getenv('REDIS_HOST', 'localhost')
r = redis.Redis(host=REDIS_CLIENT, port=6379, decode_responses=True)

# diretório padrão de download (lido do redis se existir)
DOWNLOAD_PATH_DEFAULT = Path.home() / "Downloads"
    

# Configurações de worker, como máximo de retries, tempo de Lock na fila e segundos de espera para cada tentativa
MAX_RETRIES = 3
LOCK_TTL = 60 * 60  # 1 hora
RETRY_BACKOFF = 5  # segundos entre tentativas

# tipo de identidade de caracter para o worker.
WORKER_ID = str(uuid.uuid4())

# logs estruturados em JSON para facilitar parsing
logger = logging.getLogger("download_worker")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _log_structured(event: str, extra: dict):
    payload = {"event": event, **extra}
    logger.info(json.dumps(payload, ensure_ascii=False))


# tenta colocar o lock em NX caso precise.
def acquire_lock(job_id: str) -> bool:
    lock_key = f"download:{job_id}:lock"
    return r.set(lock_key, WORKER_ID, nx=True, ex=LOCK_TTL)

# aqui ele coloca o lock em cada worker para não ter o mesmo worker funcionando várias vezes
def release_lock(job_id: str) -> None:
    lock_key = f"download:{job_id}:lock"
    try:
        val = r.get(lock_key)
        if val == WORKER_ID:
            r.delete(lock_key)
    except Exception:
        pass


# aqui funciona o encerramento do worker.
shutdown_requested = False

def _signal_handler(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    _log_structured("shutdown_request", {"signal": signum})


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def process_job(job_id: str):
    user_id = r.get(f"download:{job_id}:user_id")
    url = r.get(f"download:{job_id}:url")

    if not url:
        r.set(f"download:{job_id}:status", "error")
        r.set(f"download:{job_id}:error", "URL não encontrada")
        _log_structured("job_error", {"job_id": job_id, "reason": "url not found"})
        return

    # se já existe sinal de cancelamento antes de começar, aborta
    cancel_key = f"download:{job_id}:cancel"
    if r.get(cancel_key):
        r.set(f"download:{job_id}:status", "cancelled")
        _log_structured("job_cancelled_pre", {"job_id": job_id})
        return

    # tenta adquirir lock, se não conseguir, outro worker já está processando
    locked = acquire_lock(job_id)
    if not locked:
        _log_structured("lock_skip", {"job_id": job_id})
        # re-enfileira para tentar depois ou simplesmente retorna
        return

    # marca que estamos processando
    r.set(f"download:{job_id}:status", "downloading")
    r.set(f"download:{job_id}:progress", 0)

    try: 
        r.sadd(f"user:{user_id}:jobs", job_id)
    except Exception:
        pass

    def hook(d):
        status = d.get("status")
        # respeitar cancelamento durante o download
        if r.get(cancel_key):
            raise Exception("cancelled by user")
        if status == "downloading":
            downloaded = int(d.get('downloaded_bytes') or 0)
            total = int(d.get("total_bytes") or d.get('total_bytes_estimate') or 0)

            info = d.get("info_dict") or {}
            stream_id = info.get("format_id") or "unknown"

            try:
                last_raw = r.get(f"download:{job_id}:last_downloaded:{stream_id}") or 0
                last = int(last_raw)
            except Exception:
                last = 0

            if downloaded >= last:
                delta = downloaded - last
            else:
                delta = downloaded

            try:
                accum_raw = r.get(f"download:{job_id}:bytes_accumulated") or 0
                accum = int(accum_raw)
            except Exception:
                accum = 0

            accum += max(0, delta)

            try:
                r.incrby(f"user:{user_id}:total_bytes", delta)
            except Exception:   
                pass
            
            try:
                 r.incrby("global:total_bytes", delta)
            except Exception:
                pass

            try:
                r.set(f"download:{job_id}:bytes_accumulated", accum)
                r.set(f"download:{job_id}:last_downloaded:{stream_id}", downloaded)
            except Exception:
                pass

            percent = 0.0
            if total > 0:
                percent = downloaded / total * 100
            else:
                frag_index = d.get("fragment_index")
                frag_count = d.get("fragment_count")
                if frag_index and frag_count:
                    try:
                        percent = (frag_index / frag_count) * 100
                    except Exception:
                        percent = 0.0

            r.set(f"download:{job_id}:progress", percent, 2)
            r.set(f"download:{job_id}:status", "downloading")
            _log_structured("progress", {"job_id": job_id, "progress": percent})

        elif status == "finished":
            # Stream terminou o download - yt-dlp fará o merge se necessário
            r.set(f"download:{job_id}:status", "processing")
            _log_structured("stream_finished", {"job_id": job_id})

    # aqui determina o tipo de job enviado do usuário
    job_type = (r.get(f"download:{job_id}:type") or "video").lower()

    # Ler o formato desejado salvo no job (tem prioridade)
    job_format = r.get(f"download:{job_id}:format")

    # se não tem formato no job, buscar defaults globais em redis conforme tipo
    if job_format:
        desired_format = job_format.lower()
    else:
        if job_type == "audio":
            desired_format = (r.get("settings:default:audio_format") or "mp3").lower()
        else:
            desired_format = (r.get("settings:default:video_format") or "mp4").lower()

    """Normaliza o valor da qualidade para somente a qualidade que o usuário quer.
    """
    def normalize_quality(q):
        if not q:
            return None
        q = str(q).lower().strip()
        q = q.replace("p", "").replace("fps", "")
        return q if q.isdigit() else None

    # retorna os valores necessários
    raw_vq = (
    r.get(f"download:{job_id}:video_quality")
    or r.get("settings:video:quality"))

    # pro áudio é a mesma coisa que o vídeo, só que mais simples.
    raw_aq = (
    r.get(f"download:{job_id}:audio_quality")
    or r.get("settings:audio:quality")
    or "192")

    audio_quality = raw_aq.strip() if raw_aq.isdigit() else "192"
    video_quality = normalize_quality(raw_vq)

    # formatos suportados para extrair áudio
    audio_formats = {"mp3", "wav", "aac", "m4a", "opus", "flac"}

    # Determinar DOWNLOAD_DIR: usar valor em redis se existir, senão DEFAULT
    download_dir_raw = r.get("download:dir")

    try:
        if download_dir_raw:
            DOWNLOAD_DIR = Path(download_dir_raw)
        else:
            DOWNLOAD_DIR = DOWNLOAD_PATH_DEFAULT
    except Exception:
        DOWNLOAD_DIR = Path.home() / 'Downloads'
        
    
    # opções base comuns
    ydl_opts = {
        "progress_hooks": [hook],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s_%(format_id)s.%(ext)s"),
        "js-runtimes": ["node"],
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        },
        "retries": 3,
        "fragment_retries": 3,
    }

    fmt_option = None  

    if job_type == "audio" or desired_format in audio_formats:
        # extrair apenas o áudio e converter para o codec desejado
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": desired_format,
                "preferredquality": str(audio_quality),
            }],
        })
    
    else:
        if video_quality:
            fmt_option = f"bv*[height<={video_quality}]+ba/b"
        else:
            fmt_option = "bv*+ba/b"

        ydl_opts.update({
            "format": fmt_option,
            "merge_output_format": desired_format if desired_format else "mp4"
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)

        # Post-download: collect metadata from the actual final file
        r.set(f"download:{job_id}:status", "processing")
        
        final_filename = None
        filepath = None
        filesize = None
        
        try:
            if info_dict:
                final_filename = ydl.prepare_filename(info_dict)
                
                if final_filename:
                    p = Path(final_filename)
                    
                    if not p.exists():
                        if job_type == "audio" or desired_format in audio_formats:
                            base = p.with_suffix('')
                            p = Path(str(base) + f".{desired_format}")
                        elif desired_format:
                            base = p.with_suffix('')
                            p = Path(str(base) + f".{desired_format}")
                    
                    if p.exists():
                        filepath = str(p.resolve())
                        filesize = p.stat().st_size
                        _log_structured("file_size_from_disk", {
                            "job_id": job_id, 
                            "size": filesize,
                            "path": filepath
                        })
        except Exception as e:
            _log_structured("metadata_extraction_error", {"job_id": job_id, "error": str(e)})
        
        if filesize is None:
            filesize = int(r.get(f"download:{job_id}:bytes_accumulated") or 0)
        
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        metadata = {
            "id": info_dict.get("id") if info_dict else None,
            "title": info_dict.get("title") if info_dict else None,
            "filename": Path(final_filename).name if final_filename else None,
            "path": filepath,
            "size": int(filesize) if filesize is not None else None,
            "type": job_type,
            "created_at": created_at,
        }
        
        try:
            r.set(f"download:{job_id}:info", json.dumps(metadata, ensure_ascii=False))
            r.sadd("downloads:completed", job_id)
            r.sadd(f"user:{user_id}:downloads:completed", job_id)
            _log_structured("metadata_saved", {
                "job_id": job_id,
                "size": metadata["size"],
                "title": metadata["title"]
            })
        except Exception as e:
            _log_structured("metadata_store_error", {"job_id": job_id, "error": str(e)})

        r.set(f"download:{job_id}:status", "done")
        r.set(f"download:{job_id}:progress", 100)
        _log_structured("job_done", {"job_id": job_id})

    except Exception as e:
        _log_structured("job_exception", {"job_id": job_id, "error": str(e)})

        if r.get(cancel_key):
            r.set(f"download:{job_id}:status", "cancelled")
            r.set(f"download:{job_id}:error", "cancelled by user")
            r.lpush("queue:downloads:dead", job_id)
            _log_structured("job_cancelled", {"job_id": job_id})
            return

        attempts_key = f"download:{job_id}:attempts"
        attempts = int(r.get(attempts_key) or 0) + 1
        r.set(attempts_key, attempts)

        if attempts >= MAX_RETRIES:
            r.set(f"download:{job_id}:status", "failed")
            r.set(f"download:{job_id}:error", str(e))
            r.lpush("queue:downloads:dead", job_id)
            _log_structured("job_failed", {"job_id": job_id, "attempts": attempts})
        else:
            r.set(f"download:{job_id}:status", "queued")
            _log_structured("job_retry", {"job_id": job_id, "attempts": attempts})
            time.sleep(RETRY_BACKOFF * attempts)
            r.lpush("queue:downloads", job_id)

    finally:
        release_lock(job_id)

# aqui encerra o worker, caso requisitado.
def _main_loop():
    _log_structured("worker_start", {"worker_id": WORKER_ID})
    while not shutdown_requested:
        try:
            item = r.blpop("queue:downloads", timeout=5)
            if item:
                _, job_id = item
                process_job(job_id)
        except Exception as e:
            _log_structured("loop_exception", {"error": str(e)})
            time.sleep(1)

    _log_structured("worker_stopping", {"worker_id": WORKER_ID})


if __name__ == "__main__":
    _main_loop()
