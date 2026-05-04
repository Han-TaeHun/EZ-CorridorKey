"""이미지 시퀀스를 export 대상 디렉터리로 복사하는 유틸리티."""
from __future__ import annotations

import shutil
from pathlib import Path
from threading import Event
from typing import Callable

_IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff", ".bmp", ".dpx"})


def export_sequence(
    src_dir: str,
    out_dir: str,
    on_progress: Callable[[int, int], None] | None = None,
    cancel_event: Event | None = None,
) -> None:
    """src_dir의 이미지 시퀀스를 out_dir로 복사한다."""
    src = Path(src_dir)
    dst = Path(out_dir)
    dst.mkdir(parents=True, exist_ok=True)

    files = sorted(
        f for f in src.iterdir()
        if f.is_file() and f.suffix.lower() in _IMAGE_EXTS
    )
    total = len(files)
    for i, file_path in enumerate(files):
        if cancel_event and cancel_event.is_set():
            return
        shutil.copy2(file_path, dst / file_path.name)
        if on_progress:
            on_progress(i + 1, total)
