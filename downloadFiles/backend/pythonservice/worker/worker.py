from __future__ import annotations

import json
import logging
import signal
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from yt_dlp import YoutubeDL

from api.sqliteClient import create_table, get_db, get_setting, recover_incomplete_downloads


DOWNLOAD_PATH_DEFAULT = Path.home() / "Downloads"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5
POLL_INTERVAL_SECONDS = 1
PROGRESS_THROTTLE_MS = 500
WORKER_ID = str(uuid.uuid4())


logger = logging.getLogger("download_worker")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


shutdown_requested = False


class DownloadCancelled(Exception):
    pass


def _log_structured(event: str, extra: dict[str, Any]) -> None:
    logger.info(json.dumps({"event": event, **extra}, ensure_ascii=False))


def _signal_handler(signum, _frame) -> None:
    global shutdown_requested
    shutdown_requested = True
    _log_structured("shutdown_request", {"signal": signum})


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def _utc_db_timestamp(offset_seconds: int = 0) -> str:
    target = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return target.strftime("%Y-%m-%d %H:%M:%S")


def _normalize_quality(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    normalized = str(value).strip().lower().replace("p", "").replace("fps", "")
    return normalized if normalized.isdigit() else None


def _update_download(job_id: str, **fields: Any) -> None:
    if not fields:
        return

    db = get_db()
    assignments = []
    values = []

    for key, value in fields.items():
        assignments.append(f"{key} = ?")
        values.append(value)

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    values.append(job_id)

    db.execute(
        f"UPDATE downloads SET {', '.join(assignments)} WHERE job_id = ?",
        values,
    )


def _get_job(job_id: str) -> Optional[Any]:
    return get_db().execute(
        """
        SELECT job_id, url, user_id, type, status, progress, cancel_requested, attempt_count
        FROM downloads
        WHERE job_id = ?
        """,
        (job_id,),
    ).fetchone()


def _claim_next_job() -> Optional[Any]:
    db = get_db()
    db.execute("BEGIN IMMEDIATE")

    try:
        row = db.execute(
            """
            SELECT job_id
            FROM downloads
            WHERE status = 'queued'
              AND cancel_requested = 0
              AND datetime(next_attempt_at) <= CURRENT_TIMESTAMP
            ORDER BY datetime(created_at) ASC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            db.execute("COMMIT")
            return None

        updated = db.execute(
            """
            UPDATE downloads
            SET
                status = 'downloading',
                progress = 0,
                worker_id = ?,
                error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ? AND status = 'queued'
            """,
            (WORKER_ID, row["job_id"]),
        ).rowcount

        db.execute("COMMIT")
        if updated != 1:
            return None

        return _get_job(row["job_id"])
    except Exception:
        db.execute("ROLLBACK")
        raise


def _is_cancel_requested(job_id: str) -> bool:
    row = get_db().execute(
        "SELECT cancel_requested FROM downloads WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    return bool(row and row["cancel_requested"])


def _resolve_download_dir() -> Path:
    configured_path = get_setting("download_path")

    try:
        directory = Path(configured_path) if configured_path else DOWNLOAD_PATH_DEFAULT
    except Exception:
        directory = DOWNLOAD_PATH_DEFAULT

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _resolve_ffmpeg_location() -> Optional[str]:
    base_path = Path(__file__).resolve().parent.parent.parent
    ffmpeg_bin = base_path / "bin" / "ffmpeg" / "ffmpeg.exe"
    return str(ffmpeg_bin) if ffmpeg_bin.exists() else None


def _determine_output_format(job_type: str) -> tuple[str, Optional[str], str]:
    audio_formats = {"mp3", "wav", "aac", "m4a", "opus", "flac"}

    if job_type == "audio":
        desired_format = (get_setting("default_audio_format", "mp3") or "mp3").lower()
    else:
        desired_format = (get_setting("default_video_format", "mp4") or "mp4").lower()

    return desired_format, desired_format if desired_format in audio_formats else None, desired_format


def _build_ydl_options(job_id: str, job_type: str) -> dict[str, Any]:
    desired_format, audio_codec, merge_format = _determine_output_format(job_type)
    raw_video_quality = get_setting("video_quality")
    raw_audio_quality = get_setting("audio_quality", "192") or "192"

    video_quality = _normalize_quality(raw_video_quality)
    audio_quality = raw_audio_quality.strip() if str(raw_audio_quality).isdigit() else "192"
    download_dir = _resolve_download_dir()

    last_progress_time = [0.0]

    def hook(data: dict[str, Any]) -> None:
        if _is_cancel_requested(job_id):
            raise DownloadCancelled("cancelled by user")

        status = data.get("status")
        if status == "downloading":
            now_ms = time.time() * 1000
            if (now_ms - last_progress_time[0]) < PROGRESS_THROTTLE_MS:
                return
            last_progress_time[0] = now_ms

            downloaded = float(data.get("downloaded_bytes") or 0)
            total = float(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)

            percent = 0.0
            if total > 0:
                percent = downloaded / total * 100
            else:
                fragment_index = data.get("fragment_index")
                fragment_count = data.get("fragment_count")
                if fragment_index and fragment_count:
                    try:
                        percent = float(fragment_index) / float(fragment_count) * 100
                    except Exception:
                        percent = 0.0

            percent = max(0.0, min(100.0, percent))
            _update_download(job_id, status="downloading", progress=round(percent, 2))
            _log_structured("progress", {"job_id": job_id, "progress": round(percent, 1)})

        elif status == "finished":
            _update_download(job_id, status="processing")
            _log_structured("stream_finished", {"job_id": job_id})

    ydl_opts: dict[str, Any] = {
        "progress_hooks": [hook],
        "outtmpl": str(download_dir / "%(title)s_%(format_id)s.%(ext)s"),
        "ffmpeg_location": _resolve_ffmpeg_location(),
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

    if job_type == "audio" or audio_codec is not None:
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": desired_format,
                "preferredquality": audio_quality,
            }],
        })
    else:
        video_format = f"bv*[height<={video_quality}]+ba/b" if video_quality else "bv*+ba/b"
        ydl_opts.update({
            "format": video_format,
            "merge_output_format": merge_format or "mp4",
        })

    return ydl_opts


def _resolve_output_file(ydl: YoutubeDL, info_dict: dict[str, Any], job_type: str) -> tuple[Optional[str], Optional[str], Optional[int]]:
    desired_format, audio_codec, merge_format = _determine_output_format(job_type)

    try:
        prepared = ydl.prepare_filename(info_dict)
    except Exception:
        return None, None, None

    if not prepared:
        return None, None, None

    path = Path(prepared)
    if not path.exists():
        base = path.with_suffix("")
        if job_type == "audio" or audio_codec is not None:
            path = Path(f"{base}.{desired_format}")
        elif merge_format:
            path = Path(f"{base}.{merge_format}")

    if not path.exists():
        return Path(prepared).name, None, None

    resolved = path.resolve()
    return path.name, str(resolved), resolved.stat().st_size


def process_job(job: Any) -> None:
    job_id = job["job_id"]
    url = job["url"]
    job_type = (job["type"] or "video").lower()

    if not url:
        _update_download(
            job_id,
            status="failed",
            error="URL nao encontrada",
            worker_id=None,
        )
        _log_structured("job_error", {"job_id": job_id, "reason": "url not found"})
        return

    if _is_cancel_requested(job_id):
        _update_download(job_id, status="cancelled", error="cancelled by user", worker_id=None)
        _log_structured("job_cancelled_pre", {"job_id": job_id})
        return

    ydl_opts = _build_ydl_options(job_id, job_type)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)

            filename, filepath, filesize = _resolve_output_file(ydl, info_dict, job_type)

        source_id = info_dict.get("id") if info_dict else None
        title = info_dict.get("title") if info_dict else None
        thumbnail = info_dict.get("thumbnail") if info_dict else None

        _update_download(
            job_id,
            status="done",
            progress=100,
            source_id=source_id,
            title=title,
            thumbnail=thumbnail,
            filename=filename,
            filepath=filepath,
            size=filesize,
            error=None,
            completed_at=_utc_db_timestamp(),
            worker_id=None,
        )
        _log_structured("job_done", {"job_id": job_id, "title": title, "size": filesize})
    except DownloadCancelled as error:
        _update_download(job_id, status="cancelled", error=str(error), worker_id=None)
        _log_structured("job_cancelled", {"job_id": job_id})
    except Exception as error:
        attempts = int(job["attempt_count"] or 0) + 1
        _log_structured("job_exception", {"job_id": job_id, "error": str(error), "attempts": attempts})

        if attempts >= MAX_RETRIES:
            _update_download(
                job_id,
                status="failed",
                error=str(error),
                attempt_count=attempts,
                worker_id=None,
            )
            _log_structured("job_failed", {"job_id": job_id, "attempts": attempts})
            return

        _update_download(
            job_id,
            status="queued",
            progress=0,
            error=str(error),
            attempt_count=attempts,
            next_attempt_at=_utc_db_timestamp(RETRY_BACKOFF_SECONDS * attempts),
            worker_id=None,
        )
        _log_structured("job_retry", {"job_id": job_id, "attempts": attempts})


def _main_loop() -> None:
    create_table()
    recover_incomplete_downloads()
    _log_structured("worker_start", {"worker_id": WORKER_ID})

    while not shutdown_requested:
        try:
            job = _claim_next_job()
            if job is None:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            process_job(job)
        except Exception as error:
            _log_structured("loop_exception", {"error": str(error)})
            time.sleep(1)

    _log_structured("worker_stopping", {"worker_id": WORKER_ID})


if __name__ == "__main__":
    _main_loop()
