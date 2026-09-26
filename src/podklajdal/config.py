from dataclasses import dataclass
from pathlib import Path

from podklajdal import __version__

PRODUCT_NAME = "podkłajdal"
EXECUTABLE_NAME = "podklajdal"
VERSION = __version__
DEFAULT_MODEL = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
DEFAULT_OUTPUT_ROOT = Path.home() / "Music" / "podklajdal"
CACHE_ROOT = Path.home() / ".cache" / "podklajdal"
JOBS_ROOT = CACHE_ROOT / "jobs"
MODEL_CACHE = CACHE_ROOT / "models"
MAX_NORMAL_DURATION_SECONDS = 15 * 60
MAX_DEFAULT_DURATION_SECONDS = 60 * 60
MIN_FREE_BYTES_NORMAL = 1 * 1024**3
MIN_FREE_BYTES_LONG = 2 * 1024**3
STALE_JOB_AGE_SECONDS = 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class Settings:
    output_root: Path = DEFAULT_OUTPUT_ROOT
    jobs_root: Path = JOBS_ROOT
    model_cache: Path = MODEL_CACHE
    model_filename: str = DEFAULT_MODEL
