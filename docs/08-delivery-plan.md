# 08 — Delivery Plan

This plan is ordered to maximize early validation of the highest-risk technical assumptions.

---

## Slice 0 — Technical spike

### POD-001 — Bootstrap project

Deliver:

- Python 3.12 project;
- `uv` configuration;
- `src/` layout;
- Typer entry point;
- Ruff/formatting/testing baseline;
- CI running unit tests.

Acceptance:

```bash
podklajdal --version
podklajdal --help
```

work from the development environment.

### POD-002 — Environment diagnostics

Implement `--doctor` skeleton and detection for:

- FFmpeg;
- ffprobe;
- Python/platform;
- separator import;
- MPS/CoreML visibility where practical.

Purpose: validate target Mac setup before building orchestration.

### POD-003 — Separation spike on local audio

Given a local WAV fixture:

- load pinned model;
- run separation;
- produce vocals + instrumental;
- verify Apple Silicon acceleration/fallback;
- record representative runtime.

This is the first go/no-go technical checkpoint.

---

## Slice 1 — End-to-end happy path

### POD-004 — YouTube metadata inspection

Implement:

- URL validation;
- yt-dlp metadata-only inspection;
- single-video enforcement;
- live/duration rules.

### POD-005 — YouTube audio download

Implement:

- best-audio selection;
- progress hook adapter;
- workspace destination;
- typed download errors.

### POD-006 — Audio preparation

Implement:

- ffprobe wrapper;
- canonical WAV generation;
- media validation.

### POD-007 — Separation adapter

Implement production `SeparationService` using `python-audio-separator` Python API and pinned model/cache path.

### POD-008 — Final MP3 encoder

Implement:

- 320 kbps encode;
- tags;
- output validation;
- atomic finalization.

### POD-009 — Orchestrator

Implement complete use case:

```text
inspect -> preflight -> paths -> download -> prepare -> separate -> encode -> validate -> finalize -> cleanup
```

At the end of Slice 1:

```bash
podklajdal URL
```

must work end-to-end, even if terminal UX is still basic.

---

## Slice 2 — Product-quality CLI

### POD-010 — Stage UI

Implement Rich rendering for:

- inspection;
- download;
- model preparation;
- separation;
- encoding;
- cleanup;
- final result.

Do not show invented percentages.

### POD-011 — Output path and sanitization

Implement:

- default output root;
- `--output`;
- safe slugs;
- collision handling;
- final filenames.

### POD-012 — Overwrite safety

Implement:

- early conflict detection;
- `--overwrite`;
- temp-final files;
- rollback rules.

### POD-013 — Cancellation and cleanup

Implement:

- Ctrl+C;
- subprocess termination;
- stale cache job cleanup;
- exit 130.

### POD-014 — Error presentation and exit codes

Implement full typed error mapping from spec.

---

## Slice 3 — Hardening and release

### POD-015 — Test suite completion

Implement required unit/integration scenarios.

### POD-016 — Quality/model benchmark

Run benchmark gate and record selected model.

Update documentation if default changes.

### POD-017 — Clean-machine installation test

Validate installation on a clean supported Apple Silicon Mac.

Document:

- Python/uv installation prerequisite;
- FFmpeg installation;
- podkłajdal installation;
- `--doctor`;
- first conversion.

### POD-018 — Release packaging

MVP acceptable distribution:

```text
uv tool install ...
```

or equivalent package install from repository/release.

Homebrew formula/native binary is future work unless trivial after core delivery.

### POD-019 — Release checklist

Verify:

- versioning;
- dependency lock;
- licenses;
- README;
- changelog;
- smoke test;
- model pin;
- no debug fixtures shipped accidentally.

---

## Dependency graph

```text
POD-001
  ├── POD-002
  └── POD-003

POD-004 ─┐
POD-005 ─┤
POD-006 ─┤
POD-007 ─┼── POD-009
POD-008 ─┘

POD-009
  ├── POD-010
  ├── POD-011 ── POD-012
  ├── POD-013
  └── POD-014

POD-010..014
  └── POD-015
       ├── POD-016
       ├── POD-017
       └── POD-018
            └── POD-019
```

---

## Delivery priorities

### P0 — mandatory for MVP

POD-001 through POD-019 except optional packaging enhancements.

### P1 — immediately after MVP

- local-file input;
- FLAC/WAV output;
- batch URLs;
- configurable default output directory;
- model/cache management command.

### P2 — later

- TUI;
- playlists;
- multi-stem;
- Linux;
- Homebrew/native bundle;
- additional source adapters.

---

## Team handoff notes

Delivery should treat `README.md` and documents 01–10 as the source of truth.

When implementation needs to diverge:

1. create/update an ADR in `10-architecture-decisions.md`;
2. update affected functional/technical spec;
3. then merge code.

Do not allow implementation to silently become the only specification.
