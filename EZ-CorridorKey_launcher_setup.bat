@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title EZ-CorridorKey 워크스테이션 설치

REM 관리자 권한 확인
net session >nul 2>&1
if errorlevel 1 (
    echo [INFO] 관리자 권한이 필요합니다. UAC 창을 확인해주세요...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\" \"%USERPROFILE%\"' -Verb RunAs"
    exit /b
)

set "ORIG_USERPROFILE=%~1"
if "%ORIG_USERPROFILE%"=="" set "ORIG_USERPROFILE=%USERPROFILE%"

set "PYTHON_DIR=C:\Programs\Python311"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PYTHON_INSTALLER=\\192.168.10.200\vol05\inhouse\python\python-3.11.9-amd64.exe"
set "VENV_DIR=C:\venvs\EZ-CorridorKey"
set "VENV_SOURCE=\\192.168.10.200\vol05\inhouse\nuke_plugin\EZ-CorridorKey\EZ-CorridorKey\.venv"
set "LAUNCHER=\\192.168.10.200\vol05\inhouse\flova\flova\exec\EZ-CorridorKey_launcher.bat"
set "SHORTCUT=%ORIG_USERPROFILE%\Desktop\EZ-CorridorKey.lnk"

echo.
echo ══════════════════════════════════════════════════════════════════
echo   EZ-CorridorKey 워크스테이션 설치
echo ══════════════════════════════════════════════════════════════════
echo.
echo   Python     : %PYTHON_DIR%
echo   가상환경   : %VENV_DIR%
echo   venv 원본  : %VENV_SOURCE%
echo   런처       : %LAUNCHER%
echo   바로가기   : %SHORTCUT%
echo.

echo ────────────────────────────────────────────────────────────────
echo [CHECK] \\192.168.10.200\vol05\ 네트워크 드라이브 접근 확인
echo ────────────────────────────────────────────────────────────────
dir \\192.168.10.200\vol05\ >nul 2>&1
if errorlevel 1 goto :error
echo [OK] \\192.168.10.200\vol05\ 드라이브 접근 확인 완료.
echo.

echo ────────────────────────────────────────────────────────────────
echo [1/4] Python 3.11 설치 확인
echo ────────────────────────────────────────────────────────────────

if exist "%PYTHON_EXE%" (
    echo [OK] 이미 설치되어 있습니다: %PYTHON_EXE%
) else (
    echo [INFO] Python 설치 중...
    "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_launcher=0 PrependPath=0
    if errorlevel 1 goto :error
)
echo.

echo ────────────────────────────────────────────────────────────────
echo [2/4] 가상환경 생성 및 파일 복사
echo ────────────────────────────────────────────────────────────────

if not exist C:\venvs mkdir C:\venvs

if exist "%VENV_DIR%" (
    echo [INFO] 기존 가상환경 삭제 중...
    rmdir /s /q "%VENV_DIR%"
)

echo [INFO] 가상환경 생성 중...
"%PYTHON_EXE%" -m venv "%VENV_DIR%"
if errorlevel 1 goto :error
echo [OK] 가상환경 생성 완료.

if not exist "%VENV_SOURCE%" goto :error

echo [INFO] 파일 복사 중...
robocopy "%VENV_SOURCE%" "%VENV_DIR%" /E /XO /XN /NP
if errorlevel 8 goto :error

echo [OK] 가상환경 파일 복사 완료.
echo.

echo ────────────────────────────────────────────────────────────────
echo [3/4] Windows Defender 예외 폴더 등록
echo ────────────────────────────────────────────────────────────────
powershell -Command "Add-MpPreference -ExclusionPath '%VENV_DIR%'"
if errorlevel 1 goto :error
echo [OK] Defender 예외 등록 완료.
echo.

echo ────────────────────────────────────────────────────────────────
echo [4/4] 바탕화면 바로가기 생성
echo ────────────────────────────────────────────────────────────────

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%LAUNCHER%'; $s.WorkingDirectory = '\\192.168.10.200\vol05\inhouse\flova\flova\exec'; $s.Save()"
if errorlevel 1 goto :error

echo [OK] 설치 완료
pause
exit /b 0

:error
echo.
echo ══════════════════════════════════════════════════════════════════
echo   설치 중 오류가 발생했습니다.
echo ══════════════════════════════════════════════════════════════════
pause
exit /b 1