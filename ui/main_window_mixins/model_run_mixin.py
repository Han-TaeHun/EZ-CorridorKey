from __future__ import annotations

import logging
import os
import shutil

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Slot

from backend import ClipState, JobType
from ui.workers.gpu_job_worker import create_job_snapshot

logger = logging.getLogger(__name__)


class ModelRunMixin:
    """Model-specific run methods (GVM, BiRefNet, VideoMaMa, MatAnyone2) for MainWindow."""

    def _confirm_partial_alpha(self) -> bool | None:
        """Check for partial alpha from a previous interrupted run.

        Returns True to continue (resume or regenerate), False if cancelled,
        or None if no partial alpha was found.
        """
        alpha_dir = os.path.join(self._current_clip.root_path, "AlphaHint")
        if not os.path.isdir(alpha_dir):
            return None
        existing = [f for f in os.listdir(alpha_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not existing:
            return None
        total = (self._current_clip.input_asset.frame_count
                 if self._current_clip.input_asset else 0)
        msg = QMessageBox(self)
        msg.setWindowTitle("일부 알파 발견")
        msg.setText(
            f"이전 실행에서 생성된 알파 프레임 {len(existing)}/{total}개를 찾았습니다."
        )
        msg.setInformativeText(
            "이어 하기는 완료된 프레임을 건너뜁니다.\n"
            "재생성은 모든 프레임을 처음부터 다시 처리합니다."
        )
        resume_btn = msg.addButton("이어 하기", QMessageBox.AcceptRole)
        regen_btn = msg.addButton("재생성", QMessageBox.DestructiveRole)
        msg.addButton(QMessageBox.Cancel)
        msg.setDefaultButton(resume_btn)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == regen_btn:
            shutil.rmtree(alpha_dir, ignore_errors=True)
            return True
        if clicked == resume_btn:
            return True
        return False  # cancelled

    def _on_run_gvm(self) -> None:
        """Run GVM alpha generation on the selected clip."""
        if self._current_clip is None or self._current_clip.state not in (ClipState.RAW, ClipState.MASKED):
            return

        if not self._warn_mps_slow("GVM Auto Alpha"):
            return

        result = self._confirm_partial_alpha()
        if result is False:
            return  # cancelled

        job = create_job_snapshot(self._current_clip, job_type=JobType.GVM_ALPHA)
        if not self._service.job_queue.submit(job):
            return

        self._current_clip.set_processing(True)
        self._start_worker_if_needed(job.id, job_label="GVM Auto")

    @Slot(str)
    def _on_run_birefnet(self, usage: str) -> None:
        """Run BiRefNet alpha generation on the selected clip."""
        if self._current_clip is None or self._current_clip.state not in (ClipState.RAW, ClipState.MASKED):
            return

        result = self._confirm_partial_alpha()
        if result is False:
            return  # cancelled

        job = create_job_snapshot(
            self._current_clip,
            job_type=JobType.BIREFNET_ALPHA,
            birefnet_usage=usage,
        )
        if not self._service.job_queue.submit(job):
            return

        self._current_clip.set_processing(True)
        self._start_worker_if_needed(job.id, job_label=f"BiRefNet ({usage})")

    @Slot()
    def _on_run_videomama(self) -> None:
        """Run VideoMaMa alpha generation on the selected clip."""
        if self._current_clip is None:
            return
        if not self._clip_has_videomama_ready_mask(self._current_clip):
            QMessageBox.information(
                self,
                "Track Mask 먼저 실행",
                "VideoMaMa를 사용하기 전에 페인트 프롬프트를 칠하고 Track Mask를 실행해 주세요.",
            )
            return

        if not self._warn_mps_slow("VideoMaMa Auto Alpha"):
            return

        job = create_job_snapshot(self._current_clip, job_type=JobType.VIDEOMAMA_ALPHA)
        if not self._service.job_queue.submit(job):
            return

        self._current_clip.set_processing(True)
        self._start_worker_if_needed(job.id, job_label="VideoMaMa")

    @Slot()
    def _on_run_matanyone2(self) -> None:
        """Run MatAnyone2 video matting alpha generation on the selected clip."""
        if self._current_clip is None:
            return
        if not self._clip_has_videomama_ready_mask(self._current_clip):
            QMessageBox.information(
                self,
                "Track Mask 먼저 실행",
                "MatAnyone2는 0번 프레임에 추적된 마스크가 필요합니다.\n\n"
                "MatAnyone2를 사용하기 전에 페인트 프롬프트를 칠하고 Track Mask를 실행해 주세요.",
            )
            return

        if not self._warn_mps_slow("MatAnyone2"):
            return

        job = create_job_snapshot(self._current_clip, job_type=JobType.MATANYONE2_ALPHA)
        if not self._service.job_queue.submit(job):
            return

        self._current_clip.set_processing(True)
        self._start_worker_if_needed(job.id, job_label="MatAnyone2")
