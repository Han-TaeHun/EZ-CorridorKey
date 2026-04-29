# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application
python main.py --gui                  # PySide6 desktop GUI (default)
python main.py --cli                  # original CLI wizard
python main.py --log-level DEBUG      # verbose logging

# Tests
pytest                                # run all tests
pytest -v                             # verbose
pytest -m "not gpu"                   # skip GPU-dependent tests
pytest tests/test_clip_state.py       # single test file

# Lint / format
ruff check                            # lint check
ruff format --check                   # formatting check
ruff format                           # auto-format (line length: 120)
```

Logs are written to `logs/backend/YYMMDD_HHMMSS_corridorkey.log`.

## Docs

`docs/architecture.md` contains Mermaid diagrams for all major subsystems. Refer to it before touching cross-cutting concerns:

| Diagram | What it shows |
|---|---|
| System Overview | Entry points → UI → Backend → Models |
| CorridorKeyService mixins | Class composition and responsibilities |
| Clip State Machine | FSM transitions and trigger conditions |
| GPU Job Queue Flow | Sequence from UI submit to worker dispatch |
| Model Residency & VRAM Policy | How model switching is gated |
| UI MainWindow Mixin Structure | Which mixin owns which concern |
| Frame Processing Pipeline | Per-frame inference stages |
| Project On-Disk Layout | v1 vs v2 folder structures |
| SAM2 Tracking Data Flow | Prompt → mask propagation |

## Architecture

### Service layer — mixin composition

`backend/service/core.py::CorridorKeyService` is the single facade exposed to the UI. It is built by mixing in:

| Mixin | Responsibility |
|---|---|
| `model_manager.py` | Load/unload CorridorKey, GVM, BiRefNet, SAM2, VideoMaMa, MatAnyone2 |
| `frame_ops.py` | Frame I/O and color-space conversion |
| `inference.py` / `inference_parallel.py` | Core CorridorKey keying pipeline |
| `pipelines_auto.py` | Automatic alpha (GVM, BiRefNet) |
| `pipelines_guided.py` | Annotation-guided alpha (SAM2, VideoMaMa, MatAnyone2) |
| `helpers.py` | Export and mask utilities |

**Critical invariant:** Only one heavy model is resident in VRAM at a time. `model_manager.py` enforces this with a gated threading protocol — any model switch must go through `_request_model_switch()` which blocks until the current GPU job finishes.

### Job queue

`backend/job_queue.py` serializes all GPU work. UI workers submit `GPUJob` objects (EXTRACT, GVM, BIREFNET, SAM2, VIDEOMAMA, MATANYONE2, INFERENCE); `ui/workers/gpu_job_worker.py` drains the queue in a background thread and dispatches to the service. Job cancellation is cooperative — jobs check a cancel event at frame boundaries.

### Clip state machine

`backend/clip_state.py::ClipEntry` owns all per-clip state. The FSM flows:
`EXTRACTING → RAW → MASKED → READY → COMPLETE` (with `ERROR` from any state).
The UI never mutates clip state directly — it calls service methods which advance the FSM.

### Project formats

`backend/project.py` supports two on-disk layouts:
- **v1** (legacy): flat `Frames/`, `Source/`, `AlphaHint/` dirs at project root
- **v2**: `clips/<clip_name>/` subdirectory per clip with `Input/`, `AlphaHint/`, `Output/`

Both formats are read transparently; new projects always write v2.

### UI — mixin-based MainWindow

`ui/main_window.py::MainWindow` is assembled from ~12 mixins in `ui/main_window_mixins/`. Each mixin owns one concern (import, inference, annotation, export, …). Widgets communicate upward by calling MainWindow methods; the service is accessed only through the worker layer, never directly from widget code.

Frame display goes through `ui/preview/display_transform.py` which handles sRGB ↔ linear conversion and RGBA → QImage. The `ViewMode` enum (`ui/models/frame_index.py`) controls which channel (INPUT, MASK, ALPHA, FG, MATTE, COMP, PROCESSED) the viewport renders.

### SAM2 checkpoint loading

`sam2_tracker/wrapper.py` loads checkpoints from `sam2_tracker/checkpoints/` (dev) or `<user_data_dir>/sam2_tracker/checkpoints/` (frozen build). The path SSOT is `sam2_tracker/paths.py::get_sam2_cache_dir()`. There is **no automatic download** — if the checkpoint is missing a `FileNotFoundError` is raised with the expected path.

### Third-party boundaries

`gvm_core/`, `VideoMaMaInferenceModule/`, `CorridorKeyModule/`, and `modules/MatAnyone2Module/` are upstream research code. Do not apply ruff or refactor inside these directories — keep them close to their upstream sources.

### Model weights

Checkpoints are not in the repo. Most tests use random tensors and don't need weights. Tests requiring a GPU or real weights are marked `@pytest.mark.gpu`.
