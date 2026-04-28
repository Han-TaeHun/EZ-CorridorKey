# EZ-CorridorKey Architecture Overview

전체 레이어 구조와 데이터 흐름의 큰 그림.

---

## System Layers

```mermaid
graph TD
    Entry["main.py<br/>run_gui() / run_cli()"]

    subgraph UI["UI Layer (PySide6)"]
        App["ui/app.py<br/>PySide6 App"]
        MW["ui/main_window.py<br/>MainWindow + 13 Mixins"]
        Workers["ui/workers/<br/>GPUJobWorker · ThumbnailGenerator · GPUMonitor"]
        Widgets["ui/widgets/<br/>DualViewer · ParameterPanel · QueuePanel · IOTrayPanel · ..."]
    end

    subgraph Service["Backend Service Layer"]
        SVC["backend/service/core.py<br/>CorridorKeyService"]
        JQ["backend/job_queue.py<br/>GPUJobQueue"]
        BE["backend/project.py · clip_state.py · frame_io.py · ffmpeg_tools/"]
    end

    subgraph Models["Model Modules"]
        CK["CorridorKeyModule/<br/>CorridorKeyEngine (main keying)"]
        SAM2["sam2_tracker/<br/>SAM2Tracker (interactive tracking)"]
        GVM["gvm_core/<br/>GVMProcessor (auto alpha)"]
        VM["VideoMaMaInferenceModule/<br/>VideoInferencePipeline (diffusion alpha)"]
        BRN["modules/BiRefNetModule/<br/>BiRefNetProcessor (auto alpha)"]
        MA2["modules/MatAnyone2Module/<br/>MatAnyone2Processor (mask alpha)"]
    end

    subgraph Storage["Storage"]
        Proj["Projects/<br/>project.json · clips/ · clip.json"]
        Ckpt["Checkpoints (per-module)<br/>CorridorKeyModule/checkpoints/<br/>sam2_tracker/checkpoints/<br/>gvm_core/weights/ · ..."]
    end

    Entry --> App
    App --> MW
    MW --> Workers
    MW --> Widgets
    MW --> SVC

    Workers -->|"job dispatch"| JQ
    SVC --> JQ
    SVC --> CK
    SVC --> SAM2
    SVC --> GVM
    SVC --> VM
    SVC --> BRN
    SVC --> MA2
    SVC --> BE

    CK --> Ckpt
    SAM2 --> Ckpt
    GVM --> Ckpt
    VM --> Ckpt
    BRN --> Ckpt
    MA2 --> Ckpt
    BE --> Proj
```

---

## Project Folder Structure (Runtime)

```mermaid
graph TD
    Root["Projects/"]
    P["260301_093000_MyClip/<br/>project.json"]
    C["clips/"]
    Clip["MyClip/  (clip root)"]
    Src["Source/  (원본 비디오)"]
    Frames["Frames/  (추출된 프레임)"]
    Alpha["AlphaHint/  (alpha hint 마스크)"]
    Out["Output/"]
    FG["FG/  (전경 RGBA)"]
    Matte["Matte/  (알파 채널)"]
    Comp["Comp/  (합성)"]
    ClipJson["clip.json  (상태, 메타)"]

    Root --> P
    P --> C
    C --> Clip
    Clip --> Src
    Clip --> Frames
    Clip --> Alpha
    Clip --> Out
    Clip --> ClipJson
    Out --> FG
    Out --> Matte
    Out --> Comp
```

---

## Model Checkpoint Locations

| 모델 | 위치 | 다운로드 방식 |
|---|---|---|
| CorridorKey | `CorridorKeyModule/checkpoints/*.pth` | HuggingFace single file |
| SAM2 | `sam2_tracker/checkpoints/models--facebook--...` | HuggingFace hub cache |
| GVM | `gvm_core/weights/` | HuggingFace snapshot |
| VideoMaMa | `VideoMaMaInferenceModule/checkpoints/` | HuggingFace snapshot |
| BiRefNet | `modules/BiRefNetModule/checkpoints/<variant>/` | HuggingFace snapshot |
| MatAnyone2 | `modules/MatAnyone2Module/checkpoints/matanyone2.pth` | GitHub Releases |
| CorridorKey MLX | `CorridorKeyModule/checkpoints/corridorkey_mlx.safetensors` | GitHub Releases |

> **SAM2 SSOT**: `sam2_tracker/paths.py` — `get_sam2_cache_dir()` 함수로 경로 결정. frozen 빌드는 `get_data_dir()` 하위로 변경됨.
