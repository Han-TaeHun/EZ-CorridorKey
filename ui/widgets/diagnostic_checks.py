"""Diagnostic check data — known error patterns and startup environment checks.

This module holds the ``Diagnostic`` / ``StartupIssue`` dataclasses, the
registry of known error patterns (``_DIAGNOSTICS``), and the
``run_startup_diagnostics`` routine.  The UI dialog classes that *display*
these results live in ``diagnostic_dialog.py``.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Known error patterns ─────────────────────────────────────────────

@dataclass
class Diagnostic:
    """A single known-error diagnosis with user-facing fix steps."""
    id: str
    title: str
    pattern: re.Pattern[str]
    explanation: str
    steps: list[str]
    tags: list[str] = field(default_factory=list)


_DIAGNOSTICS: list[Diagnostic] = [
    # ── GPU / CUDA ────────────────────────────────────────────────
    Diagnostic(
        id="gpu-required",
        title="GPU 필요 - CPU 전용 PyTorch 감지됨",
        pattern=re.compile(
            r"requires a CUDA GPU but only CPU is available|"
            r"float16.*cannot run with.*cpu.*device|"
            r"No GPU acceleration available",
            re.IGNORECASE,
        ),
        explanation=(
            "현재 PyTorch 설치에는 CUDA 지원이 포함되어 있지 않아 "
            "GPU 가속 파이프라인(GVM, VideoMaMa)을 실행할 수 없습니다. "
            "대개 설치 프로그램이 CPU 전용 패키지를 선택했거나, "
            "CUDA 인덱스 없이 PyTorch를 별도로 설치한 경우입니다."
        ),
        steps=[
            "EZ-CorridorKey 폴더에서 터미널을 엽니다.",
            "가상 환경을 활성화합니다:\n"
            "    .venv\\Scripts\\activate",
            "CUDA 지원 PyTorch를 다시 설치합니다:\n"
            "    pip install torch torchvision --index-url\n"
            "    https://download.pytorch.org/whl/cu128",
            "EZ-CorridorKey를 다시 시작합니다.",
            "NVIDIA GPU가 없다면 GVM과 VideoMaMa는 지원되지 않습니다.\n"
            "이 경우 수동 알파 힌트를 사용해 주세요.",
        ],
        tags=["gpu", "cuda", "cpu", "float16"],
    ),
    # ── Missing checkpoint ────────────────────────────────────────
    Diagnostic(
        id="missing-checkpoint",
        title="모델 체크포인트를 찾을 수 없음",
        pattern=re.compile(
            r"No \.pth checkpoint found|"
            r"checkpoints.*not found|"
            r"CorridorKey\.pth.*missing",
            re.IGNORECASE,
        ),
        explanation=(
            "checkpoints 폴더에 CorridorKey 모델 가중치(.pth 파일)가 없습니다. "
            "모델 파일을 별도로 내려받아야 합니다."
        ),
        steps=[
            "프로젝트 릴리스 페이지 또는 README의 링크에서\n"
            "CorridorKey.pth를 내려받습니다.",
            "파일을 다음 위치에 둡니다:\n"
            "    CorridorKeyModule/checkpoints/CorridorKey.pth",
            "EZ-CorridorKey를 다시 시작합니다.",
        ],
        tags=["checkpoint", "model", "pth"],
    ),
    # ── FFmpeg ────────────────────────────────────────────────────
    Diagnostic(
        id="ffmpeg-invalid",
        title="지원되지 않는 FFmpeg 설치",
        pattern=re.compile(
            r"FFmpeg 7\.0 or newer is required|"
            r"FFprobe 7\.0 or newer is required|"
            r"FFmpeg and FFprobe major versions do not match|"
            r"Could not determine ffmpeg version|"
            r"Could not determine ffprobe version|"
            r"CorridorKey requires a full FFmpeg build",
            re.IGNORECASE,
        ),
        explanation=(
            "CorridorKey가 FFmpeg를 찾았지만 버전이 너무 낮거나, 설치가 불완전하거나, "
            "기능이 제거된 Windows 빌드입니다. 비디오 가져오기/내보내기에는 "
            "FFmpeg 7.0 이상과 FFprobe가 필요합니다."
        ),
        steps=[
            "Edit > Preferences > Repair FFmpeg로 이동합니다.\n"
            "호환되는 FFmpeg 빌드를 자동으로 내려받습니다.",
            "그래도 해결되지 않으면:\n"
            "  Windows: 1-install.bat을 다시 실행합니다.\n"
            "  macOS: brew install ffmpeg\n"
            "  Linux: 패키지 관리자로 ffmpeg와 ffprobe(7.0 이상)를 모두 설치합니다.",
            "두 명령이 모두 동작하는지 확인합니다:\n"
            "    ffmpeg -version\n"
            "    ffprobe -version",
        ],
        tags=["ffmpeg", "ffprobe", "video", "version"],
    ),
    Diagnostic(
        id="ffmpeg-missing",
        title="FFmpeg를 찾을 수 없음",
        pattern=re.compile(
            r"FFmpeg not found|"
            r"ffmpeg.*not.*found|"
            r"ffprobe.*not.*found",
            re.IGNORECASE,
        ),
        explanation=(
            "비디오 가져오기/내보내기에 FFmpeg와 FFprobe가 필요하지만 "
            "시스템에서 찾지 못했습니다."
        ),
        steps=[
            "Edit > Preferences > Repair FFmpeg로 이동합니다.\n"
            "FFmpeg를 자동으로 내려받아 설치합니다.",
            "그래도 해결되지 않으면:\n"
            "  Windows: 1-install.bat을 다시 실행합니다.\n"
            "  macOS: brew install ffmpeg\n"
            "  Linux: 패키지 관리자로 ffmpeg를 설치합니다.",
            "EZ-CorridorKey를 다시 시작합니다.",
        ],
        tags=["ffmpeg", "video"],
    ),
    # ── Triton / torch.compile ────────────────────────────────────
    Diagnostic(
        id="triton-missing",
        title="Triton 사용 불가(torch.compile 비활성화)",
        pattern=re.compile(
            r"triton.*not.*available|"
            r"triton.*import.*failed|"
            r"ModuleNotFoundError.*triton",
            re.IGNORECASE,
        ),
        explanation=(
            "Windows에서 torch.compile 최적화를 사용하려면 Triton이 필요합니다. "
            "Triton이 없어도 추론은 동작하지만 속도가 느려집니다."
        ),
        steps=[
            "EZ-CorridorKey 폴더에서 터미널을 엽니다.",
            "가상 환경을 활성화합니다:\n"
            "    .venv\\Scripts\\activate",
            "triton-windows를 설치합니다:\n"
            "    pip install triton-windows",
            "EZ-CorridorKey를 다시 시작합니다.",
        ],
        tags=["triton", "compile"],
    ),
    Diagnostic(
        id="msvc-compiler-missing",
        title="MSVC 컴파일러를 찾을 수 없음(torch.compile 비활성화)",
        pattern=re.compile(
            r"Compiler: cl is not found|"
            r"Compiler: cl\.exe is not found",
            re.IGNORECASE,
        ),
        explanation=(
            "Windows에서 torch.compile을 사용하려면 MSVC C++ 컴파일러(cl.exe)가 필요합니다. "
            "없어도 추론은 동작하지만 더 느린 eager 모드로 실행됩니다."
        ),
        steps=[
            "다음 위치에서 Visual Studio Build Tools를 설치합니다:\n"
            "    https://visualstudio.microsoft.com/visual-cpp-build-tools/",
            '"Desktop development with C++" 워크로드를 선택합니다.',
            "컴퓨터를 재시작한 뒤 EZ-CorridorKey를 다시 시작합니다.",
            "무시해도 추론은 동작하지만 속도가 조금 느려집니다.",
        ],
        tags=["compile", "msvc"],
    ),
    # ── CPU-only PyTorch installed (wrong wheel) ─────────────────
    Diagnostic(
        id="pytorch-cpu-wheel",
        title="CPU 전용 PyTorch 설치됨(CUDA 지원 없음)",
        pattern=re.compile(
            r"torch.*\+cpu|"
            r"PyTorch.*\+cpu",
            re.IGNORECASE,
        ),
        explanation=(
            "NVIDIA GPU가 있는데도 CPU 전용 PyTorch가 설치되어 있습니다. "
            "이 상태에서는 GPU 가속 모델(CorridorKey, GVM, VideoMaMa)이 GPU를 사용할 수 없습니다. "
            "대개 CUDA 인덱스 URL 없이 PyTorch를 설치했을 때 발생합니다."
        ),
        steps=[
            "EZ-CorridorKey 폴더에서 터미널을 엽니다.",
            "가상 환경을 활성화합니다:\n"
            "    .venv\\Scripts\\activate  (or venv\\Scripts\\activate)",
            "CPU 전용 빌드를 제거합니다:\n"
            "    pip uninstall torch torchvision -y",
            "CUDA 지원 빌드로 다시 설치합니다:\n"
            "    pip install torch torchvision --index-url\n"
            "    https://download.pytorch.org/whl/cu128",
            "EZ-CorridorKey를 다시 시작합니다.",
            "팁: 1-install.bat을 다시 실행해도 자동으로 해결됩니다.",
        ],
        tags=["gpu", "cuda", "cpu", "wheel"],
    ),
    # ── six / protobuf import error (GVM) ──────────────────────
    Diagnostic(
        id="six-metapath-importer",
        title="GVM 가져오기 오류(_SixMetaPathImporter)",
        pattern=re.compile(
            r"_SixMetaPathImporter.*object has no attribute|"
            r"SixMetaPathImporter",
            re.IGNORECASE,
        ),
        explanation=(
            "GVM 파이프라인에서 protobuf/grpc가 사용하는 'six' 라이브러리 호환성 오류가 발생했습니다. "
            "보통 PyTorch가 CPU 전용(+cpu)이거나 protobuf와 다른 패키지 사이의 버전 충돌이 있을 때 발생합니다."
        ),
        steps=[
            "먼저 CPU 전용 PyTorch인지 확인합니다:\n"
            "    python -c \"import torch; print(torch.__version__)\"",
            "버전이 '+cpu'로 끝나면 CUDA 지원 빌드로 다시 설치합니다:\n"
            "    pip install torch torchvision --index-url\n"
            "    https://download.pytorch.org/whl/cu128",
            "버전에 이미 '+cu...'가 있다면 protobuf를 업데이트합니다:\n"
            "    pip install -U protobuf grpcio",
            "EZ-CorridorKey를 다시 시작합니다.",
        ],
        tags=["gvm", "six", "protobuf", "import"],
    ),
    # ── GVM weights ───────────────────────────────────────────────
    Diagnostic(
        id="gvm-weights-missing",
        title="GVM 모델 가중치를 찾을 수 없음",
        pattern=re.compile(
            r"Base model path not found.*stable-video-diffusion|"
            r"gvm_core.*weights.*not found|"
            r"GVM.*model.*not found",
            re.IGNORECASE,
        ),
        explanation=(
            "GVM(Green-screen Video Matting) 모델 가중치가 없습니다. "
            "모델 파일을 별도로 내려받아야 합니다."
        ),
        steps=[
            "GVM 가중치 다운로더를 실행합니다:\n"
            "    python -m gvm_core.download",
            "또는 README 링크에서 직접 내려받은 뒤\n"
            "gvm_core/weights/에 둡니다.",
            "EZ-CorridorKey를 다시 시작합니다.",
        ],
        tags=["gvm", "weights"],
    ),
    # ── Python version ────────────────────────────────────────────
    Diagnostic(
        id="python-version",
        title="지원되지 않는 Python 버전",
        pattern=re.compile(
            r"Python.*3\.\d+.*not.*supported|"
            r"requires.*Python.*3\.1[0-3]|"
            r"python_requires",
            re.IGNORECASE,
        ),
        explanation=(
            "EZ-CorridorKey는 Python 3.10-3.13이 필요합니다. "
            "현재 Python 버전은 호환되지 않습니다."
        ),
        steps=[
            "https://python.org에서 Python 3.11을 내려받습니다.",
            "설치 중 'Add Python to PATH'를 체크합니다.",
            "기존 .venv 폴더를 삭제합니다.",
            "1-install.bat을 다시 실행해 새 환경을 만듭니다.",
        ],
        tags=["python", "version"],
    ),
    # ── Pascal GPU on cu130 wheel (1.9.1 → 1.9.2 upgrade path) ───
    Diagnostic(
        id="pascal-cu130-mismatch",
        title="이전 세대 NVIDIA GPU 감지됨 - 재설치 필요",
        # Pattern is unused at runtime — this diagnostic is only fired
        # by run_startup_diagnostics, not by error-text matching. The
        # regex is intentionally a no-match so a stray error message
        # can never trigger it accidentally.
        pattern=re.compile(r"(?!.*)", re.DOTALL),
        explanation=(
            "현재 NVIDIA GPU는 Pascal 세대(GeForce GTX 10 시리즈, Titan X/Xp 또는 이전 Quadro)입니다. "
            "앱에 설치된 PyTorch 빌드에는 이 GPU에 필요한 커널이 없어 AI 키잉 추론 중 CUDA 오류가 발생합니다. "
            "EZ-CorridorKey 1.9.2에는 이 GPU를 지원하는 새 PyTorch 빌드가 포함되어 있지만, "
            "앱 내부 업데이트는 대용량 런타임 파일을 교체하지 않습니다. "
            "한 번은 전체 설치 프로그램을 내려받아 업그레이드해야 합니다."
        ),
        steps=[
            "최신 설치 프로그램을 내려받습니다:\n"
            "    https://github.com/edenaion/EZ-CorridorKey/releases/latest",
            "기존 설치 위에 설치 프로그램을 실행합니다.\n"
            "프로젝트, 설정, 모델 가중치는 유지됩니다.",
            "재설치 후에는 Help > Check for Updates로\n"
            "이후 업데이트를 정상적으로 받을 수 있습니다.",
            "재설치하지 않으면 이 버전에서 해당 GPU를 사용할 수 없어\n"
            "AI 키잉이 동작하지 않습니다.",
        ],
        tags=["pascal", "gpu", "cuda", "upgrade"],
    ),
    # ── CUDA out of memory ────────────────────────────────────────
    Diagnostic(
        id="cuda-oom",
        title="GPU 메모리 부족(VRAM)",
        pattern=re.compile(
            r"CUDA out of memory|"
            r"OutOfMemoryError|"
            r"torch\.cuda\.OutOfMemoryError",
            re.IGNORECASE,
        ),
        explanation=(
            "처리 중 GPU VRAM이 부족해졌습니다. 고해상도 클립을 처리하거나 "
            "다른 앱이 GPU 메모리를 사용 중일 때 발생할 수 있습니다."
        ),
        steps=[
            "GPU 사용량이 큰 다른 앱(게임, 다른 AI 도구,\n"
            "브라우저 하드웨어 가속 등)을 닫습니다.",
            "먼저 더 낮은 해상도로 처리해 봅니다.",
            "저VRAM 모드 환경 변수를 설정합니다:\n"
            "    set CORRIDORKEY_OPT_MODE=lowvram",
            "문제가 계속되면 이 클립 해상도에 필요한 VRAM이\n"
            "현재 GPU에 부족할 수 있습니다.",
        ],
        tags=["vram", "memory", "oom"],
    ),
]


def match_diagnostic(error_msg: str) -> Diagnostic | None:
    """Return the first matching Diagnostic for *error_msg*, or ``None``."""
    for diag in _DIAGNOSTICS:
        if diag.pattern.search(error_msg):
            return diag
    return None


# ── Startup diagnostics ──────────────────────────────────────────────

@dataclass
class StartupIssue:
    """A non-fatal issue detected during application startup."""
    diagnostic: Diagnostic
    detail: str  # extra context (e.g. detected PyTorch version)


def _pascal_cu130_mismatch() -> tuple[bool, str]:
    """Detect a Pascal GPU paired with a cu13x torch wheel.

    Returns ``(is_mismatch, detail_string)``. ``is_mismatch`` is True
    when *all* of the following are true:

      * torch can be imported,
      * torch was built against CUDA 13.x (i.e. ``torch.version.cuda``
        starts with "13."),
      * an NVIDIA GPU is present and reachable,
      * the device's compute capability is below (7, 0) — i.e. Pascal
        (sm_60 / sm_61) or older.

    Every step is wrapped in try/except so a broken or missing torch
    can never crash startup. The function is the safety guard for the
    1.9.1 → 1.9.2 in-app upgrade path: existing Pascal users keep
    their cu130 wheel after a code-only update and would otherwise
    silently crash the next time they run inference.
    """
    try:
        import torch
    except Exception:
        return False, ""

    try:
        cuda_str = (torch.version.cuda or "").strip()
    except Exception:
        return False, ""
    if not cuda_str.startswith("13."):
        return False, ""

    try:
        if not torch.cuda.is_available():
            return False, ""
    except Exception:
        return False, ""

    try:
        device_count = torch.cuda.device_count()
    except Exception:
        return False, ""
    if device_count <= 0:
        return False, ""

    # Inspect device 0 — if a user has multiple GPUs and one is Pascal
    # and another isn't, we still want to flag it because inference
    # picks device 0 by default.
    try:
        cap = torch.cuda.get_device_capability(0)
        name = torch.cuda.get_device_name(0)
    except Exception:
        return False, ""

    if not isinstance(cap, tuple) or len(cap) != 2:
        return False, ""

    if cap >= (7, 0):
        # Turing or newer — fully supported by cu130 wheels.
        return False, ""

    detail = (
        f"{name}(compute capability {cap[0]}.{cap[1]})와 "
        f"PyTorch CUDA {cuda_str} 조합이 감지되었습니다. "
        f"cu13x 패키지에는 sm_{cap[0]}{cap[1]} 커널이 포함되어 있지 않습니다."
    )
    return True, detail


def run_startup_diagnostics(device: str) -> list[StartupIssue]:
    """Check the runtime environment and return any issues found.

    Called once after ``detect_device()`` during MainWindow init.
    """
    issues: list[StartupIssue] = []

    # 1. CPU-only device
    if device == "cpu":
        diag = next((d for d in _DIAGNOSTICS if d.id == "gpu-required"), None)
        if diag:
            detail = _get_torch_detail()
            issues.append(StartupIssue(diag, detail))

    # 1b. GPU present but PyTorch is CPU-only wheel (+cpu)
    if device == "cpu":
        try:
            import torch
            if "+cpu" in torch.__version__:
                has_nvidia = False
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    has_nvidia = pynvml.nvmlDeviceGetCount() > 0
                    pynvml.nvmlShutdown()
                except Exception:
                    pass
                if has_nvidia:
                    diag = next(
                        (d for d in _DIAGNOSTICS if d.id == "pytorch-cpu-wheel"),
                        None,
                    )
                    if diag:
                        issues.append(StartupIssue(
                            diag,
                            f"NVIDIA GPU가 감지되었지만 PyTorch {torch.__version__}은 CPU 전용입니다.",
                        ))
        except ImportError:
            pass

    # 2. Python version outside supported range
    import sys
    vi = sys.version_info
    if vi.major != 3 or vi.minor < 10 or vi.minor > 13:
        diag = next((d for d in _DIAGNOSTICS if d.id == "python-version"), None)
        if diag:
            issues.append(StartupIssue(
                diag,
                f"감지된 Python 버전: {vi.major}.{vi.minor}.{vi.micro}",
            ))

    # 2b. Pascal GPU detected with a cu13x torch wheel — the 1.9.1 →
    # 1.9.2 upgrade path leaves existing cu130 runtimes in place, so a
    # GTX 10-series user who clicks "Check for Updates" will still
    # crash later when inference runs. Catch them at startup with a
    # clear "download the full installer" advisory rather than letting
    # them hit "no kernel image is available" mid-job.
    #
    # The detection helper is fully defensive — wrapped in try/except
    # at every layer — but we belt-and-suspenders the call site too so
    # any unexpected failure here can't break startup for any user.
    try:
        is_mismatch, mismatch_detail = _pascal_cu130_mismatch()
        if is_mismatch:
            diag = next(
                (d for d in _DIAGNOSTICS if d.id == "pascal-cu130-mismatch"),
                None,
            )
            if diag:
                issues.append(StartupIssue(diag, mismatch_detail))
    except Exception as exc:
        logger.warning("Pascal/cu130 startup check failed: %s", exc)

    # 3. FFmpeg missing, too old, or invalid build
    try:
        from backend.ffmpeg_tools import validate_ffmpeg_install
        result = validate_ffmpeg_install()
        if not result.ok:
            # Pick the right diagnostic based on whether FFmpeg was found at all
            diag_id = "ffmpeg-missing"
            if result.ffmpeg_path:
                diag_id = "ffmpeg-invalid"
            diag = next((d for d in _DIAGNOSTICS if d.id == diag_id), None)
            if diag:
                issues.append(StartupIssue(diag, result.message))
    except Exception as exc:
        logger.warning("FFmpeg startup check failed: %s", exc)

    return issues


def _get_torch_detail() -> str:
    """Build a one-line detail string about the PyTorch install."""
    try:
        import torch
        ver = torch.__version__
        cuda = torch.version.cuda or "none"
        return f"PyTorch {ver}, CUDA toolkit: {cuda}"
    except ImportError:
        return "PyTorch가 설치되어 있지 않습니다."


# ── Context-aware diagnostic step resolution ────────────────────────
#
# The static ``Diagnostic.steps`` lists were written for developers
# running from a git clone with a venv. That guidance is actively wrong
# for users on the Windows / macOS installer (they have no ``.venv`` to
# activate) and for users without an NVIDIA GPU (no amount of pip-
# installing a different torch wheel will help). This resolver returns
# the right steps for the current runtime instead of always echoing the
# dev-mode defaults.


def _runtime_context() -> dict:
    """Snapshot the bits of runtime state that affect diagnostic advice."""
    import sys

    ctx = {
        "is_frozen": bool(getattr(sys, "frozen", False)),
        "platform": sys.platform,
        "has_nvidia": False,
    }
    # NVIDIA GPU presence check — intentionally uses pynvml (driver-level)
    # rather than torch.cuda.is_available() because we may be handling a
    # broken torch install where cuda.is_available() returns False for
    # reasons unrelated to the actual hardware.
    try:
        import pynvml
        pynvml.nvmlInit()
        ctx["has_nvidia"] = pynvml.nvmlDeviceGetCount() > 0
        pynvml.nvmlShutdown()
    except Exception:
        pass
    return ctx


def _steps_no_nvidia_gpu() -> list[str]:
    """Shared step block for any torch/CUDA issue when no NVIDIA card is
    present. Stops the user from chasing pip reinstalls that cannot
    possibly help them."""
    return [
        "EZ-CorridorKey는 NVIDIA GPU가 필요합니다.\n"
        "키잉 모델에는 CPU 대체 실행 경로가 없습니다.",
        "컴퓨터에 NVIDIA 그래픽 카드가 있는지 확인합니다\n"
        "(GeForce RTX, GTX, Quadro 등).",
        "최신 NVIDIA 드라이버를 설치합니다:\n"
        "    https://www.nvidia.com/Download/index.aspx",
        "터미널을 열고 다음 명령을 실행합니다:\n"
        "    nvidia-smi\n"
        "이 명령을 찾을 수 없다면 드라이버가 설치되어 있지 않은 것입니다.",
        "NVIDIA GPU가 없다면 이 컴퓨터에서는 EZ-CorridorKey의\n"
        "AI 파이프라인을 실행할 수 없습니다.",
    ]


def _steps_frozen_reinstall(reason: str) -> list[str]:
    """Shared step block for installer-build users: reinstalling the
    official build is the correct remedy, not pip."""
    return [
        f"{reason}",
        "최신 설치 프로그램을 내려받습니다:\n"
        "    https://github.com/edenaion/EZ-CorridorKey/releases/latest",
        "기존 설치 위에 설치 프로그램을 실행합니다.\n"
        "프로젝트와 설정은 유지됩니다.",
        "재설치 후에도 문제가 계속되면 GitHub 이슈 보고를 눌러\n"
        "조사에 필요한 정보를 보내 주세요.",
    ]


def _resolve_gpu_required(ctx: dict, base: list[str]) -> list[str]:
    if not ctx["has_nvidia"]:
        return _steps_no_nvidia_gpu()
    if ctx["is_frozen"]:
        return _steps_frozen_reinstall(
            "설치 프로그램 빌드에서 CUDA를 감지하지 못했지만 NVIDIA GPU는 있습니다.\n"
            "대개 번들 PyTorch가 손상되었거나 NVIDIA 드라이버가 너무 오래된 경우입니다."
        )
    return base  # dev mode + NVIDIA → original venv instructions


def _resolve_pytorch_cpu_wheel(ctx: dict, base: list[str]) -> list[str]:
    if not ctx["has_nvidia"]:
        return _steps_no_nvidia_gpu()
    if ctx["is_frozen"]:
        return _steps_frozen_reinstall(
            "설치 프로그램 빌드에서 CPU 전용 PyTorch 패키지가 감지되었습니다.\n"
            "정식 릴리스에서는 발생하면 안 되는 상태입니다."
        )
    return base


def _resolve_triton_missing(ctx: dict, base: list[str]) -> list[str]:
    if ctx["is_frozen"]:
        # Triton is optional (torch.compile speedup); in a frozen build
        # this is a build-time packaging miss, not something the user
        # can fix themselves. Downgrade the instructions to "safe to
        # ignore" + Report Issue.
        return [
            "이 경고는 무시해도 됩니다. 추론은 계속 동작하지만\n"
            "조금 느린 eager 모드로 실행됩니다.",
            "설치 프로그램 빌드에서 이 경고가 보이면 GitHub 이슈 보고를 눌러\n"
            "패키지 문제를 조사할 수 있게 해 주세요.",
        ]
    return base  # dev mode → original venv instructions


def _resolve_six_metapath(ctx: dict, base: list[str]) -> list[str]:
    if not ctx["has_nvidia"]:
        return _steps_no_nvidia_gpu()
    if ctx["is_frozen"]:
        return _steps_frozen_reinstall(
            "frozen 빌드 내부에서 protobuf/grpc 호환성 오류가 발생했습니다.\n"
            "정식 릴리스에서는 발생하면 안 되는 상태입니다."
        )
    return base


def _resolve_missing_checkpoint(ctx: dict, base: list[str]) -> list[str]:
    if ctx["is_frozen"]:
        return [
            "모델 가중치는 첫 실행 설정 마법사에서 내려받습니다.\n"
            "마법사를 닫았다면 앱을 다시 열고 안내에 따라\n"
            "CorridorKey.pth(~383 MB)를 내려받아 주세요.",
            "마법사가 나타나지 않으면 다음 메뉴로 이동합니다:\n"
            "    Edit > Preferences > Re-run Setup Wizard",
            "다운로드가 실패하면 시스템 정보와 함께\n"
            "GitHub 이슈 보고를 눌러 주세요.",
        ]
    return base


# Maps diagnostic id → resolver function. Entries are optional: if a
# diagnostic has no resolver we fall through to ``Diagnostic.steps``.
_STEP_RESOLVERS = {
    "gpu-required": _resolve_gpu_required,
    "pytorch-cpu-wheel": _resolve_pytorch_cpu_wheel,
    "triton-missing": _resolve_triton_missing,
    "six-metapath-importer": _resolve_six_metapath,
    "missing-checkpoint": _resolve_missing_checkpoint,
}


def resolve_steps(diag: Diagnostic) -> list[str]:
    """Return the fix steps for *diag* tailored to the current runtime.

    Dialogs should call this instead of reading ``diag.steps`` directly
    so that users on the installer build never see dev-mode guidance
    like "activate the virtual environment" (which fails on frozen
    builds) and users without an NVIDIA GPU never see pip install
    commands (which cannot fix their situation).
    """
    handler = _STEP_RESOLVERS.get(diag.id)
    if handler is None:
        return diag.steps
    try:
        ctx = _runtime_context()
        resolved = handler(ctx, diag.steps)
        return resolved or diag.steps
    except Exception as exc:
        logger.warning("Diagnostic step resolver failed for %s: %s", diag.id, exc)
        return diag.steps
