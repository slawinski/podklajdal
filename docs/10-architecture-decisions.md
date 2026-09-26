# 10 — Architecture Decisions

This file is the MVP ADR register.

---

## ADR-001 — Local CLI instead of web application

**Status:** Accepted  
**Decision:** Build a local synchronous CLI.

### Rationale

The actual product flow requires local media processing and does not need accounts, remote queues, storage, or a browser UI. Local execution dramatically reduces infrastructure scope and keeps audio private.

### Consequences

- user must have a compatible local environment;
- initial packaging is less consumer-friendly;
- no backend scaling cost;
- processing performance depends on user's hardware.

---

## ADR-002 — Python 3.12

**Status:** Accepted  
**Decision:** Use Python 3.12 as the MVP runtime.

### Rationale

The core ecosystem is Python-native: yt-dlp, PyTorch and python-audio-separator. Python 3.12 is a conservative supported midpoint: modern, above yt-dlp's recommended 3.11 baseline, and within current separator compatibility.

---

## ADR-003 — Brand name vs executable name

**Status:** Accepted  
**Decision:** Display `podkłajdal`; install `podklajdal`.

### Rationale

Python distribution names are restricted to ASCII-compatible naming and ASCII shell commands are more portable/reliable.

### Consequence

Documentation must consistently distinguish product branding from the command users type.

---

## ADR-004 — yt-dlp Python API

**Status:** Accepted  
**Decision:** Integrate yt-dlp as a Python dependency rather than shelling out to a `yt-dlp` executable.

### Rationale

- structured metadata;
- progress hooks;
- typed wrapper around dependency errors;
- no shell quoting problems;
- easier testing/mocking.

---

## ADR-005 — FFmpeg remains an external executable

**Status:** Accepted  
**Decision:** Use system FFmpeg/ffprobe through safe subprocess argument arrays.

### Rationale

FFmpeg is the appropriate mature media transcoding/probing tool. Reimplementing codecs in Python is unnecessary.

### Consequence

`ffmpeg` becomes a required local prerequisite and `--doctor` must verify it.

---

## ADR-006 — No MP3 before separation

**Status:** Accepted  
**Decision:** Preserve the downloaded source format until conversion to canonical PCM WAV for separation. Encode MP3 only after separation.

### Rationale

Avoid an additional lossy encode before ML inference.

---

## ADR-007 — python-audio-separator abstraction

**Status:** Accepted  
**Decision:** Use `python-audio-separator` behind an application-owned `SeparationService`.

### Rationale

The library exposes multiple modern UVR-related architectures/models and handles model/device concerns, including Apple Silicon acceleration.

### Consequence

No other application module may directly depend on its model-specific API.

---

## ADR-008 — Initial BS-RoFormer baseline

**Status:** Accepted with release benchmark gate  
**Decision:** Start with `model_bs_roformer_ep_317_sdr_12.9755.ckpt`.

### Rationale

It is a current high-performing vocals/instrumental model exposed prominently by the separator library and is appropriate for the two-stem use case.

### Review trigger

Before v1.0, compare against at least one current alternative on the rights-cleared benchmark set.

---

## ADR-009 — Apple Silicon/macOS-first MVP

**Status:** Accepted  
**Decision:** Officially support macOS 14+ on Apple Silicon first.

### Rationale

This matches the initial user's local environment and the current separator library documents MPS/CoreML acceleration for M1+ Macs.

### Consequence

Linux portability should be preserved architecturally, but is not a release blocker for MVP.

---

## ADR-010 — MP3 320 kbps final output

**Status:** Accepted  
**Decision:** Both final outputs are MP3 at 320 kbps.

### Rationale

The use case prioritizes convenient rehearsal/playback files. Source material is usually already lossy; FLAC would increase size without restoring lost source information.

### Future

Offer WAV/FLAC only when there is user demand for downstream editing workflows.

---

## ADR-011 — No automatic telemetry

**Status:** Accepted  
**Decision:** Do not send usage, URL, audio or diagnostic telemetry to a podkłajdal service.

### Rationale

Local utility does not require it and source URLs/media may be sensitive.

---

## ADR-012 — No interactive overwrite prompt

**Status:** Accepted  
**Decision:** Existing output is an error unless `--overwrite` is explicitly supplied.

### Rationale

Keeps the CLI deterministic and script-friendly while protecting user files.
