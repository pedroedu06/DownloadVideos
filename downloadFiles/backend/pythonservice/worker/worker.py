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

# diretório padrao de download (lido do redis se existir)
# função DEFAULT criada mas não implementada pelo dev (vai lançar NotImplementedError)
DOWNLOAD_PATH_DEFAULT = Path.home() / "Downloads"
    

# Configuracoes de worker, como maximo de retrys, tempo de Lock na fila e segundos de espera para cada tentativa
MAX_RETRIES = 3
LOCK_TTL = 60 * 60  # 1 hora
RETRY_BACKOFF = 5  # segundos entre tentativas

# tipo de indentidade de caracter para o worker.
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

#aqui ele coloca o lock em cada worker para nao ter o mesmo worker funcionando varias vezes
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

    # tenta adquirir lock, se não conseguir, outro worker já está processando
    locked = acquire_lock(job_id)
    if not locked:
        _log_structured("lock_skip", {"job_id": job_id})
        # re-enfileira para tentar depois curto retorno ou simplesmente retorna
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
            downloaded = d.get('downloaded_bytes', 0)
            total = (d.get("total_bytes") or d.get('total_bytes_estimate') or 0)

            percent = 0.0

            if total > 0:
                percent = downloaded / total * 100
            else:
                frag_index = d.get("fragment_index")
                frag_count = d.get("fragment_count")

                if frag_index and frag_count:
                    percent = (frag_index / frag_count) * 100
            
            r.set(f"download:{job_id}:progress", percent, 2)
            r.set(f"download:{job_id}:status", "downloading")
            _log_structured("progress", {"job_id": job_id, "progress": percent})

        elif status == "finished":
            # quando finalizado, marcamos processamento
            r.set(f"download:{job_id}:progress", 100)
            r.set(f"download:{job_id}:status", "processing")
            _log_structured("download_finished", {"job_id": job_id})

    # Determinar tipo do job: 'video' (default) ou 'audio'
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

    #Normaliza o valor da qualidade
    def normalize_quality(q):
        if not q:
            return None
        q = str(q).lower().strip()
        q = q.replace("p", "").replace("fps", "")
        return q if q.isdigit() else None

    #e retorna os valores necessarios
    raw_vq = (
    r.get(f"download:{job_id}:video_quality")
    or r.get("settings:video:quality"))

    #pro audio e a mesma coisa que o video, so que mais simples.
    raw_aq = (
    r.get(f"download:{job_id}:audio_quality")
    or r.get("settings:audio:quality")
    or "192")

    audio_quality = raw_aq.strip() if raw_aq.isdigit() else "192"

    video_quality = normalize_quality(raw_vq)

    # formatos suportados para extrair audio
    audio_formats = {"mp3", "wav", "aac", "m4a", "opus", "flac"}

    # Determinar DOWNLOAD_DIR: usar valor em redis se existir, senão tentar DEFAULT, senão fallback env
    download_dir_raw = r.get("download:dir")
    try:
        if download_dir_raw:
            DOWNLOAD_DIR = Path(download_dir_raw)
        else:
            try:
                DOWNLOAD_DIR = Path(DOWNLOAD_PATH_DEFAULT)
            except NotImplementedError:
                DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_PATH', '/downloads'))
    except Exception:
        DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_PATH', '/downloads'))
        
    
    # opções base comuns
    ydl_opts = {
        "progress_hooks": [hook],
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s-%(id)s.%(ext)s"),
        "js-runtimes": ["node"],
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
        print("RAW VQ:", raw_vq)
        print("qualidade video", video_quality)
        print("formato desejado", fmt_option)
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

#aqui encerra o worker, caso requisitado pelo dev.
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