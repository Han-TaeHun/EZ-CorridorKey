import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
from PySide6.QtWidgets import QApplication

from ui.widgets.parameter_panel import ParameterPanel


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_color_space_tooltip_explains_preview_and_export_behavior():
    _app()
    panel = ParameterPanel()

    tooltip = panel._color_space.toolTip()

    assert "왼쪽 INPUT 뷰어" in tooltip
    assert "이후 생성하는 내보내기" in tooltip
    assert "디스크에서 다시 작성되지 않습니다" in tooltip
    assert "추론을 다시 실행하세요" in tooltip
    assert panel._color_space_label.toolTip() == tooltip


def test_live_preview_tooltip_mentions_engine_warmup_and_saved_outputs():
    _app()
    panel = ParameterPanel()

    tooltip = panel._live_preview.toolTip()

    assert "첫 미리보기 변경에 시간이 걸릴 수 있습니다" in tooltip
    assert "추론 엔진을 불러오느라" in tooltip
    assert "내보낸 파일을 다시 작성하지 않습니다" in tooltip


def test_parallel_frames_tooltip_is_cuda_only():
    _app()
    panel = ParameterPanel()

    tooltip = panel._parallel_spin.toolTip()

    assert "현재는 CUDA에서만 지원합니다" in tooltip
    assert "Apple Silicon에서는 아직 지원하지 않습니다" in tooltip
    assert "Apple Silicon with 64GB+ unified RAM" not in tooltip


def test_set_input_is_linear_updates_combo_without_emitting_params_changed():
    _app()
    panel = ParameterPanel()
    fired: list[bool] = []
    panel.params_changed.connect(lambda: fired.append(True))

    panel.set_input_is_linear(True)

    assert panel.get_params().input_is_linear is True
    assert fired == []
