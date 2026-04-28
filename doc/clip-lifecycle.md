# Clip Lifecycle & Processing Pipelines

클립의 상태 전이, 파이프라인 라우팅, 작업 큐 흐름.

---

## Clip State Machine

```mermaid
stateDiagram-v2
    [*] --> EXTRACTING : 비디오 임포트 (ExtractWorker)
    [*] --> RAW : 이미지 시퀀스 임포트

    EXTRACTING --> RAW : 추출 완료

    RAW --> MASKED : SAM2 트래킹 완료\n(AlphaHint/ 생성)

    RAW --> READY : GVM / BiRefNet 자동 alpha 완료\n(AlphaHint/ 생성)
    MASKED --> READY : VideoMaMa / MatAnyone2 alpha 완료

    READY --> COMPLETE : run_inference() 완료\n(FG/ Matte/ Comp/ 생성)
    COMPLETE --> READY : 재처리 (파라미터 변경)

    RAW --> ERROR : 오류
    MASKED --> ERROR : 오류
    READY --> ERROR : 오류
    EXTRACTING --> ERROR : 오류
    ERROR --> RAW : 복구 시도

    note right of EXTRACTING
        비디오 → Frames/ 추출 중
        (FFmpeg, ExtractWorker)
    end note
    note right of MASKED
        Frames/ + AlphaHint/ 존재
        VideoMaMa/MatAnyone2 대기
    end note
    note right of READY
        AlphaHint/ 준비됨
        run_inference() 실행 가능
    end note
```

---

## Pipeline Routes

`run_inference()` 호출 시 clip 상태에 따라 자동 경로 결정됨 (`backend/clip_state.py`).

```mermaid
flowchart TD
    Start(["run_inference(clip)"])

    Start --> Chk{클립 상태?}

    Chk -->|"EXTRACTING / ERROR"| Skip["PipelineRoute.SKIP\n처리 불가"]

    Chk -->|"RAW\n+ annotation 없음"| GVM_Route["PipelineRoute.GVM_PIPELINE\n① GVM/BiRefNet auto alpha\n② run_inference()"]

    Chk -->|"RAW\n+ annotation 있음"| VM_Route["PipelineRoute.VIDEOMAMA_PIPELINE\n① SAM2 track → AlphaHint/\n② VideoMaMa/MatAnyone2 alpha\n③ run_inference()"]

    Chk -->|"MASKED"| VMI_Route["PipelineRoute.VIDEOMAMA_INFERENCE\n① VideoMaMa/MatAnyone2 alpha\n② run_inference()"]

    Chk -->|"READY / COMPLETE"| IO_Route["PipelineRoute.INFERENCE_ONLY\n① run_inference()"]

    GVM_Route --> Done(["COMPLETE"])
    VM_Route --> Done
    VMI_Route --> Done
    IO_Route --> Done
```

---

## End-to-End Processing Flow

```mermaid
sequenceDiagram
    actor User
    participant MW as MainWindow
    participant SVC as CorridorKeyService
    participant JQ as GPUJobQueue
    participant W as GPUJobWorker
    participant Model as Model Modules

    User->>MW: 클립 임포트
    MW->>SVC: add_clips_to_project()
    SVC-->>MW: ClipEntry list (state=RAW)

    User->>MW: GVM 실행 (또는 SAM2 annotation)
    MW->>JQ: submit(GVMJob)
    JQ->>W: next_job()
    W->>SVC: run_gvm(clip)
    SVC->>Model: GVMProcessor.process_frames()
    Model-->>SVC: AlphaHint/*.png 저장
    SVC-->>W: clip.state = READY
    W-->>MW: progress signal → QueuePanel 업데이트

    User->>MW: Run Inference 클릭
    MW->>JQ: submit(InferenceJob)
    JQ->>W: next_job()
    W->>SVC: run_inference(clip, params)
    SVC->>Model: CorridorKeyEngine.run()
    Model-->>SVC: FG/ Matte/ Comp/ 저장
    SVC-->>W: clip.state = COMPLETE
    W-->>MW: done signal → Viewer 업데이트

    User->>MW: Export
    MW->>SVC: export_video(clip)
    SVC-->>User: Output/result.mov
```

---

## Job Types (backend/job_queue.py)

| Job Type | 트리거 | 실행 모델 | 출력 |
|---|---|---|---|
| `INFERENCE` | Run 버튼 | CorridorKeyEngine | FG/ Matte/ Comp/ |
| `GVM_ALPHA` | GVM 버튼 | GVMProcessor | AlphaHint/ |
| `BIREFNET_ALPHA` | BiRefNet 버튼 | BiRefNetProcessor | AlphaHint/ |
| `SAM2_PREVIEW` | Annotation 페인팅 | SAM2Tracker | 미리보기 마스크 (메모리) |
| `SAM2_TRACK` | SAM2 Track 버튼 | SAM2Tracker | AlphaHint/ |
| `VIDEOMAMA_ALPHA` | VideoMaMa 버튼 | VideoInferencePipeline | AlphaHint/ |
| `MATANYONE2_ALPHA` | MatAnyone2 버튼 | MatAnyone2Processor | AlphaHint/ |
| `VIDEO_EXTRACT` | 비디오 임포트 | FFmpeg | Frames/ |
| `VIDEO_STITCH` | Export | FFmpeg | Output/*.mov |
| `PREVIEW_REPROCESS` | 파라미터 변경 | CorridorKeyEngine | 미리보기 (메모리) |
