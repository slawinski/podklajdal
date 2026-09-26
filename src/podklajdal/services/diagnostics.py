from __future__ import annotations

import importlib.util
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

from podklajdal.config import VERSION
from podklajdal.infrastructure.ffmpeg import version_line


@dataclass(frozen=True, slots=True)
class DiagnosticItem:
    name: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    items: tuple[DiagnosticItem, ...]
    ready: bool
    cpu_fallback: bool


def _directory_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return os.access(path, os.W_OK)
    except OSError:
        return False


class DiagnosticsService:
    def run(self, model_cache: Path, output_root: Path) -> DiagnosticReport:
        items: list[DiagnosticItem] = [
            DiagnosticItem("version", "PASS", VERSION),
            DiagnosticItem("Python", "PASS", platform.python_version()),
            DiagnosticItem("OS", "PASS", f"{platform.system()} {platform.release()}"),
            DiagnosticItem("architecture", "PASS", platform.machine()),
        ]
        ready = True

        for executable in ("ffmpeg", "ffprobe"):
            version = version_line(executable)
            if version:
                items.append(DiagnosticItem(executable, "PASS", version))
            else:
                items.append(DiagnosticItem(executable, "FAIL", "not found in PATH"))
                ready = False

        for module, label in (("yt_dlp", "yt-dlp"), ("audio_separator", "separator")):
            present = importlib.util.find_spec(module) is not None
            items.append(
                DiagnosticItem(
                    label,
                    "PASS" if present else "FAIL",
                    "installed" if present else "missing",
                )
            )
            ready = ready and present

        mps_available = False
        try:
            import torch

            mps_available = bool(torch.backends.mps.is_available())
        except Exception:
            pass
        items.append(
            DiagnosticItem(
                "PyTorch MPS",
                "PASS" if mps_available else "WARN",
                "available" if mps_available else "unavailable",
            )
        )

        coreml_available = False
        try:
            import onnxruntime as ort

            coreml_available = "CoreMLExecutionProvider" in ort.get_available_providers()
        except Exception:
            pass
        items.append(
            DiagnosticItem(
                "CoreML EP",
                "PASS" if coreml_available else "WARN",
                "available" if coreml_available else "unavailable",
            )
        )
        if mps_available and coreml_available:
            selected = "MPS/CoreML"
        elif mps_available:
            selected = "MPS"
        elif coreml_available:
            selected = "CoreML"
        else:
            selected = "CPU fallback"
        items.append(DiagnosticItem("selected", "PASS" if ready else "WARN", selected))

        for path, label in ((model_cache, "model cache"), (output_root, "output root")):
            writable = _directory_writable(path)
            items.append(
                DiagnosticItem(
                    label, "PASS" if writable else "FAIL", str(path.expanduser())
                )
            )
            ready = ready and writable

        return DiagnosticReport(
            items=tuple(items),
            ready=ready,
            cpu_fallback=ready and not (mps_available or coreml_available),
        )
