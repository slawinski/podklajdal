# 07 — Testing and Acceptance

---

## 1. Testing pyramid

```text
          manual audio quality
        /                     \
      integration / smoke tests
    /                           \
             unit tests
```

CI must not depend on YouTube availability for the majority of test coverage.

---

## 2. Unit tests

Required coverage areas:

### URL validation

- supported YouTube watch URL;
- youtu.be URL;
- YouTube Shorts URL;
- malformed URL;
- non-YouTube URL;
- playlist-only URL;
- watch URL containing playlist query parameter.

### Duration policy

- 14:59 normal;
- 15:01 warning state;
- 59:59 allowed;
- 60:01 rejected without `--allow-long`;
- 60:01 accepted with `--allow-long`.

### Filenames

- slash/backslash removal;
- Unicode title;
- emoji;
- leading/trailing dots;
- extremely long title;
- collision handling;
- malicious `../../` style title.

### Output conflicts

- no existing files;
- vocals exists;
- instrumental exists;
- both exist;
- `--overwrite` behaviour.

### State transitions

- happy path;
- failure at every stage;
- cancellation at every long-running stage.

### Error-to-exit-code mapping

Every public exit code must have explicit tests.

---

## 3. Integration tests — no external network

Use small local audio fixtures.

Required:

1. FFmpeg prepare stage creates expected WAV.
2. ffprobe wrapper parses expected metadata.
3. MP3 encode produces playable 320 kbps output.
4. output tagging works.
5. atomic finalization works.
6. separation adapter can be mocked behind its interface.
7. yt-dlp adapter can be exercised against stored metadata fixtures.
8. Ctrl+C/subprocess termination logic does not leave final partial files.

---

## 4. Separator integration test

CI profile permitting model download/cache may run one short real separation fixture.

This test should be tagged separately, e.g.:

```text
integration_model
```

Normal fast CI may skip it.

A scheduled/release pipeline should execute it.

---

## 5. Network smoke test

A non-blocking or release-only test may use a known rights-cleared/public YouTube test asset.

Verify:

- inspect succeeds;
- one audio file downloads;
- end-to-end job completes;
- output duration is sane.

Do not use random commercial videos as automated CI fixtures.

---

## 6. Audio quality benchmark gate

Before selecting the final v1.0 model, create a rights-cleared benchmark set representing at least:

1. sparse acoustic vocal;
2. dense rock/metal mix;
3. electronic/pop production;
4. track with backing vocals/reverb;
5. low-quality/compressed source.

Compare at minimum:

- current pinned BS-RoFormer baseline;
- one current alternative top vocal/instrumental model supported by `python-audio-separator`.

Score manually on a 1–5 engineering rubric for:

- lead-vocal leakage in instrumental;
- instrumental loss/damage;
- vocal clarity;
- high-frequency/transient artifacts;
- overall usefulness as a backing track.

Also record:

- runtime;
- peak memory if practical;
- model size;
- acceleration path.

### Model selection rule

Do not replace the baseline for a tiny subjective improvement if runtime or reliability regresses materially.

The decision must be recorded in the architecture-decision document.

---

## 7. End-to-end acceptance scenarios

### AC-E2E-01 — Fresh happy path

Given:

- supported Mac;
- FFmpeg installed;
- model not cached;
- public YouTube video;

When:

```bash
podklajdal URL
```

Then:

- model is cached;
- job completes;
- two final MP3s exist;
- temp media is gone;
- exit code is 0.

### AC-E2E-02 — Warm happy path

Given model is already cached, second track does not re-download model.

### AC-E2E-03 — Output conflict

Existing output causes early exit 4 without running separation.

### AC-E2E-04 — Missing FFmpeg

Preflight fails with actionable error and exit 3.

### AC-E2E-05 — Bad URL

Fails before network-heavy processing with exit 2.

### AC-E2E-06 — Ctrl+C

Interrupt during separation exits 130 and leaves no new final MP3.

### AC-E2E-07 — Separation failure

Mock/induce separator error; existing prior files remain untouched and exit is 7.

---

## 8. Definition of Done for MVP

MVP is done only when:

- [ ] all locked requirements are implemented;
- [ ] automated unit/integration tests pass;
- [ ] release-only end-to-end smoke passes;
- [ ] audio quality benchmark is reviewed;
- [ ] exact separation model is pinned;
- [ ] installation instructions work on a clean supported Mac;
- [ ] `podklajdal --doctor` is operational;
- [ ] Ctrl+C behaviour is tested;
- [ ] output conflict/overwrite safety is tested;
- [ ] README matches actual command behaviour;
- [ ] dependency licenses are reviewed for distribution method;
- [ ] no secrets/telemetry/cloud upload are present.
