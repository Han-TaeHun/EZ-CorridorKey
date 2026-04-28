# UI Layer Architecture

MainWindow 구성, Mixin 역할 분담, Widget/Worker 구조.

---

## MainWindow 상속 구조

```mermaid
graph TD
    MW["MainWindow<br/>ui/main_window.py:242<br/>QMainWindow"]

    MW --> MenuM["MenuMixin<br/>menu_mixin.py<br/>메뉴 바 (File/Edit/View/Help)"]
    MW --> ShortM["ShortcutsMixin<br/>shortcuts_mixin.py<br/>키보드 단축키"]
    MW --> ClipM["ClipMixin<br/>clip_mixin.py<br/>클립 선택·추가·제거·상태"]
    MW --> ImportM["ImportMixin<br/>import_mixin.py<br/>프로젝트/클립 임포트"]
    MW --> AlphaM["AlphaImportMixin<br/>alpha_import_mixin.py<br/>Alpha hint 임포트"]
    MW --> AnnoM["AnnotationMixin<br/>annotation_mixin.py<br/>SAM2 마스크 페인팅"]
    MW --> InfM["InferenceMixin<br/>inference_mixin.py<br/>추론 파라미터·live preview"]
    MW --> RunM["ModelRunMixin<br/>model_run_mixin.py<br/>GVM·SAM2·VideoMaMa 실행 UI"]
    MW --> WorkM["WorkerMixin<br/>worker_mixin.py<br/>백그라운드 워커 생명주기"]
    MW --> CancelM["CancelMixin<br/>cancel_mixin.py<br/>작업 취소"]
    MW --> ExpM["ExportMixin<br/>export_mixin.py<br/>결과 export"]
    MW --> SessM["SessionMixin<br/>session_mixin.py<br/>세션 로드·저장"]
    MW --> SetM["SettingsMixin<br/>settings_mixin.py<br/>Preferences 열기·적용"]
```

---

## MainWindow Layout & Widgets

```mermaid
graph TD
    Layout["MainWindow Layout"]

    Layout --> TitleBar["타이틀 바\n[CORRIDORKEY] [GPU | VRAM ##GB]"]
    Layout --> Center["중앙 영역 (QSplitter)"]
    Layout --> Bottom["하단 패널"]

    Center --> DualViewer["DualViewerPanel\ndual_viewer.py:26\n입력(왼) / 출력(오)"]
    Center --> ParamPanel["ParameterPanel\nparameter_panel.py:68\ndespill · edge blur · feather\n해상도 · 모델 · 파라미터"]

    DualViewer --> PV1["PreviewViewport (Input)\npreview_viewport.py:34"]
    DualViewer --> PV2["PreviewViewport (Output)\n+ ViewModeBar\nRGB·Alpha·Comp·FG·etc."]
    DualViewer --> Scrubber["FrameScrubber\nframe_scrubber.py:17\n프레임 타임라인·범위 선택"]

    Bottom --> IOTray["IOTrayPanel\nio_tray_panel.py:31\n클립 목록 + Export 목록"]
    Bottom --> Queue["QueuePanel\nqueue_panel.py:72\n진행 중/완료 작업"]
    Bottom --> Status["StatusBar\nstatus_bar.py:64\nVRAM · GPU온도 · 진행률 · 프레임"]

    IOTray --> ThumbCanvas["ThumbnailCanvas\nthumbnail_canvas.py:25\n클립 썸네일"]
```

---

## Background Workers

```mermaid
graph LR
    subgraph Workers["ui/workers/"]
        GPUJob["GPUJobWorker\ngpu_job_worker.py:49\nQThread\n\nGPU 작업 처리 루프\njob_queue → 모델 실행\n→ progress signal"]
        Thumb["ThumbnailGenerator\nthumbnail_worker.py\nQObject\n\n비동기 썸네일 생성\nQThreadPool 사용"]
        Monitor["GPUMonitor\ngpu_monitor.py:22\nQObject\n\nVRAM/온도 폴링\n1초 주기 → StatusBar"]
        Extract["ExtractWorker\nextract_worker.py\n\n비디오 → 이미지 시퀀스\nFFmpeg 기반"]
    end

    MW["MainWindow"] -->|"start on launch"| GPUJob
    MW -->|"start on launch"| Monitor
    MW -->|"on clip select"| Thumb
    MW -->|"on video import"| Extract
```

---

## Signal Flow (UI ↔ Backend)

```mermaid
sequenceDiagram
    participant User
    participant MW as MainWindow Mixins
    participant W as GPUJobWorker
    participant SVC as CorridorKeyService

    User->>MW: Run Inference 클릭 (InferenceMixin)
    MW->>SVC: job_queue.submit(InferenceJob)

    loop GPUJobWorker 루프
        W->>SVC: job_queue.next_job()
        SVC-->>W: InferenceJob
        W->>SVC: run_inference(clip, params)
        SVC-->>W: on_progress(current, total)
        W-->>MW: progress signal → StatusBar / QueuePanel
        W-->>MW: frame_ready signal → DualViewerPanel
    end

    W-->>MW: job_done signal
    MW->>MW: ClipMixin.refresh_clip_state()
    MW->>MW: IOTrayPanel.update()
```

---

## Annotation Workflow (SAM2)

```mermaid
flowchart TD
    User["사용자: 프레임에 페인팅"]
    Overlay["AnnotationOverlay\nannotation_overlay.py\n포인트·박스·마스크 입력"]
    AnnoMixin["AnnotationMixin\nannotation_mixin.py"]
    Preview["SAM2_PREVIEW Job\n→ SAM2Tracker.track()"]
    Mask["미리보기 마스크 표시\n(PreviewViewport 업데이트)"]
    Track["SAM2_TRACK Job\n→ SAM2Tracker.track_video()\n→ AlphaHint/ 저장"]
    State["clip.state = MASKED"]

    User --> Overlay
    Overlay --> AnnoMixin
    AnnoMixin -->|"즉시 프리뷰"| Preview
    Preview --> Mask
    User -->|"Track 버튼"| AnnoMixin
    AnnoMixin --> Track
    Track --> State
```

---

## SetupWizard Flow (첫 실행)

```mermaid
flowchart TD
    Start["앱 시작\nmain.py"]
    Check["SetupWizard.needs_setup()\n필수 모델 누락 or\n버전 변경?"]
    Skip["MainWindow 바로 표시"]
    Wizard["SetupWizard 표시\nsetup_wizard.py:603\n모델 목록 + 체크박스"]
    DL["_DownloadWorker (QThread)\nsetup_models.py 함수 호출\n진행 바 표시"]
    Done["SetupWizard 닫기\nMainWindow 표시"]

    Start --> Check
    Check -->|"No"| Skip
    Check -->|"Yes"| Wizard
    Wizard -->|"Download 버튼"| DL
    DL -->|"완료"| Done
    Skip --> Done
```
