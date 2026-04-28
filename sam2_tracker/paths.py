"""SAM2 checkpoint cache location — single source of truth."""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent


def get_sam2_cache_dir() -> Path:
    """Return the local cache directory for SAM2 checkpoints.

    Dev/source installs: <project_root>/sam2_tracker/checkpoints/
    Frozen builds: <user_data_dir>/sam2_tracker/checkpoints/
    """
    if not getattr(sys, "frozen", False):
        return _PACKAGE_ROOT / "checkpoints"
    try:
        from backend.project import get_data_dir

        return Path(get_data_dir()) / "sam2_tracker" / "checkpoints"
    except ImportError:
        return _PACKAGE_ROOT / "checkpoints"
