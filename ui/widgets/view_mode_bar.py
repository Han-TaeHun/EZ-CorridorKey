"""View mode toggle bar — switches between Input/Alpha/FG/Matte/Comp/Processed.

Uses QButtonGroup with exclusive selection. Active button highlighted
with brand yellow. Buttons are enabled/disabled based on which output
directories actually have frames (via FrameIndex availability).
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup
from PySide6.QtCore import Signal

from ui.preview.frame_index import ViewMode


# Display labels for each mode
_MODE_LABELS: dict[ViewMode, str] = {
    ViewMode.INPUT: "INPUT",
    ViewMode.MASK: "MASK",
    ViewMode.ALPHA: "ALPHA",
    ViewMode.FG: "FG",
    ViewMode.MATTE: "MATTE",
    ViewMode.COMP: "COMP",
    ViewMode.PROCESSED: "PROC",
}

_MODE_TOOLTIPS: dict[ViewMode, str] = {
    ViewMode.INPUT: "원본 입력 영상입니다(처리 전).\n\n단축키: F1",
    ViewMode.MASK: (
        "트래킹된 마스크입니다. SAM2 세그멘테이션 출력입니다.\n"
        "흰색 = 전경, 검은색 = 배경.\n"
        "MatAnyone2/VideoMaMa 보정 전의 바이너리 마스크입니다.\n\n"
        "단축키: F2"
    ),
    ViewMode.ALPHA: (
        "AlphaHint입니다. GVM, VideoMaMa, MatAnyone2가 생성합니다.\n"
        "흰색 = 전경, 검은색 = 배경.\n"
        "CorridorKey가 추론 전에 사용하는 가이드입니다.\n\n"
        "단축키: F3"
    ),
    ViewMode.FG: (
        "전경입니다. 그린 스필이 제거된 피사체입니다.\n"
        "디스필 중간 결과라 색이 달라 보일 수 있습니다.\n\n"
        "단축키: F4"
    ),
    ViewMode.MATTE: (
        "알파 매트입니다. 흰색 = 불투명, 검은색 = 투명.\n"
        "전경과 배경에 대한 AI의 신뢰도를 보여줍니다.\n\n"
        "단축키: F5"
    ),
    ViewMode.COMP: (
        "합성 결과입니다. 체크보드 위에 최종 키 결과를 보여줍니다.\n"
        "색상을 유지하면서 키 품질을 확인하기 가장 좋은 미리보기입니다.\n\n"
        "단축키: F6"
    ),
    ViewMode.PROCESSED: (
        "Processed 출력입니다. 제작용 RGBA(스트레이트, 리니어)입니다.\n"
        "Resolve, Premiere, 합성 도구용입니다.\n"
        "미리보기에서는 저장된 이미지를 검은색 위에 합성해 표시합니다.\n"
        "최종 합성은 원하는 합성 도구에서 진행하세요.\n\n"
        "단축키: F7"
    ),
}


class ViewModeBar(QWidget):
    """Horizontal bar of toggle buttons for preview view modes.

    Button enable-state is the combination of two availability layers:

    * **Clip-level** (``set_available_modes``) — modes with zero frames
      anywhere in the clip stay permanently disabled.
    * **Per-stem** (``set_current_stem_availability``) — modes that have
      clip-level frames but none at the current stem are disabled on
      scrub. The currently selected mode is the one exception: it stays
      enabled even when its stem has no data, so the user's mode choice
      visually persists (the viewport falls back to showing the input
      frame in that case).
    """

    mode_changed = Signal(str)  # emits ViewMode.value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(2)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._buttons: dict[ViewMode, QPushButton] = {}
        # Clip-level availability: which modes have any frames at all.
        self._clip_available: set[ViewMode] = set()
        # Per-stem availability: which modes have a frame at the current
        # stem. Defaults to empty so we don't falsely enable buttons
        # before the first navigation computes availability.
        self._stem_present: set[ViewMode] = set()

        for i, mode in enumerate(ViewMode):
            btn = QPushButton(_MODE_LABELS[mode])
            btn.setCheckable(True)
            btn.setEnabled(False)
            btn.setFixedHeight(24)
            btn.setMinimumWidth(50)
            btn.setStyleSheet(self._button_style(False))
            btn.setToolTip(_MODE_TOOLTIPS.get(mode, ""))
            self._buttons[mode] = btn
            self._button_group.addButton(btn, i)
            layout.addWidget(btn)

        # Default to COMP
        self._buttons[ViewMode.COMP].setChecked(True)

        self._button_group.idClicked.connect(self._on_mode_clicked)
        layout.addStretch()


    def set_available_modes(self, modes: list[ViewMode]) -> None:
        """Register which modes have any frames in the whole clip.

        This is the clip-level gate — called on clip load and whenever
        the frame index is rebuilt. Until ``set_current_stem_availability``
        is called with a concrete stem, all clip-available modes are
        assumed present (so the UI isn't momentarily empty).
        """
        self._clip_available = set(modes)
        # Default stem_present to match clip_available so the bar isn't
        # all-disabled between clip load and first navigation.
        self._stem_present = set(self._clip_available)
        self._refresh_all_buttons()

        # If current mode fell out of clip-level availability, switch to
        # the most useful fallback that is available.
        current = self.current_mode()
        if current not in self._clip_available and self._clip_available:
            for fallback in [ViewMode.COMP, ViewMode.ALPHA, ViewMode.INPUT]:
                if fallback in self._clip_available:
                    self._buttons[fallback].setChecked(True)
                    self._on_mode_clicked(list(ViewMode).index(fallback))
                    return
            first = next(iter(self._clip_available))
            self._buttons[first].setChecked(True)
            self._on_mode_clicked(list(ViewMode).index(first))

    def set_current_stem_availability(self, modes_with_current_frame) -> None:
        """Per-stem availability update.

        Called on every scrub. Modes that have no frame at the current
        stem become unclickable. The currently selected mode is always
        kept enabled even if its stem is empty, so the user's selection
        visually persists and the viewport can fall back to showing the
        input frame without the bar flickering.

        Args:
            modes_with_current_frame: Iterable of :class:`ViewMode`
                values that have a frame at the currently displayed stem.
        """
        self._stem_present = set(modes_with_current_frame)
        self._refresh_all_buttons()

    def current_mode(self) -> ViewMode:
        """Return the currently selected ViewMode."""
        checked_id = self._button_group.checkedId()
        if checked_id >= 0:
            return list(ViewMode)[checked_id]
        return ViewMode.COMP

    def _on_mode_clicked(self, button_id: int) -> None:
        mode = list(ViewMode)[button_id]
        # Selection changed — refresh so the new active button gets the
        # yellow style and the old one loses it. Enable-state is also
        # re-evaluated in case the newly selected mode was keeping its
        # own enable bit forced on and now doesn't need to.
        self._refresh_all_buttons()
        self.mode_changed.emit(mode.value)

    def _refresh_all_buttons(self) -> None:
        """Recompute enabled + style for every button."""
        current = self.current_mode()
        for mode, btn in self._buttons.items():
            clip_ok = mode in self._clip_available
            stem_ok = mode in self._stem_present
            # Currently selected mode stays enabled as long as it has any
            # clip-level frames, even if the current stem is empty.
            # Other modes require both clip-level and per-stem frames.
            if mode == current:
                enabled = clip_ok
            else:
                enabled = clip_ok and stem_ok
            btn.setEnabled(enabled)
            self._refresh_button_style(mode)

    def _refresh_button_style(self, mode: ViewMode) -> None:
        """Re-apply stylesheet for one button based on active state."""
        btn = self._buttons[mode]
        is_active = (self.current_mode() == mode)
        btn.setStyleSheet(self._button_style(is_active))

    @staticmethod
    def _button_style(active: bool) -> str:
        if active:
            return (
                "QPushButton { background-color: #FFF203; color: #000000; "
                "font-weight: 700; font-size: 10px; padding: 2px 6px; border: none; }"
                "QPushButton:disabled { background-color: #FFF203; color: #000000; }"
            )
        return (
            "QPushButton { background-color: #1A1900; color: #808070; "
            "font-size: 10px; padding: 2px 6px; border: 1px solid #2A2910; }"
            "QPushButton:hover { border-color: #454430; color: #E0E0E0; }"
            "QPushButton:disabled { color: #3A3A30; border-color: #1A1900; }"
        )
