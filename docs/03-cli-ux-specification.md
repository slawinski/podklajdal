# 03 — CLI UX Specification

---

## 1. UX principles

1. **One command for the happy path.**
2. **No fake percentages.**
3. **Human-readable default output; detailed logs only with `--verbose`.**
4. **Errors explain the next action.**
5. **Implementation names stay out of the normal flow.**
6. **Successful output paths are always printed.**

---

## 2. Branding

Display name:

```text
podkłajdal
```

Executable:

```text
podklajdal
```

The Unicode name may be used in headings and terminal copy. The user must never be required to type `ł` to invoke the program.

---

## 3. Happy-path transcript

```text
$ podklajdal "https://youtu.be/abc123"

podkłajdal

✓ Inspecting URL
  Artist - Song Title · 03:42

✓ Downloading audio
  8.7 MB / 8.7 MB

✓ Preparing audio

⠹ Separating vocals and instrumental… 00:31

✓ Encoding MP3
✓ Cleaning temporary files

Done
  Vocals:       ~/Music/podklajdal/artist-song-title/artist-song-title-vocals.mp3
  Instrumental: ~/Music/podklajdal/artist-song-title/artist-song-title-instrumental.mp3
```

If exact byte progress is unavailable, the download stage may use an indeterminate indicator rather than inventing values.

---

## 4. First-run model transcript

```text
✓ Downloading audio
✓ Preparing audio

⠹ Preparing separation model…
  First run only. The model will be cached locally.

⠹ Separating vocals and instrumental… 00:00
```

Do not describe model download as an application update.

---

## 5. Long-track warning

For 15–60 min:

```text
! This video is 27:14. Long tracks use more memory and take longer to separate.
  Continuing…
```

For >60 min:

```text
Error: video duration is 01:43:08.
Tracks longer than 60 minutes are blocked by default.
Re-run with --allow-long if this is intentional.
```

Exit code: `2`.

---

## 6. Existing files

```text
Error: output files already exist:
  ...-vocals.mp3
  ...-instrumental.mp3

Use --overwrite to replace them.
```

Exit code: `4`.

No interactive confirmation prompt is required. This keeps the command deterministic and scriptable.

---

## 7. Invalid URL

```text
Error: expected a single YouTube video URL.
Received: https://example.com/song
```

Exit code: `2`.

---

## 8. Unsupported/private content

Example:

```text
Error: this video cannot be downloaded without authentication.
podkłajdal MVP supports public videos that do not require cookies or login.
```

Do not suggest DRM circumvention.

---

## 9. Missing FFmpeg

```text
Error: FFmpeg is required but was not found in PATH.

macOS with Homebrew:
  brew install ffmpeg

Then run:
  podklajdal --doctor
```

Exit code: `3`.

---

## 10. Diagnostic mode

```bash
podklajdal --doctor
```

Reference output:

```text
podkłajdal doctor

Application
  version       0.1.0
  Python        3.12.7

System
  macOS         15.x
  architecture  arm64

Dependencies
  ffmpeg        ✓ 8.x
  ffprobe       ✓ 8.x
  yt-dlp        ✓ installed
  separator     ✓ installed

Acceleration
  PyTorch MPS   ✓ available
  CoreML EP     ✓ available
  selected      MPS/CoreML

Storage
  model cache   ✓ ~/.cache/podklajdal/models
  output root   ✓ ~/Music/podklajdal

Result: ready
```

When degraded but usable:

```text
Result: ready with CPU fallback
```

When blocked:

```text
Result: not ready
```

`--doctor` exits `0` if usable, `3` if a required local dependency is missing/broken.

---

## 11. Verbose mode

```bash
podklajdal URL --verbose
```

Adds:

- dependency versions;
- detected source format;
- temp workspace path;
- selected model filename;
- detected accelerator;
- FFmpeg command summaries;
- exception chain on failure.

Verbose logs must not print secrets/cookies. Cookies are not supported in MVP.

---

## 12. Colour and non-interactive terminals

- colour enabled when stdout is a compatible TTY;
- `NO_COLOR` convention should be respected if easy to support;
- `--no-color` always disables colour;
- CI/piped output must remain understandable without spinners/ANSI control sequences.

---

## 13. Ctrl+C behaviour

First interrupt:

```text
Cancelled. Cleaning temporary files…
```

Then:

- stop ongoing subprocesses where possible;
- remove incomplete output temp files;
- preserve existing valid output files;
- best-effort cleanup job workspace;
- exit `130`.

---

## 14. Exit-code contract

| Code | Meaning |
|---:|---|
| 0 | success |
| 1 | unexpected internal error |
| 2 | invalid input / unsupported content / policy guardrail |
| 3 | local environment/dependency not ready |
| 4 | output conflict |
| 5 | remote/download failure |
| 6 | audio preparation/encoding failure |
| 7 | separation/model failure |
| 130 | interrupted by user |

Exit codes are part of the public CLI contract and must be tested.
