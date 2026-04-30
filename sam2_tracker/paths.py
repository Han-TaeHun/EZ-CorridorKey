"""SAM2 checkpoint cache location."""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent


def get_sam2_cache_dir() -> Path:
    """Return the local cache directory for SAM2 checkpoints.

    Dev/source installs: <project_root>/checkpoints/sam2/
    Frozen builds: <user_data_dir>/checkpoints/sam2/
    """
    try:
        from backend import model_paths

        return model_paths.get_sam2_dir()
    except ImportError:
        if getattr(sys, "frozen", False):
            try:
                from backend.project import get_data_dir

                return Path(get_data_dir()) / "sam2_tracker" / "checkpoints"
            except ImportError:
                pass
        return _PACKAGE_ROOT / "checkpoints"
