# 04 — Technical Architecture

---

## 1. Architecture overview

podkłajdal is a synchronous local CLI application.

```text
┌───────────────┐
│ CLI / Typer   │
└──────┬────────┘
       │
       ▼
┌──────────────────────────┐
│ Application Orchestrator │
└───┬─────────┬─────────┬──┘
    │         │         │
    ▼         ▼         ▼
YouTube    Audio     Separator
service    service   service
    │         │         │
    ▼         ▼         ▼
 yt-dlp    FFmpeg   audio-separator
    │         │         │
    └─────────┴─────────┘
              │
              ▼
         Filesystem
```

No component should require a server process.

---

## 2. Runtime baseline

MVP runtime:

- Python 3.12;
- macOS 14+;
- Apple Silicon ARM64;
- system `ffmpeg` and `ffprobe` available on PATH.

Python 3.12 is selected to stay above yt-dlp's recommended Python 3.11 baseline while avoiding unnecessary early adoption of Python 3.14, for which the separator currently has explicit version constraints.

---

## 3. Dependency roles

### Typer

Responsibilities:

- argument parsing;
- help/version output;
- exit handling;
- command contract.

### Rich

Responsibilities:

- stage display;
- spinners/progress;
- formatted errors;
- TTY-aware rendering.

Typer may supply Rich integration internally; avoid duplicating presentation abstractions unnecessarily.

### yt-dlp

Use the Python API, not shell-string construction.

Responsibilities:

- inspect YouTube metadata;
- select best available audio;
- download one video's audio;
- expose progress hooks;
- reject/translate unsupported content failures.

### FFmpeg / ffprobe

Invoked as argument arrays, never interpolated shell commands.

Responsibilities:

- probe downloaded audio;
- create canonical separation input when needed;
- encode final MP3;
- metadata tagging;
- duration validation.

### python-audio-separator

Use its Python API rather than calling its CLI as a subprocess.

Responsibilities:

- model management;
- device selection/acceleration;
- source separation;
- vocals/instrumental intermediate outputs.

---

## 4. Module boundaries

Recommended structure:

```text
src/podklajdal/
├── __init__.py
├── __main__.py
├── cli.py
├── application.py
├── config.py
├── domain/
│   ├── errors.py
│   ├── job.py
│   └── metadata.py
├── services/
│   ├── youtube.py
│   ├── audio.py
│   ├── separator.py
│   └── diagnostics.py
└── infrastructure/
    ├── filesystem.py
    ├── ffmpeg.py
    └── logging.py
```

### `cli.py`

May:

- parse flags;
- render progress/results/errors;
- translate domain errors to exit codes.

Must not:

- run yt-dlp directly;
- build FFmpeg commands;
- import PyTorch directly;
- decide output filenames.

### `application.py`

Owns the use case:

```python
process_youtube_video(request) -> JobResult
```

Responsibilities:

- stage sequencing;
- cancellation propagation;
- early conflict checks;
- cleanup decisions;
- returning final paths.

No terminal rendering in this module.

### `services/youtube.py`

Public interface conceptually:

```python
class YouTubeService:
    def inspect(url: str) -> VideoMetadata: ...
    def download_audio(metadata: VideoMetadata, destination: Path, on_progress) -> DownloadedAudio: ...
```

### `services/audio.py`

Conceptually:

```python
class AudioService:
    def prepare(source: Path, destination: Path) -> PreparedAudio: ...
    def encode_mp3(source: Path, destination: Path, metadata: TrackMetadata) -> Path: ...
    def probe(path: Path) -> AudioInfo: ...
```

### `services/separator.py`

Conceptually:

```python
class SeparationService:
    def ensure_model() -> ModelInfo: ...
    def separate(source: Path, destination_dir: Path) -> SeparatedStems: ...
```

The rest of the application must not depend on internal `audio-separator` object shapes.

---

## 5. Domain model

### `VideoMetadata`

```text
id: str
title: str
webpage_url: str
duration_seconds: int
uploader: str | None
artist: str | None
track: str | None
is_live: bool
```

### `JobRequest`

```text
url: str
output_root: Path
overwrite: bool
allow_long: bool
keep_temp: bool
```

### `JobPaths`

```text
workspace: Path
source_audio: Path
prepared_audio: Path
stems_dir: Path
final_dir: Path
vocals_final: Path
instrumental_final: Path
```

### `JobResult`

```text
metadata: VideoMetadata
vocals_path: Path
instrumental_path: Path
elapsed_seconds: float
```

---

## 6. State model

Valid job states:

```text
CREATED
  ↓
INSPECTING
  ↓
DOWNLOADING
  ↓
PREPARING
  ↓
MODEL_READY
  ↓
SEPARATING
  ↓
ENCODING
  ↓
VALIDATING
  ↓
FINALIZING
  ↓
SUCCEEDED
```

Any processing state may transition to:

```text
FAILED
CANCELLED
```

The state enum should exist even if not persisted. It simplifies logging, UX and tests.

---

## 7. Filesystem strategy

### Temp first, final last

Never write directly to the final MP3 path during encoding.

Use:

```text
<workspace>/final-vocals.mp3.part
<workspace>/final-instrumental.mp3.part
```

After both files pass validation:

1. ensure final directory exists;
2. atomically rename/move each file into its final path;
3. mark job successful;
4. clean workspace.

This avoids presenting partial output as success.

---

## 8. Concurrency

MVP processes one job per process.

No internal worker pool or queue is needed.

Multiple independent CLI processes may run concurrently. Therefore:

- each job uses a UUID workspace;
- model cache access must tolerate concurrent readers/download attempts;
- final output collision rules must still apply.

No explicit global lock should be added unless dependency behaviour proves it necessary.

---

## 9. Cancellation

Cancellation must be cooperative where possible:

- set application cancellation state;
- terminate active FFmpeg subprocess;
- let yt-dlp abort through hook/exception where practical;
- do not `kill -9` unless process refuses graceful termination;
- clean temporary files.

---

## 10. Packaging

`pyproject.toml` must expose:

```toml
[project.scripts]
podklajdal = "podklajdal.cli:main"
```

Project/package identifier must remain ASCII:

```text
podklajdal
```

Human-readable metadata may use:

```text
podkłajdal
```

---

## 11. Version pinning

Because both yt-dlp and separation dependencies change rapidly:

- pin the application's direct dependencies to tested compatible ranges;
- commit `uv.lock`;
- CI uses the lockfile;
- model filename is pinned for a given release;
- upgrades happen intentionally through dependency-update PRs with smoke/regression testing.

Do not automatically upgrade dependencies during normal app execution.
