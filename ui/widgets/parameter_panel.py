"""Right panel — alpha generation, tracking, and output config."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QCheckBox, QSpinBox, QPushButton, QGroupBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QEvent


def _no_scroll_wheel(widget: QWidget) -> QWidget:
    """Prevent mouse-wheel from changing value unless widget is focused.

    Users scrolling the panel accidentally change sliders/spinboxes.
    StrongFocus means the widget only accepts wheel events after a click.
    """
    widget.setFocusPolicy(Qt.StrongFocus)
    widget.installEventFilter(_WheelGuard.instance())
    return widget


class _WheelGuard(QWidget):
    """Event filter that ignores wheel events on unfocused widgets."""

    _singleton = None

    @classmethod
    def instance(cls):
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and not obj.hasFocus():
            event.ignore()
            return True
        return False

from backend import InferenceParams, OutputConfig


_COLOR_SPACE_TOOLTIP = (
    "추론 전에 CorridorKey가 소스를 해석하는 방식입니다.\n"
    "왼쪽 INPUT 뷰어는 항상 이 해석으로 표시되므로, 영상이 CorridorKey에서 어떻게 인식되는지와 맞아야 합니다.\n\n"
    "sRGB: 표준 감마 보정 영상(대부분의 카메라, 휴대폰 영상, PNG/JPG).\n"
    "Linear: 리니어 라이트 영상(진짜 리니어 EXR, CG 렌더).\n\n"
    "추론 실행 전에 변경하면 라이브 미리보기와 이후 생성하는 내보내기에 적용됩니다.\n"
    "이미 내보낸 파일은 이 값을 바꿔도 디스크에서 다시 작성되지 않습니다. 새 출력으로 저장하려면 추론을 다시 실행하세요.\n"
    "가능하면 포맷/메타데이터로 자동 감지하지만, INPUT 뷰어가 잘못 보이면 직접 바꿀 수 있습니다."
)

_LIVE_PREVIEW_TOOLTIP = (
    "Color Space, Despill, Refiner, Despeckle 값을 조정하면 현재 프레임을 즉시 다시 처리합니다.\n"
    "AlphaHint가 있는 READY 또는 COMPLETE 클립이 필요합니다.\n"
    "앱을 새로 실행한 직후에는 추론 엔진을 불러오느라 첫 미리보기 변경에 시간이 걸릴 수 있습니다.\n"
    "미리보기 업데이트는 디스크의 내보낸 파일을 다시 작성하지 않습니다. 저장하려면 추론을 다시 실행하세요."
)


class ParameterPanel(QWidget):
    """Right panel with all inference parameter controls."""

    params_changed = Signal()  # emitted when any parameter changes
    parallel_frames_changed = Signal(int)  # parallel engine count changed
    gvm_requested = Signal()      # GVM AUTO button clicked
    birefnet_requested = Signal(str)  # BiRefNet button clicked, emits model variant name
    videomama_requested = Signal() # VIDEOMAMA button clicked
    matanyone2_requested = Signal()  # MatAnyone2 button clicked
    track_masks_requested = Signal()  # Track annotation prompts into dense masks
    import_alpha_requested = Signal()  # Import own AlphaHint folder

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("paramPanel")
        self.setMinimumWidth(240)

        # Signal suppression flag (Codex: block signals during session restore)
        self._suppress_signals = False

        # Wrap all controls in a scroll area so they never squish below
        # their natural size — panel scrolls instead of compressing.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("paramPanelScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.NoFrame)

        inner = QWidget()
        inner.setObjectName("paramPanelInner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # ── ALPHA GENERATION section (Step 1) ──
        alpha_group = QGroupBox("ALPHA GENERATION")
        alpha_layout = QVBoxLayout(alpha_group)
        alpha_layout.setSpacing(8)

        # -- Automatic sub-section --
        auto_label = QLabel("Automatic")
        auto_label.setAlignment(Qt.AlignCenter)
        auto_label.setStyleSheet("color: #A0A090; font-size: 10px; margin: 0px 0 2px 0;")
        alpha_layout.addWidget(auto_label)

        self._gvm_btn = QPushButton("GVM AUTO")
        self._gvm_btn.setEnabled(False)
        self._gvm_btn.setToolTip(
            "전체 클립의 AlphaHint를 자동 생성합니다.\n"
            "GVM으로 전경/배경 분리를 예측합니다.\n"
            "클립이 RAW 상태(프레임 추출 완료)일 때 사용할 수 있습니다."
        )
        self._gvm_btn.clicked.connect(self.gvm_requested.emit)
        alpha_layout.addWidget(self._gvm_btn)

        # BiRefNet: button + model variant dropdown in a single row
        birefnet_row = QHBoxLayout()
        birefnet_row.setSpacing(4)
        self._birefnet_btn = QPushButton("BIREFNET")
        self._birefnet_btn.setEnabled(False)
        self._birefnet_btn.setToolTip(
            "BiRefNet으로 AlphaHint를 자동 생성합니다.\n"
            "완전 자동 방식이라 페인팅이나 어노테이션이 필요 없습니다.\n"
            "선택한 모델 변형은 처음 사용할 때 다운로드됩니다.\n\n"
            "Matting: 머리카락/투명 디테일에 가장 적합(권장).\n"
            "Portrait: 사람 클로즈업에 최적화.\n"
            "General: 전경/배경 분리 균형형.\n"
            "HR 변형: 2K/4K 영상용(VRAM을 더 많이 사용)."
        )
        self._birefnet_btn.clicked.connect(self._on_birefnet_clicked)
        birefnet_row.addWidget(self._birefnet_btn, 1)

        self._birefnet_model = QComboBox()
        self._birefnet_model.setMinimumWidth(120)
        self._birefnet_model.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._birefnet_model.setToolTip("BiRefNet 모델 변형입니다. 변경 사항은 다음 실행부터 적용됩니다.")
        # Populate from the wrapper's model registry
        from modules.BiRefNetModule.wrapper import BIREFNET_MODELS, DEFAULT_MODEL
        for display_name in BIREFNET_MODELS:
            self._birefnet_model.addItem(display_name)
        # Restore last-used model from QSettings
        from PySide6.QtCore import QSettings
        saved_model = QSettings().value("alpha/birefnet_model", DEFAULT_MODEL)
        idx = self._birefnet_model.findText(saved_model)
        if idx >= 0:
            self._birefnet_model.setCurrentIndex(idx)
        self._birefnet_model.currentTextChanged.connect(self._on_birefnet_model_changed)
        birefnet_row.addWidget(self._birefnet_model)
        alpha_layout.addLayout(birefnet_row)

        or_label = QLabel("— or —")
        or_label.setAlignment(Qt.AlignCenter)
        or_label.setStyleSheet("color: #808070; font-size: 11px;")
        alpha_layout.addWidget(or_label)

        # -- Guided sub-section --
        guided_label = QLabel("Requires brushstrokes")
        guided_label.setAlignment(Qt.AlignCenter)
        guided_label.setStyleSheet("color: #A0A090; font-size: 10px; margin: 0px 0 2px 0;")
        alpha_layout.addWidget(guided_label)

        annotate_hint = QLabel("Paint subject with 1, background with 2")
        annotate_hint.setAlignment(Qt.AlignCenter)
        annotate_hint.setWordWrap(True)
        annotate_hint.setStyleSheet("color: #A0A090; font-size: 10px; margin: 2px 0;")
        alpha_layout.addWidget(annotate_hint)

        self._track_masks_btn = QPushButton("TRACK MASK")
        self._track_masks_btn.setEnabled(False)
        self._track_masks_btn.setToolTip(
            "SAM2로 페인트한 프롬프트를 촘촘한 마스크 트랙으로 변환합니다.\n"
            "MatAnyone2 또는 VideoMaMa를 실행하기 전에 필요합니다.\n\n"
            "사용 방법:\n"
            "1. 1번을 눌러 초록 브러시를 선택합니다(전경, 남길 대상).\n"
            "2. 2번을 눌러 빨간 브러시를 선택합니다(배경, 제거할 영역).\n"
            "3. 왼쪽 뷰어의 영상 위에 스트로크를 그립니다.\n"
            "4. TRACK MASK를 클릭해 페인트한 프레임에서 SAM2 미리보기를 확인합니다.\n"
            "5. 미리보기가 적절하면 확인해서 모든 프레임으로 전파합니다."
        )
        self._track_masks_btn.clicked.connect(self.track_masks_requested.emit)
        alpha_layout.addWidget(self._track_masks_btn)

        self._annotation_info = QLabel("")
        self._annotation_info.setStyleSheet("color: #808070; font-size: 10px;")
        alpha_layout.addWidget(self._annotation_info)

        matanyone2_hint = QLabel("Requires paint strokes on frame 1")
        matanyone2_hint.setAlignment(Qt.AlignCenter)
        matanyone2_hint.setWordWrap(True)
        matanyone2_hint.setStyleSheet("color: #A0A090; font-size: 10px; margin: 2px 0;")
        alpha_layout.addWidget(matanyone2_hint)

        self._matanyone2_btn = QPushButton("MATANYONE2")
        self._matanyone2_btn.setEnabled(False)
        self._matanyone2_btn.setToolTip(
            "MatAnyone2 비디오 매팅으로 AlphaHint를 생성합니다.\n"
            "첫 프레임(프레임 1)에 페인트 스트로크가 필요합니다.\n\n"
            "1. 프레임 1(가장 첫 프레임)로 이동합니다.\n"
            "2. 전경(단축키 1)과 배경(단축키 2)을 페인트합니다.\n"
            "3. Track Mask를 클릭해 SAM2로 촘촘한 마스크를 생성합니다.\n"
            "4. MATANYONE2를 클릭해 시간적으로 안정적인 AlphaHint를 생성합니다."
        )
        self._matanyone2_btn.clicked.connect(self.matanyone2_requested.emit)
        alpha_layout.addWidget(self._matanyone2_btn)

        self._videomama_btn = QPushButton("VIDEOMAMA")
        self._videomama_btn.setEnabled(False)
        self._videomama_btn.setToolTip(
            "촘촘한 VideoMaMa 마스크 트랙에서 AlphaHint를 생성합니다.\n\n"
            "1. 전경/배경 프롬프트를 간단히 페인트합니다.\n"
            "2. Track Mask를 클릭해 SAM2로 촘촘한 마스크를 생성합니다.\n"
            "3. VIDEOMAMA를 클릭해 AlphaHint를 생성합니다."
        )
        self._videomama_btn.clicked.connect(self.videomama_requested.emit)
        alpha_layout.addWidget(self._videomama_btn)

        or_label2 = QLabel("— or —")
        or_label2.setAlignment(Qt.AlignCenter)
        or_label2.setStyleSheet("color: #808070; font-size: 11px;")
        alpha_layout.addWidget(or_label2)

        self._import_alpha_btn = QPushButton("IMPORT ALPHA")
        self._import_alpha_btn.setEnabled(False)
        self._import_alpha_btn.setToolTip(
            "이미지 폴더나 비디오 파일에서 AlphaHint를 가져옵니다.\n"
            "지원 형식: PNG/JPG/TIF/EXR 시퀀스 또는 MOV/MP4/ProRes 비디오.\n"
            "흰색 = 전경, 검은색 = 배경입니다.\n"
            "파일은 클립의 AlphaHint/ 폴더로 복사되며,\n"
            "클립은 추론 가능한 READY 상태로 전환됩니다."
        )
        self._import_alpha_btn.clicked.connect(self.import_alpha_requested.emit)
        alpha_layout.addWidget(self._import_alpha_btn)

        layout.addWidget(alpha_group)

        # ── INFERENCE section (Step 2) ──
        inf_group = QGroupBox("INFERENCE")
        inf_layout = QVBoxLayout(inf_group)
        inf_layout.setSpacing(8)

        # Color Space
        cs_row = QHBoxLayout()
        self._color_space_label = QLabel("Color Space")
        self._color_space_label.setFixedWidth(80)
        self._color_space_label.setToolTip(_COLOR_SPACE_TOOLTIP)
        cs_row.addWidget(self._color_space_label)
        self._color_space = _no_scroll_wheel(QComboBox())
        self._color_space.addItems(["sRGB", "Linear"])
        self._color_space.setToolTip(_COLOR_SPACE_TOOLTIP)
        self._color_space.currentIndexChanged.connect(self._emit_changed)
        cs_row.addWidget(self._color_space, 1)
        inf_layout.addLayout(cs_row)

        # Despill Strength (slider 0-10 → 0.0-1.0)
        self._despill_label = QLabel("Despill: 0.5")
        inf_layout.addWidget(self._despill_label)
        self._despill_slider = _no_scroll_wheel(QSlider(Qt.Horizontal))
        self._despill_slider.setRange(0, 10)
        self._despill_slider.setValue(5)
        self._despill_slider.setToolTip(
            "그린 스필 제거 강도(0.0-1.0)입니다.\n"
            "머리카락, 피부, 가장자리의 초록색 번짐을 제거합니다.\n"
            "1.0 = 최대 제거, 0.0 = 제거 없음(원본 색 유지)."
        )
        self._despill_slider.valueChanged.connect(self._on_despill_changed)
        inf_layout.addWidget(self._despill_slider)

        # Despeckle toggle + size
        despeckle_row = QHBoxLayout()
        self._despeckle_check = QCheckBox("Despeckle")
        self._despeckle_check.setChecked(True)
        self._despeckle_check.setToolTip(
            "자동 가비지 매트입니다.\n"
            "크기 임계값보다 작은 고립 영역을 버려 알파의 작은 떠 있는 노이즈와 점을 제거합니다."
        )
        self._despeckle_check.stateChanged.connect(self._on_despeckle_toggled)
        despeckle_row.addWidget(self._despeckle_check)
        self._despeckle_size = _no_scroll_wheel(QSpinBox())
        self._despeckle_size.setRange(50, 2000)
        self._despeckle_size.setValue(400)
        self._despeckle_size.setSuffix("px")
        self._despeckle_size.setToolTip(
            "영역이 유지되기 위한 최소 면적(픽셀)입니다.\n"
            "이 값보다 작은 고립된 알파 덩어리는 제거됩니다.\n"
            "낮을수록 디테일을 더 보존하고, 높을수록 매트가 더 깨끗해집니다."
        )
        self._despeckle_size.valueChanged.connect(self._emit_changed)
        despeckle_row.addWidget(self._despeckle_size, 1)
        inf_layout.addLayout(despeckle_row)

        # Refiner Scale (slider 0-30 → 0.0-3.0)
        self._refiner_label = QLabel("Refiner: 1.0")
        inf_layout.addWidget(self._refiner_label)
        self._refiner_slider = _no_scroll_wheel(QSlider(Qt.Horizontal))
        self._refiner_slider.setRange(0, 30)
        self._refiner_slider.setValue(10)
        self._refiner_slider.setToolTip(
            "가장자리 보정 강도(0.0-3.0)입니다.\n"
            "CNN 리파이너의 가장자리 보정량을 조절합니다.\n"
            "1.0 = 기본값, 0.0 = 백본만 사용(보정 없음),\n"
            "값이 높을수록 가장자리가 선명해지지만 아티팩트가 생길 수 있습니다."
        )
        self._refiner_slider.valueChanged.connect(self._on_refiner_changed)
        inf_layout.addWidget(self._refiner_slider)

        # Live Preview toggle
        self._live_preview = QCheckBox("Live Preview")
        self._live_preview.setChecked(True)
        self._live_preview.setToolTip(_LIVE_PREVIEW_TOOLTIP)
        inf_layout.addWidget(self._live_preview)

        layout.addWidget(inf_group)

        # ── OUTPUT FORMAT section (Step 3) ──
        out_group = QGroupBox("OUTPUT")
        out_layout = QVBoxLayout(out_group)
        out_layout.setSpacing(6)

        # FG
        fg_row = QHBoxLayout()
        self._fg_check = QCheckBox("FG")
        self._fg_check.setChecked(False)
        self._fg_check.setToolTip(
            "전경 출력입니다. 검은 배경 위에 디스필 처리된 피사체를 저장합니다.\n"
            "머리카락과 가장자리의 그린 스필이 제거됩니다.\n"
            "스트레이트 알파입니다(프리멀티플라이 아님)."
        )
        fg_row.addWidget(self._fg_check, 1)
        self._fg_format = QComboBox()
        self._fg_format.addItems(["exr", "png"])
        self._fg_format.setFixedWidth(70)
        self._fg_format.setToolTip("EXR = 32비트 float(후반 작업용).\nPNG = 8비트(일반 용도).")
        fg_row.addWidget(self._fg_format)
        out_layout.addLayout(fg_row)

        # Matte
        matte_row = QHBoxLayout()
        self._matte_check = QCheckBox("Matte")
        self._matte_check.setChecked(True)
        self._matte_check.setToolTip(
            "알파 매트입니다. 회색조 투명도 맵입니다.\n"
            "흰색 = 완전 불투명, 검은색 = 완전 투명.\n"
            "합성 소프트웨어에서 수동 키잉 제어에 사용합니다."
        )
        matte_row.addWidget(self._matte_check, 1)
        self._matte_format = QComboBox()
        self._matte_format.addItems(["exr", "png"])
        self._matte_format.setFixedWidth(70)
        self._matte_format.setToolTip("EXR = 32비트 float(후반 작업용).\nPNG = 8비트(일반 용도).")
        matte_row.addWidget(self._matte_format)
        out_layout.addLayout(matte_row)

        # Comp
        comp_row = QHBoxLayout()
        self._comp_check = QCheckBox("Comp")
        self._comp_check.setChecked(False)
        self._comp_check.setToolTip(
            "합성 미리보기 출력입니다. 체크보드 위에 최종 키 결과를 보여줍니다.\n"
            "키 품질을 확인하기 가장 좋은 표현입니다.\n"
            "색상은 원본 입력과 최대한 일치합니다."
        )
        comp_row.addWidget(self._comp_check, 1)
        self._comp_format = QComboBox()
        self._comp_format.addItems(["png", "exr"])
        self._comp_format.setFixedWidth(70)
        self._comp_format.setToolTip("PNG = 투명도를 포함한 8비트.\nEXR = 32비트 float(후반 작업용).")
        comp_row.addWidget(self._comp_format)
        out_layout.addLayout(comp_row)

        # Processed
        proc_row = QHBoxLayout()
        self._proc_check = QCheckBox("Processed")
        self._proc_check.setChecked(False)
        self._proc_check.setToolTip(
            "Processed 출력입니다. 제작용 RGBA(스트레이트, 리니어)입니다.\n"
            "Resolve, Premiere, 합성 도구로 가져가기 좋게 설계되었습니다.\n"
            "디스필과 가비지 매트 정리가 적용됩니다."
        )
        proc_row.addWidget(self._proc_check, 1)
        self._proc_format = QComboBox()
        self._proc_format.addItems(["exr", "png"])
        self._proc_format.setFixedWidth(70)
        self._proc_format.setToolTip("EXR = 32비트 float(Processed에 권장).\nPNG = 8비트(스트레이트 리니어 RGBA에는 손실 가능).")
        proc_row.addWidget(self._proc_format)
        out_layout.addLayout(proc_row)

        layout.addWidget(out_group)

        # ── PERFORMANCE section ──
        perf_group = QGroupBox("PERFORMANCE")
        perf_layout = QVBoxLayout(perf_group)
        perf_layout.setSpacing(6)

        parallel_row = QHBoxLayout()
        parallel_label = QLabel("Parallel frames")
        parallel_row.addWidget(parallel_label, 1)
        self._parallel_spin = QSpinBox()
        self._parallel_spin.setRange(1, 64)
        self._parallel_spin.setToolTip(
            "병렬 엔진으로 여러 프레임을 동시에 처리합니다.\n\n"
            "엔진을 하나 추가할 때마다 모델 전체 사본이 하나 더 로드됩니다.\n"
            "CUDA: 엔진당 약 6-8GB VRAM을 사용합니다.\n\n"
            "기본값: 1(가장 안전). 먼저 2를 시도한 뒤 안정적이면 늘리세요.\n\n"
            "실험적 기능: 8보다 큰 값은 RTX 6000 같은 고메모리 CUDA 시스템용입니다.\n"
            "메모리가 부족하면 앱이 자동으로 가능한 엔진 수까지 줄입니다.\n\n"
            "현재는 CUDA에서만 지원합니다. Apple Silicon에서는 아직 지원하지 않습니다."
        )
        self._parallel_spin.setFixedWidth(60)
        from ui.widgets.preferences_dialog import get_setting_int, KEY_PARALLEL_CLIPS, DEFAULT_PARALLEL_CLIPS
        self._parallel_spin.setValue(get_setting_int(KEY_PARALLEL_CLIPS, DEFAULT_PARALLEL_CLIPS))
        self._parallel_spin.valueChanged.connect(self._on_parallel_changed)
        parallel_row.addWidget(self._parallel_spin)
        perf_layout.addLayout(parallel_row)

        layout.addWidget(perf_group)

        layout.addStretch(1)

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # Middle-click reset: map widget → (setter_callable, default_value)
        self._middle_click_defaults: dict[QWidget, tuple] = {
            self._despill_slider: (self._despill_slider.setValue, 5),       # 0.5
            self._refiner_slider: (self._refiner_slider.setValue, 10),      # 1.0
            self._despeckle_size: (self._despeckle_size.setValue, 400),      # 400px
        }
        for widget in self._middle_click_defaults:
            widget.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        """Middle-click resets a control to its default value."""
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.MiddleButton:
            if obj in self._middle_click_defaults:
                setter, default = self._middle_click_defaults[obj]
                setter(default)
                return True
        return super().eventFilter(obj, event)

    def _emit_changed(self) -> None:
        """Emit params_changed unless signals are suppressed."""
        if not self._suppress_signals:
            self.params_changed.emit()

    def _on_despeckle_toggled(self, state: int) -> None:
        self._emit_changed()

    def _on_despill_changed(self, value: int) -> None:
        display = value / 10.0
        self._despill_label.setText(f"Despill: {display:.1f}")
        self._emit_changed()

    def _on_refiner_changed(self, value: int) -> None:
        display = value / 10.0
        self._refiner_label.setText(f"Refiner: {display:.1f}")
        self._emit_changed()

    def _on_birefnet_clicked(self) -> None:
        """Emit birefnet_requested with the currently selected model variant."""
        self.birefnet_requested.emit(self._birefnet_model.currentText())

    def _on_birefnet_model_changed(self, text: str) -> None:
        """Persist the selected BiRefNet model variant to QSettings."""
        from PySide6.QtCore import QSettings
        QSettings().setValue("alpha/birefnet_model", text)

    def _on_parallel_changed(self, value: int) -> None:
        from PySide6.QtCore import QSettings
        from ui.widgets.preferences_dialog import KEY_PARALLEL_CLIPS
        QSettings().setValue(KEY_PARALLEL_CLIPS, value)
        self.parallel_frames_changed.emit(value)

    @property
    def live_preview_enabled(self) -> bool:
        return self._live_preview.isChecked()

    def get_params(self) -> InferenceParams:
        """Snapshot current parameter values into a frozen InferenceParams."""
        return InferenceParams(
            input_is_linear=self._color_space.currentIndex() == 1,
            despill_strength=self._despill_slider.value() / 10.0,
            auto_despeckle=self._despeckle_check.isChecked(),
            despeckle_size=self._despeckle_size.value(),
            despeckle_dilation=25,  # fixed default
            despeckle_blur=5,       # fixed default
            refiner_scale=self._refiner_slider.value() / 10.0,
        )

    def get_output_config(self) -> OutputConfig:
        """Snapshot current output format configuration."""
        from ui.widgets.preferences_dialog import (
            KEY_EXR_COMPRESSION, DEFAULT_EXR_COMPRESSION, get_setting_str,
        )
        return OutputConfig(
            fg_enabled=self._fg_check.isChecked(),
            fg_format=self._fg_format.currentText(),
            matte_enabled=self._matte_check.isChecked(),
            matte_format=self._matte_format.currentText(),
            comp_enabled=self._comp_check.isChecked(),
            comp_format=self._comp_format.currentText(),
            processed_enabled=self._proc_check.isChecked(),
            processed_format=self._proc_format.currentText(),
            exr_compression=get_setting_str(KEY_EXR_COMPRESSION, DEFAULT_EXR_COMPRESSION),
        )

    def auto_detect_color_space(self, prefer_linear: bool) -> None:
        """Auto-set color space based on input format.

        Standalone linear EXR sequences → Linear, video-derived footage → sRGB.
        """
        target = 1 if prefer_linear else 0  # 1=Linear, 0=sRGB
        if self._color_space.currentIndex() != target:
            self._color_space.setCurrentIndex(target)

    def set_input_is_linear(self, input_is_linear: bool) -> None:
        """Programmatically set Color Space without emitting params_changed."""
        self._suppress_signals = True
        try:
            self._color_space.setCurrentIndex(1 if input_is_linear else 0)
        finally:
            self._suppress_signals = False

    def set_params(self, params: InferenceParams) -> None:
        """Load parameter values (e.g. from a saved session).

        Suppresses signals during restore to prevent event storms (Codex).
        """
        self._suppress_signals = True
        try:
            self._color_space.setCurrentIndex(1 if params.input_is_linear else 0)
            self._despill_slider.setValue(int(params.despill_strength * 10))
            self._despeckle_check.setChecked(params.auto_despeckle)
            self._despeckle_size.setValue(params.despeckle_size)
            # despeckle_dilation / despeckle_blur: no longer exposed in UI (fixed defaults)
            self._refiner_slider.setValue(int(params.refiner_scale * 10))
        finally:
            self._suppress_signals = False

    def set_output_config(self, config: OutputConfig) -> None:
        """Load output config values (e.g. from a saved session)."""
        self._suppress_signals = True
        try:
            self._fg_check.setChecked(config.fg_enabled)
            self._fg_format.setCurrentText(config.fg_format)
            self._matte_check.setChecked(config.matte_enabled)
            self._matte_format.setCurrentText(config.matte_format)
            self._comp_check.setChecked(config.comp_enabled)
            self._comp_format.setCurrentText(config.comp_format)
            self._proc_check.setChecked(config.processed_enabled)
            self._proc_format.setCurrentText(config.processed_format)
        finally:
            self._suppress_signals = False

    def set_gvm_enabled(self, enabled: bool) -> None:
        """Enable/disable GVM button based on clip state."""
        self._gvm_btn.setEnabled(enabled)

    def set_birefnet_enabled(self, enabled: bool) -> None:
        """Enable/disable BiRefNet button based on clip state."""
        self._birefnet_btn.setEnabled(enabled)

    def set_videomama_enabled(self, enabled: bool) -> None:
        """Enable/disable VideoMaMa button based on clip state."""
        self._videomama_btn.setEnabled(enabled)

    def set_matanyone2_enabled(self, enabled: bool) -> None:
        """Enable/disable MatAnyone2 button based on clip state."""
        self._matanyone2_btn.setEnabled(enabled)

    def set_import_alpha_enabled(self, enabled: bool) -> None:
        """Enable/disable Import Alpha button based on clip state."""
        self._import_alpha_btn.setEnabled(enabled)

    def set_annotation_info(self, annotated: int, total: int) -> None:
        """Update annotation frame counter."""
        if annotated > 0 and total > 0:
            self._annotation_info.setText(f"Painted: {annotated} / {total} frames")
            self._track_masks_btn.setEnabled(True)
        else:
            self._annotation_info.setText("")
            self._track_masks_btn.setEnabled(False)
