# DownloadFiles

DownloadFiles is a desktop YouTube downloader built with Tauri, React, TypeScript, FastAPI, and a bundled Python runtime. The application is designed as a local-first desktop system: the frontend runs inside a Tauri window, the API and worker run as local Python processes, SQLite stores durable state, and WebSocket streams carry live download progress to the UI.

This repository uses a nested app folder:

- `downloadFiles/`: main application source
- `downloadFiles/src/`: React frontend
- `downloadFiles/src-tauri/`: Tauri desktop shell and process orchestration
- `downloadFiles/backend/pythonservice/`: Python API and worker
- `downloadFiles/backend/bin/`: bundled Python and FFmpeg runtime for packaging

## Architecture Overview

At runtime the app is composed of four major layers:

1. `Tauri shell`
   The Rust desktop layer starts the window, spawns the Python API and Python worker, resolves resource paths for dev and packaged builds, and shuts both processes down when the window closes.

2. `React frontend`
   The UI provides the home page, settings page, and download history page. It communicates with the local FastAPI service through HTTP for commands and WebSocket for real-time progress.

3. `FastAPI service`
   The API accepts download requests, stores jobs and settings in SQLite, exposes history and configuration endpoints, and broadcasts download progress over WebSocket by observing database changes.

4. `Worker process`
   The worker continuously polls the SQLite-backed queue, claims pending jobs atomically, runs `yt-dlp`, updates job progress/status, and persists the final download metadata.

## Why SQLite + WebSocket

The current architecture removes Redis entirely and replaces it with two local mechanisms that better fit a desktop application:

- `SQLite`
  Used as the durable source of truth for:
  - queued jobs
  - retry scheduling
  - cancellation flags
  - user download history
  - download settings
  - target download directory

- `WebSocket`
  Used only for low-latency progress delivery from the backend to the frontend.

The key design principle is separation of responsibilities:

- `SQLite` owns durable state.
- `WebSocket` owns live state delivery.

That means the app can recover after crashes or restarts because the queue and download history live in the database, while the progress stream remains lightweight and transient.

## End-to-End Runtime Flow

### 1. App startup

When the Tauri app starts:

- the Rust layer resolves bundled resource paths
- it spawns the Python API process
- it spawns the Python worker process
- both processes run from `backend/pythonservice`
- the API initializes the SQLite schema if needed
- the worker recovers interrupted jobs and requeues unfinished work

Important runtime entrypoints:

- `downloadFiles/src-tauri/src/main.rs`
- `downloadFiles/backend/pythonservice/bootstrap_api.py`
- `downloadFiles/backend/pythonservice/bootstrap_worker.py`

### 2. Home page workflow

On the home page:

- the user pastes a YouTube URL or clicks a video from the feed
- the frontend requests preview metadata from `POST /getInfoVideo`
- the user selects `video` or `audio`
- the frontend posts a new job to `POST /downloadtask`
- the API inserts a row in SQLite with `status='queued'`
- the UI opens a progress card for that job
- the progress card fetches initial status through HTTP
- the progress card then subscribes to `ws://localhost:8000/ws/downloads/{job_id}`

### 3. Worker queue processing

The worker loop:

- checks SQLite for the oldest eligible queued job
- uses an atomic claim inside a transaction
- marks the row as `downloading`
- runs `yt-dlp`
- writes progress back into the same row
- marks the job as `processing` when the media stream is finished
- persists final metadata when the file is done
- marks the job `done`, `failed`, or `cancelled`

### 4. Progress delivery

The API keeps a `ProgressManager` in memory. It does not execute the download itself. Instead, it:

- tracks WebSocket clients by `job_id`
- polls the relevant rows in SQLite at a short interval
- compares the latest payload with the last payload sent
- broadcasts only when progress or status changes

This produces a local push-like UX without introducing an external message broker.

## SQLite Data Model

The SQLite schema is defined in:

- `downloadFiles/backend/pythonservice/api/sqliteClient.py`

### `downloads` table

This table is both the queue and the job history.

Core columns:

- `job_id`: primary key
- `url`: original requested URL
- `user_id`: local per-user identifier generated in the frontend
- `type`: `video` or `audio`
- `status`: queue and lifecycle state
- `progress`: numeric progress percentage
- `cancel_requested`: cancellation signal for the worker
- `attempt_count`: retry counter
- `next_attempt_at`: retry scheduling timestamp
- `worker_id`: current worker owner
- `source_id`: source platform video ID
- `title`: final or discovered title
- `thumbnail`: thumbnail URL
- `filename`: generated output filename
- `filepath`: absolute output path
- `size`: final file size
- `error`: error payload for failed jobs
- `created_at`, `updated_at`, `completed_at`: lifecycle timestamps

This model replaces multiple Redis key families with one normalized, queryable structure.

### `settings` table

The `settings` table stores app-level configuration:

- `download_path`
- `default_video_format`
- `default_audio_format`
- `video_quality`
- `audio_quality`

All settings are persisted with simple key/value rows and updated via an upsert.

## Queue Design

The queue is implemented directly in SQLite using the `downloads` table.

### Queue states

Typical job states:

- `queued`
- `downloading`
- `processing`
- `done`
- `failed`
- `cancelled`

### Queue selection strategy

The worker claims jobs by:

- starting an immediate transaction
- selecting the oldest row where:
  - `status = 'queued'`
  - `cancel_requested = 0`
  - `next_attempt_at <= CURRENT_TIMESTAMP`
- updating that same row to `downloading`

This gives the app a simple single-consumer queue with durable retry scheduling and transactional ownership.

### Retry behavior

If a job fails:

- `attempt_count` is incremented
- `next_attempt_at` is shifted into the future
- the job returns to `queued` if retries remain
- the job becomes `failed` when `MAX_RETRIES` is reached

### Recovery behavior

On worker startup, `recover_incomplete_downloads()` resets interrupted jobs:

- `downloading` or `processing` jobs become `queued`
- already cancelled jobs remain `cancelled`
- `worker_id` is cleared
- `next_attempt_at` is reset to current time

This is the mechanism that makes the queue restart-safe without Redis.

## WebSocket Progress Model

The WebSocket endpoint is:

- `GET ws://localhost:8000/ws/downloads/{job_id}`

The frontend component:

- fetches the initial state from `GET /downloadStatus/{job_id}`
- connects to the socket
- updates the progress card from push events
- reconnects automatically if the socket drops before terminal completion

The API sends payloads shaped like:

```json
{
  "job_id": "uuid",
  "status": "downloading",
  "progress": 42.5,
  "error": null,
  "title": "Some Video"
}
```

The WebSocket layer is intentionally stateless beyond active connections. If the app disconnects, the source of truth remains SQLite.

## Worker Internals

The worker lives in:

- `downloadFiles/backend/pythonservice/worker/worker.py`

### Main responsibilities

- queue polling
- atomic job claiming
- download execution through `yt-dlp`
- cancellation checks
- progress persistence
- retry scheduling
- final metadata extraction

### Download pipeline

For each claimed job, the worker:

1. loads download settings from SQLite
2. resolves output directory
3. resolves FFmpeg location
4. builds `yt-dlp` options
5. registers a progress hook
6. writes progress updates to SQLite
7. extracts final file path and size
8. stores terminal metadata in the `downloads` row

### Cancellation model

Cancellation is database-driven:

- the API sets `cancel_requested = 1`
- the worker checks that flag before and during download
- the `yt-dlp` progress hook raises `DownloadCancelled` if the flag is set
- the row ends in `cancelled`

### Output handling

The worker supports:

- video downloads using merged formats
- audio extraction using FFmpeg post-processors
- configurable output format and quality

It derives the final path and file size after `yt-dlp` completes and persists that information for the history page.

## FastAPI Service

The API lives in:

- `downloadFiles/backend/pythonservice/api/main.py`

### Main responsibilities

- schema initialization
- request validation
- queue insertion
- job status lookup
- progress WebSocket management
- settings persistence
- history queries
- feed and preview caching

### Important endpoints

#### Feed and preview

- `GET /feed`
  Returns a curated feed of YouTube content.

- `POST /getInfoVideo`
  Resolves a YouTube URL into preview metadata such as title and thumbnail.

#### Downloads

- `POST /downloadtask`
  Inserts a queued job into SQLite.

- `GET /downloadStatus/{job_id}`
  Returns current status, progress, and error state.

- `POST /downloadCancel/{job_id}`
  Marks cancellation in SQLite.

- `WS /ws/downloads/{job_id}`
  Streams job progress to the UI.

#### Settings and persistence

- `POST /downloadPath`
  Saves the default output directory.

- `POST /downloadSettings`
  Saves video/audio format and quality defaults.

- `GET /list_downloads`
  Returns all completed downloads.

- `GET /userDownload/{user_id}/downloads`
  Returns completed downloads for a specific local user.

- `POST /deletCache`
  Clears in-memory API caches.

- `POST /deletuserSettings`
  Clears persisted app settings from SQLite.

## Frontend Structure

The React frontend lives in:

- `downloadFiles/src/`

### Core pages

- `pages/home/home.tsx`
  Main search/download page with the right-side progress drawer.

- `pages/settings/settings.tsx`
  Theme, path, audio/video format, quality, maintenance actions.

- `pages/historico/history.tsx`
  History page and filter controls.

### Important frontend behaviors

#### Local user identity

`src/App.tsx` creates a local `user_id` and stores it in `localStorage`. This value is used to associate downloads with a local user without requiring authentication.

#### Download preview and enqueue

`home.tsx`:

- sends preview requests to the API
- opens a format-selection modal
- creates a queued download
- creates a live progress card immediately after job creation

#### Live progress card

`CardDownloadprogress.tsx`:

- fetches initial status over HTTP
- opens the WebSocket stream
- updates the card in real time
- closes the socket automatically when the job reaches a terminal state
- posts cancellation requests when the close button is pressed

#### History page

`historicoGrid.tsx`:

- fetches user-specific completed downloads
- sorts by date, size, or type
- renders file path, size, relative time, and media type

## Tauri Process Orchestration

The desktop shell is implemented in:

- `downloadFiles/src-tauri/src/main.rs`

### What Tauri does

- launches the desktop window
- resolves resource paths for dev and packaged builds
- starts the API process
- starts the worker process
- captures process output for logging
- kills child processes when the window closes

### Important implementation details

- the API is skipped if port `8000` is already in use
- bundled Python paths are configured dynamically
- `PYTHONDONTWRITEBYTECODE=1` is set to reduce `__pycache__` and `.pyc` lock issues on Windows
- Windows child processes are created with `CREATE_NO_WINDOW`

## Bootstrapping the Python Runtime

The Python bootstraps:

- load `api/.env` manually
- add the bundled Python DLL directory
- extend `sys.path` to include:
  - service root
  - bundled `site-packages`
  - bundled `python312.zip`

This makes the app self-contained and reduces dependency on a system Python installation.

## Development Notes

### Main commands

From `downloadFiles/`:

```bash
npm run dev
```

```bash
npm run build
```

```bash
npm run tauri dev
```

### Starting backend manually

From `downloadFiles/backend/pythonservice/`:

```powershell
..\bin\python\python.exe bootstrap_api.py
```

```powershell
..\bin\python\python.exe bootstrap_worker.py
```

### Database file

SQLite is stored at:

- `downloadFiles/backend/pythonservice/api/database.db`

The database uses:

- WAL journal mode
- foreign keys enabled
- `busy_timeout`
- per-thread connection reuse

## Failure Handling and Resilience

The app includes several resilience strategies:

- restart-safe queue recovery through SQLite
- retry scheduling through `attempt_count` and `next_attempt_at`
- explicit cancel flag checked during active downloads
- in-memory API caches isolated from durable state
- frontend WebSocket reconnection for non-terminal jobs
- terminal status persisted even if the UI is closed

## Current Tradeoffs

The current design is pragmatic and well-suited for a local desktop app, but it has explicit tradeoffs:

- the WebSocket broadcaster currently polls SQLite rather than subscribing to database events
- the queue model is optimized for a single local worker, not a distributed cluster
- settings are global key/value rows rather than normalized per-user preferences
- some frontend/API labels and endpoint names still reflect the original project naming style

These are acceptable tradeoffs for a local single-machine downloader and keep the system significantly simpler than a Redis-backed architecture.

## Key Files

- `downloadFiles/src-tauri/src/main.rs`
- `downloadFiles/backend/pythonservice/bootstrap_api.py`
- `downloadFiles/backend/pythonservice/bootstrap_worker.py`
- `downloadFiles/backend/pythonservice/api/main.py`
- `downloadFiles/backend/pythonservice/api/sqliteClient.py`
- `downloadFiles/backend/pythonservice/worker/worker.py`
- `downloadFiles/src/pages/home/home.tsx`
- `downloadFiles/src/components/CardDownloadprogress.tsx`
- `downloadFiles/src/pages/settings/settings.tsx`
- `downloadFiles/src/pages/componetsHistory/historicoGrid.tsx`

## Summary

DownloadFiles is a desktop application where:

- Tauri owns the desktop runtime and local process lifecycle
- React owns the user experience
- FastAPI owns orchestration and API access
- SQLite owns durable queue/history/settings state
- WebSocket owns live progress delivery
- the worker owns actual media download execution

That combination gives the app a local-first architecture with durable jobs, restart-safe history, and real-time progress without requiring Redis or any external infrastructure.
