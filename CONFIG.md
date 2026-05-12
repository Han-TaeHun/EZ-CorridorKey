# EZ-CorridorKey 환경 설정 가이드

이 문서는 앱이 어디에 데이터를 저장하고, 어떤 설정 키와 환경 변수를 인식하는지를 한 곳에 정리한다. 일상적인 사용 흐름은 `USED.md`를 본다.

---

## 1. 한눈에 보는 경로 구조

EZ-CorridorKey는 **두 개의 루트**를 분리해서 쓴다. 하나는 사용자 데이터(프로젝트/로그/설정), 다른 하나는 모델 체크포인트다. 실행 모드에 따라 둘이 같을 수도 있고 다를 수도 있다.

### 사용자 데이터 루트 (`get_user_data_root()`)

| 실행 모드                                    | 경로                              |
| -------------------------------------------- | --------------------------------- |
| Dev (`python main.py`)                       | `~/EZ_corridorkey`                |
| Frozen 빌드 (설치형)                         | `~/EZ_corridorkey`                |
| Portable 빌드 (exe 옆 `portable.txt` 존재)   | exe 디렉터리                      |

여기에는 다음이 들어간다.

```
~/EZ_corridorkey/
  Projects/                                  # 모든 프로젝트
  logs/backend/                              # 세션별 로그
  EZSCAPE/EZ-CorridorKey.ini                 # QSettings INI
  .corridorkey_session.json                  # (각 프로젝트 폴더에도)
```

> **참고**: 체크포인트는 이 경로 아래에 들어가지 **않는다**. 아래의 "체크포인트 루트"를 본다.

### 체크포인트 루트 (`backend.model_paths.get_checkpoints_root()`)

모든 모델 가중치는 단일 루트 `<체크포인트 루트>/checkpoints/` 아래에 모인다.

| 실행 모드          | 경로                                    |
| ------------------ | --------------------------------------- |
| Dev                | `<repo root>/checkpoints/`              |
| Frozen 빌드        | `<get_data_dir()>/checkpoints/`         |
| Portable 빌드      | `<exe 디렉터리>/checkpoints/`           |

`get_data_dir()`는 frozen 빌드에서 다음 순서로 결정된다.

1. `portable.txt`가 exe 옆에 있으면 exe 디렉터리
2. QSettings의 `app/install_path` (Setup Wizard에서 사용자가 지정한 설치 경로)
3. fallback — macOS는 `~/Library/Application Support/EZ-CorridorKey`, 그 외는 exe 디렉터리

### 체크포인트 하위 폴더

| 모델            | 폴더                                        |
| --------------- | ------------------------------------------- |
| CorridorKey     | `checkpoints/corridorkey/*.pth`             |
| CorridorKey MLX | `checkpoints/corridorkey/*.safetensors`     |
| SAM2            | `checkpoints/sam2/sam2.1_hiera_*.pt`        |
| BiRefNet        | `checkpoints/birefnet/<variant>/*.safetensors` |
| GVM             | `checkpoints/gvm/unet/diffusion_pytorch_model.safetensors` |
| VideoMaMa       | `checkpoints/videomama/VideoMaMa/...` + `checkpoints/videomama/stable-video-diffusion-img2vid-xt/...` |
| MatAnyone2      | `checkpoints/matanyone2/matanyone2.pth`     |
| ResNet18        | `checkpoints/resnet18/resnet18-5c106cde.pth` |
| ResNet50        | `checkpoints/resnet50/resnet50-19c8e357.pth` |

SAM2 캐시 경로의 SSOT는 `sam2_tracker/paths.py::get_sam2_cache_dir()`이고, 다른 모델 경로의 SSOT는 `backend/model_paths.py`다.

---

## 2. 실행 모드 결정 흐름

```
sys.frozen?
  ├─ False  →  Dev 모드: repo root를 데이터/체크포인트 루트로 사용
  └─ True   →  Frozen 모드
       └─ exe 옆에 portable.txt?
            ├─ Yes  →  Portable 모드: exe 디렉터리 = 데이터 루트 = 체크포인트 루트
            └─ No   →  Installed 모드
                 └─ QSettings("app/install_path") 가 유효한 디렉터리?
                      ├─ Yes  →  그 경로를 체크포인트 루트로
                      └─ No   →  macOS: ~/Library/Application Support/EZ-CorridorKey
                                  Win/Linux: exe 디렉터리
```

**Portable 빌드를 만드는 방법**: 빌드 결과 폴더의 exe 옆에 빈 `portable.txt` 파일을 두면 된다. 그 순간 모든 데이터가 exe 디렉터리 아래로 모인다(USB 스틱용).

---

## 3. QSettings INI 위치

- **포맷**: `QSettings.Format.IniFormat` (레지스트리/plist 대신 INI 파일)
- **경로**: `<get_user_data_root()>/EZSCAPE/EZ-CorridorKey.ini`
- **조직/앱 이름**: `setOrganizationName("EZSCAPE")`, `setApplicationName("EZ-CorridorKey")`

### 레지스트리 → INI 일회성 마이그레이션

INI 포맷으로 전환한 뒤 첫 실행 시, Windows의 기존 레지스트리 키를 자동으로 INI로 복사한다. 다음 두 위치를 모두 검사한다.

- `HKCU\Software\EZSCAPE\EZ-CorridorKey` (이전 native 포맷)
- `HKCU\Software\Corridor Digital\CorridorKey` (그보다 더 이전의 upstream 키)

마이그레이션 후 INI에 `_migrated_from_reg = true`가 기록되어 다시 실행하지 않는다. macOS/Linux에서는 native 포맷이 plist라 무시한다.

---

## 4. QSettings 키 목록

`ui/widgets/preferences_dialog.py`와 다른 모듈에서 사용하는 키들이다. 기본값은 코드 기준이다.

### 앱 / 설치

| 키                       | 기본        | 의미                                                          |
| ------------------------ | ----------- | ------------------------------------------------------------- |
| `app/install_path`       | (없음)      | Setup Wizard에서 선택한 설치 경로 (frozen 빌드의 데이터 루트) |
| `app/version_last_seen`  | (없음)      | Setup Wizard가 마지막으로 본 앱 버전 (업그레이드 감지용)      |
| `_migrated_from_reg`     | false       | 레지스트리→INI 마이그레이션 완료 플래그                       |
| `_migrated_from_legacy`  | false       | Corridor Digital/CorridorKey 키 마이그레이션 완료 플래그      |

### UI

| 키                  | 기본          | 의미                                |
| ------------------- | ------------- | ----------------------------------- |
| `ui/show_tooltips`  | `true`        | 컨트롤 툴팁 표시                    |
| `ui/sounds_enabled` | `true`        | UI 사운드 켜기                      |
| `ui/sounds_volume`  | `1.0`         | UI 사운드 볼륨 (0.0–1.0)            |

### 프로젝트 / 미디어

| 키                                | 기본    | 의미                                                  |
| --------------------------------- | ------- | ----------------------------------------------------- |
| `project/copy_source_videos`      | `true`  | 가져온 비디오를 프로젝트 폴더로 복사                  |
| `project/copy_image_sequences`    | `false` | 가져온 이미지 시퀀스를 프로젝트 폴더로 복사           |

### 재생

| 키               | 기본    | 의미                          |
| ---------------- | ------- | ----------------------------- |
| `playback/loop`  | `true`  | In/Out 범위 내 반복 재생      |

### 추론

| 키                          | 기본       | 의미                                                                |
| --------------------------- | ---------- | ------------------------------------------------------------------- |
| `inference/model_resolution`| 2048 (CUDA) / 1024 (Apple Silicon) | CorridorKey 입력 해상도         |
| `inference/backend`         | `auto`     | macOS 백엔드 선택 — `auto` / `torch` / `mlx`                        |
| `gpu/parallel_clips`        | `1`        | 병렬 추론 엔진 수 (VRAM 사용량 증가)                                |

### 출력

| 키                          | 기본     | 의미                                                          |
| --------------------------- | -------- | ------------------------------------------------------------- |
| `output/exr_compression`    | `dwab`   | EXR 압축 — `dwab` / `piz` / `zip` / `none`                    |
| `output/default_directory`  | (없음)   | 전역 기본 출력 폴더 — 비어 있으면 각 클립의 `Output/`         |

### 알파 / 추적

| 키                       | 기본                                  | 의미                                  |
| ------------------------ | ------------------------------------- | ------------------------------------- |
| `tracking/sam2_model`    | `facebook/sam2.1-hiera-base-plus`     | SAM2 추적 모델 선택                   |
| `alpha/birefnet_model`   | (코드 기본값)                         | BiRefNet 콤보박스 마지막 선택값       |

### 단축키 / 디버그

| 키                  | 의미                                                |
| ------------------- | --------------------------------------------------- |
| `shortcuts/*`       | `Edit > Hotkeys...`에서 재지정한 각 키 바인딩       |
| `debug_console/*`   | 디버그 콘솔(F12) 위치/크기/표시 상태                |

---

## 5. 환경 변수

명령행/`os.environ`에서 인식되는 환경 변수. CLI 플래그가 있으면 그쪽이 우선이다.

| 변수                              | 값                                | 의미                                                                       |
| --------------------------------- | --------------------------------- | -------------------------------------------------------------------------- |
| `CORRIDORKEY_OPT_MODE`            | `auto` / `speed` / `lowvram`      | GPU 최적화 모드. `--opt-mode` CLI 플래그가 이 변수를 덮어쓴다.             |
| `CORRIDORKEY_BACKEND`             | `auto` / `torch` / `mlx`          | CorridorKey 추론 백엔드 강제. QSettings `inference/backend`보다 우선.       |
| `CORRIDORKEY_CONTAINER_MODE`      | `0` / `1`                         | `1`이면 컨테이너 모드(노VNC 등)로 UI 일부 동작 변경                        |
| `CORRIDORKEY_SKIP_STARTUP_DIAGNOSTICS` | `0` / `1`                    | `1`이면 시작 진단을 건너뜀 (CI/스모크 테스트용)                            |
| `CORRIDORKEY_SKIP_UPDATE_CHECK`   | `0` / `1`                         | `1`이면 자동 업데이트 체크를 건너뜀                                        |
| `CORRIDORKEY_EXPECT_GPU`          | `auto` / `cuda` / `cpu` / 등      | `scripts/verify_torch_runtime.py`가 기대하는 런타임                        |
| `CORRIDORKEY_MOCK_NVIDIA_SMI_FILE`| 경로                              | (테스트) `nvidia-smi` 출력을 파일로 모킹                                   |
| `CORRIDORKEY_NVIDIA_SMI_PATH`     | 경로                              | `nvidia-smi` 실행 파일 위치 명시                                           |
| `CORRIDORKEY_MOCK_DRIVER_VERSION` | 문자열                            | (테스트) 드라이버 버전 강제                                                |
| `OPENCV_IO_ENABLE_OPENEXR`        | `1`                               | `main.py`에서 항상 `1`로 설정. cv2 import 전에 EXR 지원 활성화.            |

`CORRIDORKEY_OPT_MODE`는 `auto`이면 VRAM을 보고 자동 결정한다 — 12GB 이상이면 `speed`, 그 미만이면 `lowvram`. 8GB 카드에서 강제로 lowvram을 쓰려면 `set CORRIDORKEY_OPT_MODE=lowvram`.

---

## 6. 출력 위치 우선순위

추론 결과는 다음 우선순위로 저장된다.

1. **클립별 출력 폴더** — I/O 트레이 클립 우클릭 → `Set Output Directory...`
2. **프로젝트 출력 폴더** — `File > Set Project Output Folder...` (project.json에 저장)
3. **전역 기본 출력 폴더** — `Preferences > Output > Default output directory` (QSettings `output/default_directory`)
4. **기본값** — 각 클립의 `Output/`

비기본 출력 폴더를 쓰면 프로젝트/클립별 충돌을 막기 위해 다음 형태로 정리된다.

```
<출력폴더>/
  <ProjectName>/
    <ClipName>/
      FG/ Matte/ Comp/ Processed/
```

---

## 7. 프로젝트 온디스크 구조 (v2)

새 프로젝트는 v2 구조를 사용한다. v1(레거시)도 자동 인식한다.

```
~/EZ_corridorkey/Projects/
  <YYMMDD_HHMMSS>_<ProjectName>/
    project.json                       # v2 메타데이터, 클립 목록
    .corridorkey_session.json          # 세션 자동 저장 (60초 주기)
    clips/
      <ClipName>/
        clip.json                      # 클립별 메타데이터
        Source/                        # 원본 (복사 옵션 ON일 때만)
        Frames/ 또는 Input/            # 추출된 EXR DWAB 시퀀스
        AlphaHint/                     # 알파 힌트 PNG
        VideoMamaMaskHint/             # SAM2 추적 마스크
        Output/
          FG/ Matte/ Comp/ Processed/
        annotations.json               # 페인트 스트로크
        _EXPORTS/                      # 내보낸 비디오/시퀀스
```

세션은 60초마다 자동 저장하고, 앱을 닫을 때도 세션과 페인트 스트로크를 저장한다.

---

## 8. 로그

- 경로: `<get_user_data_root()>/logs/backend/`
- 파일명: `<YYMMDD_HHMMSS>_corridorkey.log` (앱 실행마다 새 파일)
- 콘솔: `--log-level`에 따른 레벨 (`DEBUG`/`INFO`/`WARNING`/`ERROR`, 기본 `INFO`)
- 파일: 항상 `DEBUG` 레벨, 50MB 단위 로테이션, backup 3개

---

## 9. Preferences 다이얼로그 매핑

`Edit > Preferences` (`Ctrl+,`)에서 보이는 항목과 위 QSettings 키의 대응표다.

| 패널         | 항목                              | 키                                  |
| ------------ | --------------------------------- | ----------------------------------- |
| User Interface | Show tooltips                   | `ui/show_tooltips`                  |
| User Interface | UI sounds                       | `ui/sounds_enabled`                 |
| Project      | Copy source videos                | `project/copy_source_videos`        |
| Project      | Copy imported image sequences     | `project/copy_image_sequences`      |
| Playback     | Loop within in/out range          | `playback/loop`                     |
| Tracking     | SAM2 model                        | `tracking/sam2_model`               |
| Tracking     | Open cache folder                 | `sam2_tracker/checkpoints` (열기)   |
| Inference    | Model resolution                  | `inference/model_resolution`        |
| Inference    | Apple Silicon backend             | `inference/backend`                 |
| Inference    | Parallel clips                    | `gpu/parallel_clips`                |
| Output       | EXR compression                   | `output/exr_compression`            |
| Output       | Default output directory          | `output/default_directory`          |
| Video Tools  | FFmpeg status / Repair / Open folder | (앱 동작, 키 없음)               |

---

## 10. 모델 설치 (Setup Wizard / Download Manager / CLI)

### GUI

앱 첫 실행 시 또는 `Edit > Download Manager...`에서 모델을 설치한다. 설치 위치는 위의 "체크포인트 루트"를 따른다.

설치된 모델은 `ui/widgets/setup_wizard.py::detect_installed_models()`가 디스크에서 직접 확인하기 때문에, 설치 경로를 바꿔도 즉시 반영된다. BiRefNet 콤보박스에는 디스크에 실제로 존재하는 변형만 표시된다.

### CLI

`scripts/setup_models.py`로 명령행에서 받을 수도 있다.

```bash
python scripts/setup_models.py --check          # 설치 상태 출력
python scripts/setup_models.py --corridorkey    # 필수 (383MB)
python scripts/setup_models.py --sam2           # SAM2 Base+ (324MB)
python scripts/setup_models.py --sam2 large     # SAM2 Large (898MB)
python scripts/setup_models.py --birefnet       # ~940MB
python scripts/setup_models.py --gvm            # ~6GB
python scripts/setup_models.py --videomama      # ~37GB
python scripts/setup_models.py --matanyone2     # ~141MB
python scripts/setup_models.py --resnet18       # 45MB (MatAnyone2 backbone)
python scripts/setup_models.py --resnet50       # 98MB
python scripts/setup_models.py --corridorkey-mlx # Apple Silicon (380MB)
python scripts/setup_models.py --all            # 전부
```

스크립트는 `backend.model_paths`를 단일 진입점으로 쓰므로 GUI/CLI/Frozen 어디서 실행해도 같은 폴더에 저장한다.

---

## 11. 자주 묻는 환경 설정 시나리오

### 다른 드라이브로 데이터를 옮기고 싶다 (Frozen)

Setup Wizard에서 `app/install_path`를 새 경로로 다시 지정한다. 이후 `<새 경로>/checkpoints/` 하위 폴더에 모델 가중치를 그대로 옮겨두면 된다.

### USB 스틱에 휴대용으로 들고 다니고 싶다 (Frozen)

빌드된 폴더의 exe 옆에 빈 `portable.txt`를 만든다. 그 즉시 모든 사용자 데이터와 체크포인트가 exe 디렉터리 아래로 통합된다.

### 8GB 카드에서 lowvram을 강제하고 싶다

```cmd
set CORRIDORKEY_OPT_MODE=lowvram
python main.py
```

또는 `python main.py --opt-mode lowvram`. CLI 플래그가 환경 변수를 덮어쓴다.

### Mac에서 MLX를 강제로 끄고 싶다

`Preferences > Inference > Apple Silicon backend`를 `torch`로 두거나, `set CORRIDORKEY_BACKEND=torch`로 실행한다.

### 큰 EXR 시퀀스를 복사하지 않고 참조만 하고 싶다

`Preferences > Project > Copy imported image sequences`를 끈다 (기본 OFF). 원본 위치에서 그대로 읽어들인다.
