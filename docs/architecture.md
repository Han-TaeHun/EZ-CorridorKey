# EZ-CorridorKey Architecture

## 1. System Overview

```mermaid
graph TD
    subgraph Entry["Entry Points"]
        main["main.py"]
        bat["2-start.bat / 2-start.sh"]
    end

    subgraph UI["UI Layer (PySide6)"]
        MW["MainWindow\n(12 mixins)"]
        Workers["Workers\nextract / gpu_job / thumbnail / gpu_monitor"]
        Widgets["Widgets\ndual_viewer / parameter_panel / timeline / dialogs"]
    end

    subgraph Backend["Backend Layer"]
        Service["CorridorKeyService\n(facade)"]
        JobQueue["GPUJobQueue"]
        ClipState["ClipEntry FSM"]
        Project["Project v1/v2"]
    end

    subgraph Models["Inference Models"]
        CK["CorridorKey\n(core keyer)"]
        GVM["GVM\n(auto alpha)"]
        BiRefNet["BiRefNet\n(salient object)"]
        SAM2["SAM2\n(tracking)"]
        VideoMaMa["VideoMaMa\n(guided matte)"]
        MatAnyone2["MatAnyone2\n(learning matte)"]
    end

    bat --> main
    main --> MW
    MW --> Workers
    MW --> Widgets
    Workers --> JobQueue
    JobQueue --> Service
    Service --> ClipState
    Service --> Project
    Service --> CK
    Service --> GVM
    Service --> BiRefNet
    Service --> SAM2
    Service --> VideoMaMa
    Service --> MatAnyone2
```

---

## 2. CorridorKeyService — Mixin Composition

```mermaid
classDiagram
    class CorridorKeyService {
        +_engine_pool: list
        +_active_model: _ActiveModel
        +_gpu_lock: Lock
        +job_queue: GPUJobQueue
        +detect_device()
        +scan_clips()
        +set_model_resolution()
        +set_pool_size()
        +_begin_inference()
        +_end_inference()
    }

    class ModelManagerMixin {
        +_get_ck_engine()
        +_get_gvm_processor()
        +_get_sam2_tracker()
        +_get_videomama_pipeline()
        +_get_matanyone2_processor()
        +_get_birefnet_processor()
        +_unload_all()
        +_request_model_switch()
    }

    class FrameOpsMixin {
        +load_frame()
        +save_frame()
        +linear_to_srgb()
        +srgb_to_linear()
        +frames_to_display()
    }

    class InferenceMixin {
        +run_inference()
        +_run_single_frame()
        +_run_parallel_frames()
    }

    class PipelinesMixin {
        +run_gvm()
        +run_birefnet()
        +run_sam2_tracking()
        +preview_sam2_prompt()
        +run_videomama()
        +run_matanyone2()
    }

    CorridorKeyService --|> ModelManagerMixin
    CorridorKeyService --|> FrameOpsMixin
    CorridorKeyService --|> InferenceMixin
    CorridorKeyService --|> PipelinesMixin
```

---

## 3. Clip State Machine

```mermaid
stateDiagram-v2
    [*] --> EXTRACTING : video imported

    EXTRACTING --> RAW : frames extracted (FFmpeg)
    EXTRACTING --> ERROR : extraction failed

    RAW --> MASKED : alpha hint painted\nor auto-alpha run
    RAW --> READY : skip alpha hint
    RAW --> ERROR

    MASKED --> READY : alpha accepted
    MASKED --> ERROR

    READY --> COMPLETE : inference finished
    READY --> ERROR : inference failed

    ERROR --> EXTRACTING : retry

    note right of READY
        Inference can run
        CorridorKey keying
    end note
```

---

## 4. GPU Job Queue Flow

```mermaid
sequenceDiagram
    participant UI as UI Thread (MainWindow)
    participant Q as GPUJobQueue
    participant W as gpu_job_worker (QThread)
    participant S as CorridorKeyService

    UI->>Q: submit(GPUJob)
    Note over Q: dedup check\npreview jobs → replace latest

    loop Worker run loop
        W->>Q: next_job()
        Q-->>W: GPUJob
        W->>Q: start_job(job)
        W->>S: dispatch (inference / gvm / sam2 / …)
        S-->>W: on_progress callbacks
        W->>Q: report_progress()
        alt success
            W->>Q: complete_job(job)
        else cancelled
            W->>Q: mark_cancelled(job)
        else error
            W->>Q: fail_job(job, error)
        end
    end

    Q-->>UI: on_completion / on_error / on_progress signals
```

---

## 5. Model Residency & VRAM Policy

```mermaid
flowchart TD
    Start(["request new model"]) --> Check{"same model\nalready active?"}
    Check -- yes --> Use["use existing\n(no reload)"]
    Check -- no --> Gate["_request_model_switch()\nwait for _inference_idle"]
    Gate --> Unload["unload current model\ntorch.cuda.empty_cache()"]
    Unload --> Load["load new model\nto GPU"]
    Load --> SetActive["_active_model = NEW"]
    SetActive --> Use

    subgraph Models
        NONE["NONE"]
        CK_M["INFERENCE\n(CorridorKey engine pool)"]
        GVM_M["GVM"]
        SAM2_M["SAM2"]
        VM_M["VIDEOMAMA"]
        MA_M["MATANYONE2"]
        BR_M["BIREFNET"]
    end

    SetActive --> Models
```

---

## 6. UI MainWindow Mixin Structure

```mermaid
graph LR
    subgraph MainWindow
        menu["MenuMixin\nFile/Edit/View menus"]
        shortcuts["ShortcutsMixin\nhotkey registry"]
        clip["ClipMixin\nselection & state display"]
        import_["ImportMixin\nvideo / image seq import"]
        inference["InferenceMixin\nparams UI, run keying"]
        alpha["AlphaImportMixin\nimport pre-made alpha"]
        model_run["ModelRunMixin\nGVM / SAM2 / VideoMaMa / MatAnyone2"]
        cancel["CancelMixin\njob cancellation"]
        worker["WorkerMixin\nthread lifecycle"]
        annotation["AnnotationMixin\npaint strokes"]
        export_["ExportMixin\nformat & file write"]
        session["SessionMixin\nproject save/load"]
        settings["SettingsMixin\npreferences dialog"]
    end

    worker --> model_run
    worker --> inference
    clip --> inference
    clip --> model_run
    annotation --> model_run
```

---

## 7. Frame Processing Pipeline (CorridorKey Inference)

```mermaid
flowchart LR
    Input["Input Frame\n(PNG/EXR)"] --> ColorIn["Color Space\nsRGB → linear\n(if input_is_linear=False)"]
    ColorIn --> Engine["CorridorKey Engine\n(ViT-based keyer)"]
    Engine --> Alpha["Alpha Matte"]
    Engine --> FG["Foreground"]
    Alpha --> Despeckle["Auto Despeckle\n(optional)"]
    Despeckle --> EdgeOps["Edge Erode/Blur"]
    EdgeOps --> Despill["Despill\n(green spill removal)"]
    Despill --> Refiner["Refiner\n(detail recovery)"]
    Refiner --> Output

    subgraph Output["Outputs (per OutputConfig)"]
        FG_out["FG (EXR/PNG)"]
        Matte_out["Matte (EXR/PNG)"]
        Comp_out["Comp (PNG)"]
        Proc_out["Processed (EXR)"]
    end
```

---

## 8. Project On-Disk Layout

```mermaid
graph TD
    subgraph v2["v2 Layout (current)"]
        proj2["ProjectRoot/"]
        clips_dir["clips/"]
        clip1["clip_name/"]
        input_dir["Input/  ← extracted frames"]
        alpha_dir["AlphaHint/  ← painted masks"]
        output_dir["Output/  ← inference results"]
        meta2["project.json"]

        proj2 --> clips_dir
        proj2 --> meta2
        clips_dir --> clip1
        clip1 --> input_dir
        clip1 --> alpha_dir
        clip1 --> output_dir
    end

    subgraph v1["v1 Layout (legacy read-only)"]
        proj1["ProjectRoot/"]
        frames1["Frames/"]
        source1["Source/"]
        alphahint1["AlphaHint/"]
        meta1["project.json"]

        proj1 --> frames1
        proj1 --> source1
        proj1 --> alphahint1
        proj1 --> meta1
    end
```

---

## 9. SAM2 Tracking Data Flow

```mermaid
flowchart TD
    Paint["User paint strokes\n(annotation_overlay)"] --> Prompts["PromptFrame list\n(positive/negative points,\nbox, mask)"]
    Prompts --> Sanitize["SAM2Tracker._sanitize_prompt_frame()\nclamp to frame bounds"]
    Sanitize --> Forward["Forward propagation\nfrom earliest prompt"]
    Forward --> Reverse["Reverse propagation\nfrom latest prompt\n(reset_state between passes)"]
    Reverse --> Masks["Dense mask per frame\n(uint8 0/255)"]
    Masks --> AlphaHint["Written to\nclip/AlphaHint/"]
    AlphaHint --> Ready["ClipState → MASKED"]

    Ckpt["sam2_tracker/checkpoints/\n*.pt  ← manual install"] --> Tracker["SAM2Tracker\n(wrapper.py)"]
    Tracker --> Forward
```
