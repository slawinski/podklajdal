# 11 — Technical References

Reference snapshot checked for this specification on **2026-09-26**.

These are implementation references, not runtime dependencies by URL.

---

## yt-dlp

- Repository: https://github.com/yt-dlp/yt-dlp
- Installation wiki: https://github.com/yt-dlp/yt-dlp/wiki/Installation
- Changelog: https://github.com/yt-dlp/yt-dlp/blob/master/Changelog.md

Relevant assumptions at spec time:

- project remains actively maintained;
- Python 3.11+ is the current recommended baseline;
- FFmpeg/ffprobe remain important dependencies for media post-processing.

---

## python-audio-separator

- Repository: https://github.com/nomadkaraoke/python-audio-separator
- README: https://github.com/nomadkaraoke/python-audio-separator/blob/main/README.md
- Model registry: https://github.com/nomadkaraoke/python-audio-separator/blob/main/audio_separator/models.json

Relevant assumptions at spec time:

- supports vocals/instrumental source separation;
- supports MDX/MDXC/RoFormer/Demucs-related model families;
- Apple Silicon can use MPS for PyTorch models and CoreML execution provider for compatible ONNX paths;
- model files can be downloaded/cached automatically;
- `model_bs_roformer_ep_317_sdr_12.9755.ckpt` is a documented high-performing/default BS-RoFormer option.

---

## Typer

- Documentation: https://typer.tiangolo.com/

Used for the public Python CLI contract.

---

## Python packaging name rules

- Name normalization specification: https://packaging.python.org/en/latest/specifications/name-normalization/

Project distribution names are constrained to ASCII letters/digits plus `.`, `_`, and `-`, which is why the package/executable identifier is `podklajdal` while the product brand remains `podkłajdal`.

---

## YouTube terms

- Terms of Service: https://www.youtube.com/static?template=terms

Delivery must not interpret technical capability as permission to download/reuse any specific content.
