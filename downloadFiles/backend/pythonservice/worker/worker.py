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


# Configuração do Redis vinda do ambiente
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASS = os.getenv('REDIS_PASSWORD')
if REDIS_PASS and not REDIS_PASS.strip():
    REDIS_PASS = None
elif not REDIS_PASS:
    REDIS_PASS = None

# Pool de conexões Redis - reutiliza conexões em vez de criar novas
_redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    decode_responses=True,
    max_connections=10,
    socket_connect_timeout=5,
    socket_timeout=5,
    retry_on_timeout=True,
)

def get_redis_connection():
    try:
        client = redis.Redis(connection_pool=_redis_pool)
        client.ping()
        return client
    except Exception as e:
        print(f"Erro ao conectar ao Redis no Worker: {e}")
        return None

r = get_redis_connection()
if not r:
    print("ERRO: Não foi possível estabelecer conexão inicial com o Redis.")


# diretório padrão de download (lido do redis se existir)
DOWNLOAD_PATH_DEFAULT = Path.home() / "Downloads"
    

# Configurações de worker
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
    # Usar pipeline para buscar múltiplas chaves de uma vez - reduz round-trips
    pipe = r.pipeline(transaction=False)
    pipe.get(f"download:{job_id}:user_id")
    pipe.get(f"download:{job_id}:url")
    pipe.get(f"download:{job_id}:cancel")
    pipe.get(f"download:{job_id}:type")
    pipe.get(f"download:{job_id}:format")
    results = pipe.execute()
    
    user_id = results[0]
    url = results[1]
    cancel_flag = results[2]
    job_type_raw = results[3]
    job_format = results[4]

    if not url:
        pipe = r.pipeline(transaction=False)
        pipe.set(f"download:{job_id}:status", "error")
        pipe.set(f"download:{job_id}:error", "URL não encontrada")
        pipe.execute()
        _log_structured("job_error", {"job_id": job_id, "reason": "url not found"})
        return

    # se já existe sinal de cancelamento antes de começar, aborta
    if cancel_flag:
        r.set(f"download:{job_id}:status", "cancelled")
        _log_structured("job_cancelled_pre", {"job_id": job_id})
        return

    # tenta adquirir lock, se não conseguir, outro worker já está processando
    locked = acquire_lock(job_id)
    if not locked:
        _log_structured("lock_skip", {"job_id": job_id})
        return

    # marca que estamos processando (pipeline)
    pipe = r.pipeline(transaction=False)
    pipe.set(f"download:{job_id}:status", "downloading")
    pipe.set(f"download:{job_id}:progress", 0)
    pipe.sadd(f"user:{user_id}:jobs", job_id)
    pipe.execute()

    cancel_key = f"download:{job_id}:cancel"
    
    # Throttle: só envia progresso ao Redis a cada 500ms para reduzir I/O
    _last_progress_time = [0.0]
    PROGRESS_THROTTLE_MS = 500

    def hook(d):
        status = d.get("status")
        # respeitar cancelamento durante o download
        if r.get(cancel_key):
            raise Exception("cancelled by user")
        if status == "downloading":
            now_ms = time.time() * 1000
            # Throttle: pula atualizações muito frequentes
            if (now_ms - _last_progress_time[0]) < PROGRESS_THROTTLE_MS:
                return
            _last_progress_time[0] = now_ms
            
            downloaded = int(d.get('downloaded_bytes') or 0)
            total = int(d.get("total_bytes") or d.get('total_bytes_estimate') or 0)

            info = d.get("info_dict") or {}
            stream_id = info.get("format_id") or "unknown"

            # Usar pipeline para ler e escrever de uma vez
            read_pipe = r.pipeline(transaction=False)
            read_pipe.get(f"download:{job_id}:last_downloaded:{stream_id}")
            read_pipe.get(f"download:{job_id}:bytes_accumulated")
            read_results = read_pipe.execute()
            
            try:
                last = int(read_results[0] or 0)
            except Exception:
                last = 0
            
            try:
                accum = int(read_results[1] or 0)
            except Exception:
                accum = 0

            if downloaded >= last:
                delta = downloaded - last
            else:
                delta = downloaded

            accum += max(0, delta)

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

            # Pipeline de escrita - todas as operações em um único round-trip
            write_pipe = r.pipeline(transaction=False)
            write_pipe.incrby(f"user:{user_id}:total_bytes", delta)
            write_pipe.incrby("global:total_bytes", delta)
            write_pipe.set(f"download:{job_id}:bytes_accumulated", accum)
            write_pipe.set(f"download:{job_id}:last_downloaded:{stream_id}", downloaded)
            write_pipe.set(f"download:{job_id}:progress", percent, 2)
            write_pipe.set(f"download:{job_id}:status", "downloading")
            write_pipe.execute()

            _log_structured("progress", {"job_id": job_id, "progress": round(percent, 1)})

        elif status == "finished":
            r.set(f"download:{job_id}:status", "processing")
            _log_structured("stream_finished", {"job_id": job_id})

    # aqui determina o tipo de job enviado do usuário
    job_type = (job_type_raw or "video").lower()

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

    # Pipeline para ler configurações de qualidade
    q_pipe = r.pipeline(transaction=False)
    q_pipe.get(f"download:{job_id}:video_quality")
    q_pipe.get("settings:video:quality")
    q_pipe.get(f"download:{job_id}:audio_quality")
    q_pipe.get("settings:audio:quality")
    q_results = q_pipe.execute()
    
    raw_vq = q_results[0] or q_results[1]
    raw_aq = q_results[2] or q_results[3] or "192"

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
        
    
    # Localizar o FFmpeg de forma portátil
    base_path = Path(__file__).resolve().parent.parent.parent
    ffmpeg_bin = base_path / "bin" / "ffmpeg" / "ffmpeg.exe"
    
    # Se não achar o interno (em dev), tenta o do sistema
    ffmpeg_location = str(ffmpeg_bin) if ffmpeg_bin.exists() else None

    # opções base comuns
    ydl_opts = {
        "progress_hooks": [hook],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s_%(format_id)s.%(ext)s"),
        "ffmpeg_location": ffmpeg_location,
        "js-runtimes": ["node"],
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        },
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 5,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }

    fmt_option = None  

    if job_type == "audio" or desired_format in audio_formats:
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
        
        # Pipeline final: salva metadata + marca como concluído em um round-trip
        try:
            done_pipe = r.pipeline(transaction=False)
            done_pipe.set(f"download:{job_id}:info", json.dumps(metadata, ensure_ascii=False))
            done_pipe.sadd("downloads:completed", job_id)
            done_pipe.sadd(f"user:{user_id}:downloads:completed", job_id)
            done_pipe.set(f"download:{job_id}:status", "done")
            done_pipe.set(f"download:{job_id}:progress", 100)
            done_pipe.execute()
            
            _log_structured("job_done", {
                "job_id": job_id,
                "size": metadata["size"],
                "title": metadata["title"]
            })
        except Exception as e:
            _log_structured("metadata_store_error", {"job_id": job_id, "error": str(e)})

    except Exception as e:
        _log_structured("job_exception", {"job_id": job_id, "error": str(e)})

        if r.get(cancel_key):
            pipe = r.pipeline(transaction=False)
            pipe.set(f"download:{job_id}:status", "cancelled")
            pipe.set(f"download:{job_id}:error", "cancelled by user")
            pipe.lpush("queue:downloads:dead", job_id)
            pipe.execute()
            _log_structured("job_cancelled", {"job_id": job_id})
            return

        attempts_key = f"download:{job_id}:attempts"
        attempts = int(r.get(attempts_key) or 0) + 1
        r.set(attempts_key, attempts)

        if attempts >= MAX_RETRIES:
            pipe = r.pipeline(transaction=False)
            pipe.set(f"download:{job_id}:status", "failed")
            pipe.set(f"download:{job_id}:error", str(e))
            pipe.lpush("queue:downloads:dead", job_id)
            pipe.execute()
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
    
    if r is None:
        _log_structured("connection_error", {"error": "Redis client is None. Connection failed."})
        return

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
