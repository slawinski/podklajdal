# Podkłajdal

> Local CLI that turns a YouTube video into two audio files: **vocals** and **instrumental**.

**Document status:** Delivery specification v1.0  
**Date:** 2026-09-26  
**Product name:** `podkłajdal`  
**Executable / package name:** `podklajdal`

---

## 1. Purpose of this repository

This documentation is the delivery team's entry point for the first production-quality version of **podkłajdal**.

The MVP is intentionally narrow:

```text
YouTube URL
    ↓
inspect video
    ↓
download best available audio
    ↓
prepare canonical audio
    ↓
AI source separation
    ↓
┌───────────────────┬────────────────────┐
│ vocals.mp3        │ instrumental.mp3   │
└───────────────────┴────────────────────┘
```

The application is **local-first**. There is no web application, backend service, authentication, database, remote queue, or cloud storage in MVP.

---

## 2. Primary user journey

The primary invocation is deliberately one-step:

```bash
podklajdal "https://www.youtube.com/watch?v=VIDEO_ID"
```

Expected successful result:

```text
podkłajdal

✓ Video found: Artist - Song Title
✓ Audio downloaded
✓ Audio prepared
✓ Vocals separated
✓ MP3 files encoded

Done:
  ~/Music/podklajdal/artist-song-title/artist-song-title-vocals.mp3
  ~/Music/podklajdal/artist-song-title/artist-song-title-instrumental.mp3
```

The user should not need to know what `yt-dlp`, FFmpeg, PyTorch, MPS, CoreML, UVR, or BS-RoFormer are.

---

## 3. MVP definition

### In scope

- accept a single YouTube video URL;
- inspect the video before downloading;
- download the best available audio stream;
- separate audio into two stems:
  - vocals;
  - instrumental;
- encode both outputs as MP3;
- show honest, stage-based progress;
- store outputs locally;
- clean temporary files after success;
- keep downloaded AI model files cached between runs;
- provide actionable errors;
- provide a `--doctor` diagnostic mode;
- run locally on Apple Silicon macOS as the primary supported platform.

### Explicitly out of scope for MVP

- web UI or TUI;
- playlists;
- batch processing;
- Spotify/Tidal/SoundCloud input;
- YouTube authentication/cookies;
- bypassing private/DRM-protected content;
- live streams;
- four-/six-stem output;
- model selection in the normal user flow;
- accounts, history, cloud sync, telemetry;
- Windows support;
- automated publishing of separated audio.

---

## 4. Locked technical decisions

| Area                     | Decision                                                                                     |
| ------------------------ | -------------------------------------------------------------------------------------------- |
| Language                 | Python 3.12                                                                                  |
| CLI                      | Typer + Rich                                                                                 |
| Packaging / dev env      | `uv` + `pyproject.toml`                                                                      |
| YouTube ingestion        | `yt-dlp` Python API                                                                          |
| Audio processing         | system FFmpeg / ffprobe                                                                      |
| Separation engine        | `python-audio-separator` Python API                                                          |
| Default model family     | BS-RoFormer / MDXC                                                                           |
| Initial model            | `model_bs_roformer_ep_317_sdr_12.9755.ckpt` unless benchmark gate replaces it before release |
| Primary platform         | macOS 14+ on Apple Silicon (M1 or newer)                                                     |
| Acceleration             | MPS/CoreML when exposed by the separation library; CPU fallback allowed                      |
| Final format             | MP3, 320 kbps                                                                                |
| Default output root      | `~/Music/podklajdal/`                                                                        |
| Temp workspaces          | `~/.cache/podklajdal/jobs/<job-id>/`                                                         |
| Model cache              | `~/.cache/podklajdal/models/`                                                                |
| Product branding         | `podkłajdal`                                                                                 |
| Shell/package identifier | `podklajdal`                                                                                 |

The ASCII executable name is intentional. Python package/project names are ASCII-constrained and an ASCII command is more reliable across shells, scripts, CI, and package managers.

---

## 5. Documentation map

Read these documents in order when onboarding to delivery:

1. [`docs/01-product-requirements.md`](docs/01-product-requirements.md) — goals, scope, personas, success criteria.
2. [`docs/02-functional-specification.md`](docs/02-functional-specification.md) — exact functional behaviour and rules.
3. [`docs/03-cli-ux-specification.md`](docs/03-cli-ux-specification.md) — command syntax, output, progress, prompts and exit codes.
4. [`docs/04-technical-architecture.md`](docs/04-technical-architecture.md) — components, module boundaries, data flow and project structure.
5. [`docs/05-audio-pipeline.md`](docs/05-audio-pipeline.md) — detailed download, preparation, separation and encoding pipeline.
6. [`docs/06-errors-and-operability.md`](docs/06-errors-and-operability.md) — error taxonomy, diagnostics, logging, cleanup and recovery.
7. [`docs/07-testing-and-acceptance.md`](docs/07-testing-and-acceptance.md) — test strategy and Definition of Done.
8. [`docs/08-delivery-plan.md`](docs/08-delivery-plan.md) — recommended implementation slices and ticket breakdown.
9. [`docs/09-legal-and-product-constraints.md`](docs/09-legal-and-product-constraints.md) — YouTube/copyright constraints and product guardrails.
10. [`docs/10-architecture-decisions.md`](docs/10-architecture-decisions.md) — ADR-style rationale for key decisions.

---

## 6. Suggested repository structure

```text
podklajdal/
├── README.md
├── pyproject.toml
├── uv.lock
├── src/
│   └── podklajdal/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── application.py
│       ├── config.py
│       ├── domain/
│       │   ├── job.py
│       │   ├── metadata.py
│       │   └── errors.py
│       ├── services/
│       │   ├── youtube.py
│       │   ├── audio.py
│       │   ├── separator.py
│       │   └── diagnostics.py
│       └── infrastructure/
│           ├── filesystem.py
│           ├── ffmpeg.py
│           └── logging.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── docs/
```

CLI concerns must not leak into the audio pipeline. The core use case must be callable from Python without invoking the CLI.

---

## 7. Reference behaviour

### Happy path

```bash
podklajdal "https://youtu.be/abc123"
```

creates:

```text
~/Music/podklajdal/<safe-track-slug>/
├── <safe-track-slug>-vocals.mp3
└── <safe-track-slug>-instrumental.mp3
```

Temporary source audio, WAV files and intermediary stems are removed after successful completion.

### Repeat run

If both final files already exist, the application must not silently overwrite them.

Default behaviour:

```text
Outputs already exist.
Use --overwrite to replace them.
```

Exit code: `4`.

### First run

The separation model may need to be downloaded. The application must identify this as a separate stage and must not present the delay as a frozen separation process.

---

## 8. Delivery principle

The product promise is:

> Paste one YouTube URL. Receive one vocal track and one backing track.

Every implementation decision should preserve that simplicity.

Advanced capability belongs behind configuration or future commands; it should not leak into the MVP's primary invocation.
