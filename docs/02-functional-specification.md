# 02 — Functional Specification

---

## 1. Primary command

```bash
podklajdal [OPTIONS] YOUTUBE_URL
```

The absence of subcommands is deliberate for MVP.

Auxiliary operational functionality is exposed as options (`--doctor`, `--version`) rather than making the normal user type `podklajdal separate ...`.

---

## 2. Supported URL forms

Accept single-video URLs from:

- `youtube.com/watch?...`;
- `www.youtube.com/watch?...`;
- `m.youtube.com/watch?...`;
- `music.youtube.com/watch?...`;
- `youtu.be/...`;
- `youtube.com/shorts/...` when yt-dlp can resolve it to a normal finite video.

URLs may contain additional query parameters.

### Rejected in MVP

- playlist-only URLs;
- channel URLs;
- search-result URLs;
- live streams currently in progress;
- private videos;
- content requiring cookies/authentication;
- URLs for other services;
- arbitrary local files.

If a watch URL also includes a playlist parameter, only the explicitly selected video may be processed. The application must never silently process the entire playlist.

---

## 3. URL inspection

Before downloading media, retrieve metadata through yt-dlp in metadata-only mode.

Capture at minimum:

```text
video_id
title
uploader/channel
duration
webpage_url
is_live / live_status
```

Optional where available:

```text
artist
track
album
release_year
```

Inspection must occur before creating final output files.

---

## 4. Duration handling

- `<= 15 min`: process normally.
- `> 15 min and <= 60 min`: show a warning but continue.
- `> 60 min`: reject by default to prevent accidental processing of long-form content.
- `--allow-long`: bypass the 60-minute safety limit.

Reason: separation cost scales with duration and long content can consume substantial memory, disk and time.

---

## 5. Output directory

Default root:

```text
~/Music/podklajdal/
```

Per-track directory:

```text
<safe-slug>/
```

Example:

```text
~/Music/podklajdal/david-bowie-heroes/
```

If `--output PATH` is provided, `PATH` becomes the root and the track subdirectory is still created unless `--flat-output` is introduced in a future version.

### Slug rules

- derive from `artist - title` where reliable metadata exists;
- otherwise derive from title;
- normalize Unicode for filesystem safety;
- replace path separators and control characters;
- collapse repeated whitespace/punctuation;
- trim leading/trailing dots/spaces;
- cap slug at 120 characters;
- append short video ID only if needed to resolve collision.

Output naming must not depend on shell escaping behaviour.

---

## 6. Final files

Default:

```text
<slug>-vocals.mp3
<slug>-instrumental.mp3
```

Encoding:

- codec: MP3 / libmp3lame;
- bitrate: 320 kbps;
- sample rate: 44.1 kHz unless separator output requires equivalent preserved rate;
- channels: stereo.

No additional media files remain in the final track directory after a normal successful run.

---

## 7. Overwrite behaviour

If either target output exists:

- default: abort before performing expensive separation;
- print paths that conflict;
- exit `4`.

`--overwrite`:

- permits replacement;
- existing final files are not deleted until newly encoded replacements are ready;
- use atomic move/rename into final paths where supported.

This avoids losing a good prior result if the new run fails.

---

## 8. Temporary workspace

Per job:

```text
~/.cache/podklajdal/jobs/<uuid>/
```

May contain:

```text
source.*
prepared.wav
vocals-intermediate.*
instrumental-intermediate.*
logs/debug metadata when verbose mode is enabled
```

Default cleanup:

- success: delete entire job workspace;
- expected failure: delete transient media;
- Ctrl+C: best-effort cleanup;
- internal crash: cleanup on next startup may remove stale job directories older than 24h.

`--keep-temp` is a developer/debug option and must be hidden from normal help or clearly marked advanced.

---

## 9. Model cache

Persistent cache:

```text
~/.cache/podklajdal/models/
```

Model files are **not** deleted after each run.

On first use:

1. display `Preparing separation model`;
2. download the pinned model through `python-audio-separator`;
3. keep it for future runs;
4. surface model download errors separately from audio-download errors.

---

## 10. Configuration precedence

MVP supports defaults plus CLI flags.

Optional configuration file may be introduced during implementation only if needed:

```text
~/.config/podklajdal/config.toml
```

Precedence must be:

```text
CLI flag > config file > application default
```

Environment variables are not part of the public MVP contract except those required by dependencies/debugging.

---

## 11. CLI options

Required public options:

```text
-o, --output PATH
--overwrite
--allow-long
--no-color
-v, --verbose
--doctor
--version
-h, --help
```

Advanced/developer option:

```text
--keep-temp
```

Not public in MVP:

```text
--model
--stems
--device
--bitrate
--cookies
--playlist
```

These should not be exposed until there is a demonstrated product need.

---

## 12. Metadata in MP3 outputs

Where trustworthy metadata is available, write:

- title: original track/video title;
- artist: parsed `artist` field if available; otherwise omit rather than guessing from uploader;
- comment: `Generated locally by podkłajdal from YouTube video <video_id>`.

Do not embed thumbnails in MVP.

---

## 13. Idempotency

Given the same URL, model version and application version, repeated successful runs should be operationally equivalent but are not required to be byte-identical due to dependency/model behaviour.

The application must not use existing files as proof that a prior job used the same model version.

---

## 14. Network use

Network access is permitted only for:

- YouTube/yt-dlp media and metadata retrieval;
- initial or missing separation-model download.

The application must not send source audio, stems or usage telemetry to a podkłajdal-controlled server.
