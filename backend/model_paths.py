"""Single source of truth for model checkpoint locations."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def get_checkpoints_root() -> Path:
    """Return the root directory for all model checkpoints.

    Dev/source installs use ``<repo>/checkpoints``. Frozen builds use the
    application data directory selected by ``backend.project.get_data_dir``.
    """
    if not getattr(sys, "frozen", False):
        return _REPO_ROOT / "checkpoints"
    try:
        from backend.project import get_data_dir

        return Path(get_data_dir()) / "checkpoints"
    except ImportError:
        return _REPO_ROOT / "checkpoints"


def get_sam2_dir() -> Path:
    return get_checkpoints_root() / "sam2"


def get_birefnet_dir() -> Path:
    return get_checkpoints_root() / "birefnet"


def get_gvm_dir() -> Path:
    return get_checkpoints_root() / "gvm"


def get_videomama_dir() -> Path:
    return get_checkpoints_root() / "videomama"


def get_matanyone2_dir() -> Path:
    return get_checkpoints_root() / "matanyone2"


def get_corridorkey_dir() -> Path:
    return get_checkpoints_root() / "corridorkey"
