# 06 — Errors and Operability

---

## 1. Error design

All expected failures must map to typed application errors.

Recommended hierarchy:

```text
PodklajdalError
├── InputError
│   ├── InvalidUrlError
│   ├── UnsupportedUrlError
│   ├── PlaylistNotSupportedError
│   ├── LiveStreamNotSupportedError
│   └── DurationLimitError
├── EnvironmentError
│   ├── FFmpegMissingError
│   ├── FFprobeMissingError
│   └── OutputNotWritableError
├── DownloadError
│   ├── VideoUnavailableError
│   ├── AuthenticationRequiredError
│   └── MediaDownloadError
├── AudioProcessingError
│   ├── ProbeError
│   ├── PreparationError
│   └── EncodeError
├── SeparationError
│   ├── ModelDownloadError
│   ├── ModelLoadError
│   └── InferenceError
└── OutputConflictError
```

Do not surface raw dependency exceptions by default.

---

## 2. User-facing error template

Expected failure:

```text
Error: <plain-language explanation>
<one actionable next step when one exists>
```

Verbose mode may append:

```text
Details:
  stage: separating
  exception: ...
  workspace: ...
```

---

## 3. Retry policy

MVP does not silently retry whole jobs.

Allowed limited retries:

- yt-dlp's own safe transport retries according to its normal configuration;
- dependency-managed model download retry if provided by library.

Do not automatically restart source separation after an inference failure; it can be expensive and may fail deterministically.

---

## 4. Cleanup rules

### Success

Delete the entire job workspace.

### Expected failure before download

No workspace required, or remove empty workspace.

### Failure after download

Delete transient media unless `--keep-temp`.

### Ctrl+C

Best-effort cleanup, exit 130.

### Hard crash / power loss

On next app startup, stale job workspaces older than 24 hours may be removed.

Never automatically delete:

- model cache;
- successful final outputs;
- directories outside podkłajdal-controlled cache roots.

---

## 5. Logging

Default mode:

- human-readable stage UI;
- no persistent log file required.

Verbose mode:

- structured internal log events may be emitted to stderr;
- include timestamps and stages;
- include dependency versions at startup;
- redact URL query values if future authentication parameters are ever introduced.

MVP contains no telemetry or remote logging.

---

## 6. Dependency preflight

Before performing network/download work, validate at minimum:

- output root can be created/written;
- `ffmpeg` exists;
- `ffprobe` exists;
- core Python imports succeed.

Do not force model loading during every preflight because that adds unnecessary startup cost. `--doctor` performs deeper checks.

---

## 7. Disk-space behaviour

MVP should estimate required temporary space from source duration conservatively.

At minimum:

- check cache filesystem has a reasonable free-space floor before canonical WAV creation;
- for normal tracks, require at least 1 GB free;
- for >15 min content, warn if free space is below 2 GB;
- if FFmpeg reports ENOSPC, translate to a clear disk-space error.

No destructive auto-cleanup outside stale podkłajdal job folders.

---

## 8. Failure safety

The following must always hold:

1. Existing successful outputs are never deleted unless `--overwrite` is explicitly present.
2. A failed job never leaves `.part` files in the final output directory.
3. The application never invokes shell commands with untrusted URL/title interpolation.
4. Filename sanitization prevents `../` path traversal.
5. A malicious video title cannot make output escape the selected output root.

---

## 9. `--doctor` implementation requirements

Diagnostics must be callable without a URL.

Checks should be independent so one failed check does not prevent reporting subsequent checks.

Result categories:

- `PASS` — feature available;
- `WARN` — usable with degraded performance;
- `FAIL` — application cannot perform core job.

Examples:

```text
MPS unavailable + CPU available => WARN
FFmpeg missing => FAIL
model cache not yet populated => PASS (model will be downloaded)
output root not writable => FAIL
```
