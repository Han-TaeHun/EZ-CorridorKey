"""Single source of truth for model checkpoint locations."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def get_checkpoints_root() -> Path:
    """Return the root directory for all model checkpoints.

    ``backend.project.get_data_dir()``를 단일 진입점으로 사용.
    backend 패키지 전체 임포트가 불가능한 경우(setup_models.py 등 경량 컨텍스트)에는
    이 파일 위치 기준 repo root로 폴백 — dev 모드에서 결과값이 동일하다.
    """
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


def get_resnet18_dir() -> Path:
    return get_checkpoints_root() / "resnet18"


def get_resnet50_dir() -> Path:
    return get_checkpoints_root() / "resnet50"


def get_corridorkey_dir() -> Path:
    return get_checkpoints_root() / "corridorkey"
