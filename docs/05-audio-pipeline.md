# 05 — Audio Pipeline

---

## 1. Pipeline objective

Produce two useful 320 kbps MP3 files from the best audio available for one YouTube video while avoiding unnecessary lossy transcoding before AI separation.

```text
YouTube
  ↓
best audio stream
  ↓
canonical PCM working audio
  ↓
BS-RoFormer separation
  ↓
vocals + instrumental intermediates
  ↓
MP3 320k
```

Critical rule:

> Do not convert the YouTube source to MP3 before source separation.

Lossy MP3 encoding before ML inference can introduce artifacts and cannot improve source quality.

---

## 2. Stage A — Inspect

Use yt-dlp metadata extraction without downloading media.

Validate:

- host is supported;
- one video is selected;
- video is not a currently running live stream;
- duration policy passes;
- video is available without unsupported authentication.

Resolve final output paths before downloading, so existing-file conflicts fail early.

---

## 3. Stage B — Download best available audio

Selection objective:

- audio-only format when available;
- otherwise best available format containing audio;
- do not request a specific lossy codec unless necessary;
- retain original container/codec in the job workspace.

Examples may include Opus/WebM or AAC/M4A.

Do not request video bytes when an audio-only stream exists.

The downloader returns the actual downloaded path; callers must not infer file extension.

---

## 4. Stage C — Probe

Use ffprobe to validate source audio before separation.

Require:

- at least one audio stream;
- finite positive duration;
- decodable audio;
- sane duration compared with metadata.

If yt-dlp duration and ffprobe duration differ substantially (>5 seconds for normal music videos), log a warning in verbose mode but prefer probed media duration for technical validation.

---

## 5. Stage D — Prepare canonical working audio

Create:

```text
prepared.wav
```

Recommended working format:

- WAV;
- PCM signed 16-bit little-endian;
- 44.1 kHz;
- stereo.

Reference transformation intent:

```text
ffmpeg -i SOURCE -vn -ac 2 -ar 44100 -c:a pcm_s16le prepared.wav
```

Implementation must invoke FFmpeg without a shell.

No loudness normalization is applied by podkłajdal before separation in MVP.

Reason:

- preserve source dynamics;
- avoid making a product-level mastering decision;
- rely on separator's expected input handling.

---

## 6. Stage E — Ensure model

Initial pinned model:

```text
model_bs_roformer_ep_317_sdr_12.9755.ckpt
```

Model family:

```text
MDXC / BS-RoFormer
```

The selected library currently presents this model as its default/top vocal-separation option.

Before v1.0 release, execute the benchmark gate described in the testing spec. The exact model may be replaced if a clearly better model produces materially better backing-track quality on the project's rights-cleared benchmark set without unacceptable runtime/memory regression.

If the exact model changes, update:

- this document;
- ADR;
- lock/release notes;
- regression baselines.

---

## 7. Stage F — Separation

Input:

```text
prepared.wav
```

Output requirement:

```text
vocals intermediate
instrumental intermediate
```

Use `python-audio-separator` through its Python API.

Device selection is delegated to the library's supported acceleration path. On supported Apple Silicon, prefer MPS/CoreML when available, with CPU fallback permitted.

The core application must treat the separator as an adapter; model-specific configuration must remain isolated inside `SeparationService`.

---

## 8. Stage G — Stem validation

Before MP3 encoding, validate both stems:

- files exist;
- file size > 0;
- decodable;
- duration difference from prepared input <= 1.0 second unless a documented dependency limitation requires a slightly larger tolerance;
- both have audio streams.

Do not attempt to judge artistic quality automatically in the runtime application.

---

## 9. Stage H — Final encode

Encode each stem separately to:

```text
MP3, libmp3lame, 320 kbps, stereo
```

Use temporary output names inside workspace first.

Tag metadata where available.

No normalization, limiter or EQ is applied in MVP.

---

## 10. Stage I — Final validation

For both final MP3 files:

- ffprobe succeeds;
- codec is MP3;
- duration is within tolerance;
- file is non-zero;
- no `.part` file remains in final directory.

Only after **both** outputs validate may the job transition to `SUCCEEDED`.

---

## 11. Stage J — Finalize and clean

1. Move validated files into final directory.
2. Print final paths.
3. Remove job workspace unless `--keep-temp` is set.

If moving the second final file fails after the first was moved, rollback the first newly created file when safe to do so. Never delete an older pre-existing file in rollback logic.

---

## 12. Quality caveats

Source separation can leave:

- vocal reverb in instrumental;
- backing vocals mixed into either side;
- transient artifacts;
- phasey cymbals/high frequencies;
- leaked instruments in vocals;
- leaked vocals in dense mixes.

These are expected model limitations, not necessarily application defects.

Application defects include:

- truncated tracks;
- wrong speed/pitch;
- silent output caused by orchestration;
- channel loss;
- corrupted encoding;
- swapped vocal/instrumental file labels.
