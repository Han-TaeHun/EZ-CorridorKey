@echo off
TITLE EZ-CorridorKey
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run 1-install.bat first!
    pause
    exit /b 1
)

REM Add local ffmpeg to PATH if present
if exist "%~dp0tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%~dp0tools\ffmpeg\bin;%PATH%"

REM Cache torch.compile Triton kernels locally — prevents 2~5 min recompile each run
if not defined TORCHINDUCTOR_CACHE_DIR set "TORCHINDUCTOR_CACHE_DIR=%LOCALAPPDATA%\EZ-CorridorKey\torch_cache"
REM Cache Python bytecode locally — speeds up import on subsequent runs
if not defined PYTHONPYCACHEPREFIX set "PYTHONPYCACHEPREFIX=%LOCALAPPDATA%\EZ-CorridorKey\pycache"

call .venv\Scripts\activate.bat
start "" pythonw main.py %*
exit
