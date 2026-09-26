# 01 — Product Requirements

**Product:** podkłajdal  
**Version:** MVP / v1.0  
**Status:** Delivery specification

---

## 1. Product statement

**podkłajdal** is a local command-line application that converts a single public YouTube video into two locally stored audio tracks:

1. isolated vocals;
2. instrumental / backing track.

The product removes the need to manually chain a YouTube-to-audio tool with a separate vocal-removal service.

---

## 2. User problem

Today the user must perform several independent operations:

1. copy a YouTube URL;
2. use a downloader/converter;
3. find the downloaded audio file;
4. upload it to a source-separation service;
5. wait for processing;
6. download vocals;
7. download instrumental;
8. clean up temporary files.

The MVP collapses these steps into one command.

---

## 3. Target user

Primary user:

- comfortable with a terminal;
- wants a backing track and/or isolated vocals from a YouTube-hosted song;
- prefers a local workflow;
- does not want to understand audio/ML implementation details.

The MVP is not targeted at non-technical users who require a graphical installer or GUI.

---

## 4. Jobs to be done

### JTBD-01 — Create a backing track

> When I find a song on YouTube, I want to create a local instrumental version with one command, so that I can sing/play over it.

### JTBD-02 — Extract vocals

> When I find a song on YouTube, I want the isolated vocal stem as a separate file, so that I can rehearse or inspect the vocal line.

### JTBD-03 — Avoid manual tool chaining

> I want the application to manage downloading, conversion, separation and cleanup so that I do not have to move files between tools.

---

## 5. Product goals

### G-01 — One-command workflow

A normal successful run requires only:

```bash
podklajdal <youtube-url>
```

### G-02 — Useful output by default

The default output must be immediately playable by mainstream audio players: MP3 at 320 kbps.

### G-03 — Local-first

All user audio processing occurs on the user's machine.

### G-04 — High-quality separation

Use a modern pretrained vocal/instrumental model rather than traditional phase cancellation or EQ-based karaoke processing.

### G-05 — Understandable failure

When the application cannot complete a job, the user must receive a specific explanation and a corrective action where one exists.

---

## 6. Non-goals

MVP does not attempt to:

- guarantee studio-master isolation;
- remove every backing vocal or reverb artifact;
- recover information absent from the compressed source;
- provide professional mastering;
- preserve or recreate multitrack project files;
- become a general YouTube downloader;
- provide a hosted conversion service.

---

## 7. Core user stories

### US-01 — Process a YouTube video

**As a user**, I want to pass a YouTube URL so that the application downloads and processes the corresponding audio.

Acceptance:

- public, non-live single-video URLs are accepted;
- metadata is inspected before large processing starts;
- playlists are rejected in MVP;
- malformed/non-YouTube URLs are rejected before download.

### US-02 — Receive two tracks

**As a user**, I want vocals and instrumental as separate MP3 files.

Acceptance:

- exactly two final files are produced by default;
- both are non-empty and playable;
- durations approximately match the source audio;
- filenames clearly distinguish `vocals` and `instrumental`.

### US-03 — See progress

**As a user**, I want to know what the application is doing.

Acceptance:

- each major stage is visible;
- deterministic percentages are shown only when known;
- separation may use a spinner/elapsed time instead of fabricated percentage;
- first-time model download is called out explicitly.

### US-04 — Choose output location

**As a user**, I want to override the default output location.

Acceptance:

```bash
podklajdal URL --output ~/Desktop/karaoke
```

writes final files under the provided directory.

### US-05 — Diagnose my environment

**As a user**, I want a diagnostic command so that setup problems can be distinguished from content-specific failures.

Acceptance:

```bash
podklajdal --doctor
```

reports:

- application version;
- Python version;
- OS and architecture;
- FFmpeg/ffprobe availability and versions;
- separator importability;
- available acceleration (MPS/CoreML/CPU as detectable);
- model cache path and writability;
- output-root writability.

---

## 8. Success criteria

MVP is ready when all of the following are true:

1. A clean supported Mac can install and run the application using documented steps.
2. A public single YouTube music video can be converted without manual file handling.
3. A successful job leaves exactly two intended final audio files in its output folder.
4. Temporary media is cleaned up after success.
5. A failed job does not leave a final file that appears successful but is partial/corrupt.
6. `--doctor` identifies missing FFmpeg before a conversion is attempted.
7. Ctrl+C terminates safely and cleans transient files.
8. Automated tests cover the orchestration and failure states without requiring YouTube network access on every CI run.

---

## 9. Quality expectations

Separation quality depends on source material and is probabilistic.

The product must not promise "perfect" or "lossless" stem extraction.

For the release benchmark set, expected behaviour is:

- lead vocal is substantially attenuated in instrumental output;
- instrumental accompaniment remains recognisable and useful;
- vocal output contains the dominant lead vocal;
- no catastrophic clipping, truncation, time shift or speed change is introduced;
- no output is silent unless the source genuinely contains no corresponding content.

A manually reviewed, rights-cleared benchmark set must be retained for release regression testing.

---

## 10. Future product directions — not MVP commitments

Potential follow-ups:

- batch mode;
- playlist mode;
- drag/drop or local-file input;
- TUI;
- WAV/FLAC output;
- multi-stem extraction;
- source/model presets;
- audio preview;
- automatic update checks;
- Homebrew distribution;
- Linux support;
- native packaged macOS binary.
