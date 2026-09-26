from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from podklajdal.domain.errors import FFmpegMissingError, FFprobeMissingError


def executable_path(name: str) -> str | None:
    return shutil.which(name)


def require_ffmpeg() -> str:
    path = executable_path("ffmpeg")
    if not path:
        raise FFmpegMissingError(
            "FFmpeg is required but was not found in PATH.",
            "macOS with Homebrew: brew install ffmpeg\nThen run: podklajdal --doctor",
        )
    return path


def require_ffprobe() -> str:
    path = executable_path("ffprobe")
    if not path:
        raise FFprobeMissingError(
            "ffprobe is required but was not found in PATH.",
            "Install FFmpeg, then run: podklajdal --doctor",
        )
    return path


def run_process(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    completed = subprocess.CompletedProcess(
        args=list(args),
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
    )
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            list(args),
            output=stdout,
            stderr=stderr,
        )
    return completed


def probe_json(path: Path) -> dict:
    ffprobe = require_ffprobe()
    completed = run_process(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(completed.stdout)


def version_line(name: str) -> str | None:
    path = executable_path(name)
    if not path:
        return None
    completed = run_process([path, "-version"], check=False)
    first = completed.stdout.splitlines()[:1]
    return first[0] if first else "installed"
