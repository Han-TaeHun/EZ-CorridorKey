# Backend Service Layer

`CorridorKeyService`의 내부 구조, Mixin 상속, VRAM 관리 정책.

---

## CorridorKeyService 구성

```mermaid
graph TD
    SVC["CorridorKeyService<br/>backend/service/core.py:107"]

    SVC --> MM["ModelManagerMixin<br/>model_manager.py:32<br/>VRAM lifecycle 관리"]
    SVC --> FO["FrameOpsMixin<br/>frame_ops.py<br/>프레임 I/O · 색상 변환"]
    SVC --> IM["InferenceMixin<br/>inference.py:28<br/>run_inference() dispatcher"]
    SVC --> PM["PipelinesMixin<br/>pipelines.py:15"]

    PM --> APM["AutoPipelinesMixin<br/>pipelines_auto.py:20<br/>run_gvm() / run_birefnet()"]
    PM --> GPM["GuidedPipelinesMixin<br/>pipelines_guided.py:31<br/>run_sam2_*() / run_videomama_*() / run_matanyone2_*()"]

    IM --> PIM["InferenceParallelMixin<br/>inference_parallel.py<br/>pool_size > 1 병렬 처리"]
```

---

## ModelManagerMixin: VRAM 관리 정책

한 번에 **Heavy Model 1개**만 VRAM에 로드. 스위치 시 이전 모델을 CPU로 offload.

```mermaid
flowchart TD
    Call["_ensure_model(needed)"]

    Call --> Same{현재 로드 모델\n== needed?}
    Same -->|Yes| Done["반환 (no-op)"]

    Same -->|No| Busy{모델 스위치\n진행 중?}
    Busy -->|Yes| Wait["스위치 대기\n(새 추론 차단)"]
    Wait --> Unload

    Busy -->|No| Unload["_safe_offload(current_model)\n→ .to('cpu') + 참조 제거"]
    Unload --> Load["새 모델 로드\n_get_engine_pool() /\n_load_gvm_processor() / etc."]
    Load --> Done

    style Wait fill:#f9a825,color:#000
    style Unload fill:#ef5350,color:#fff
    style Load fill:#43a047,color:#fff
```

### _ActiveModel Enum (model_manager.py:21)

| 값 | 모델 |
|---|---|
| `NONE` | 아무 모델도 없음 |
| `INFERENCE` | CorridorKeyEngine |
| `GVM` | GVMProcessor |
| `SAM2` | SAM2Tracker |
| `VIDEOMAMA` | VideoInferencePipeline |
| `MATANYONE2` | MatAnyone2Processor |
| `BIREFNET` | BiRefNetProcessor |

---

## InferenceMixin: run_inference 흐름

```mermaid
flowchart TD
    RI["run_inference(clip, params, job, ...)"]

    RI --> Pool{pool_size > 1?}
    Pool -->|Yes| Par["_run_inference_parallel()\ninference_parallel.py\n여러 CorridorKeyEngine 동시 처리"]
    Pool -->|No| Seq["_run_inference_sequential()\n단일 엔진 순차 처리"]

    Par --> Frame["각 프레임:\n1. read_frame(Frames/)\n2. read_alpha(AlphaHint/)\n3. engine.run(input, alpha)\n4. write(FG/ Matte/ Comp/)"]
    Seq --> Frame

    Frame --> Chk{cancel_check()}
    Chk -->|"cancelled"| Cancel["JobCancelledError"]
    Chk -->|"ok"| Progress["on_progress(current, total)"]
    Progress --> Frame
```

---

## CorridorKeyService 주요 속성 (core.py:129)

| 속성 | 타입 | 역할 |
|---|---|---|
| `_engine_pool` | `list[CorridorKeyEngine]` | 추론 엔진 풀 (pool_size 개) |
| `_pool_size` | `int` | 병렬 엔진 수 (기본 1) |
| `_model_resolution` | `int` | 추론 해상도 (1024/2048) |
| `_device` | `str` | "cuda" / "cpu" / "mps" |
| `_active_model` | `_ActiveModel` | 현재 VRAM 로드 모델 |
| `_gpu_lock` | `threading.Lock` | GPU 상호배제 |
| `_job_queue` | `GPUJobQueue` | 작업 큐 (lazy init) |
| `_sam2_tracker` | `SAM2Tracker \| None` | SAM2 인스턴스 |
| `_gvm_processor` | `GVMProcessor \| None` | GVM 인스턴스 |
| `_birefnet_processor` | `BiRefNetProcessor \| None` | BiRefNet 인스턴스 |
| `_videomama_pipeline` | `VideoInferencePipeline \| None` | VideoMaMa 인스턴스 |
| `_matanyone2_processor` | `MatAnyone2Processor \| None` | MatAnyone2 인스턴스 |

---

## 모델별 로딩 경로 (model_manager.py)

```mermaid
flowchart LR
    Ensure["_ensure_model(needed)"]

    Ensure -->|"INFERENCE"| EngPool["_get_engine_pool()\n→ CorridorKeyEngine 생성\n→ checkpoint glob"]
    Ensure -->|"GVM"| GVMLoad["_load_gvm_processor()\n→ GVMProcessor(device)"]
    Ensure -->|"SAM2"| SAM2Load["_get_sam2_tracker()\n→ SAM2Tracker(model_id)\n→ .prepare()  ← hf_hub_download"]
    Ensure -->|"VIDEOMAMA"| VMLoad["VideoInferencePipeline()\n→ checkpoints/ 로드"]
    Ensure -->|"MATANYONE2"| MA2Load["MatAnyone2Processor()\n→ matanyone2.pth 로드"]
    Ensure -->|"BIREFNET"| BRNLoad["BiRefNetProcessor()\n→ snapshot_download or cache"]
```
