@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title EZ-CorridorKey 워크스테이션 설치

REM ══════════════════════════════════════════════════════════════════
REM  관리자 권한 확인 및 자동 승격
REM ══════════════════════════════════════════════════════════════════
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] 관리자 권한이 필요합니다. UAC 창을 확인해주세요...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\" \"%USERPROFILE%\"' -Verb RunAs -Wait"
    exit /b
)

REM 승격된 인스턴스: 첫 번째 인수로 원본 사용자 프로파일 경로를 받음
set "ORIG_USERPROFILE=%~1"
if "%ORIG_USERPROFILE%"=="" set "ORIG_USERPROFILE=%USERPROFILE%"

REM ── 경로 변수 정의 ────────────────────────────────────────────────
set "PYTHON_DIR=C:\Programs\Python311"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PYTHON_INSTALLER=W:\inhouse\python\python-3.11.9-amd64.exe"
set "VENV_DIR=C:\venvs\EZ-CorridorKey"
set "VENV_SOURCE=W:\inhouse\nuke_plugin\EZ-CorridorKey\EZ-CorridorKey\.venv"
set "LAUNCHER=W:\inhouse\flova\flova\exec\EZ-CorridorKey_launcher.bat"
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

REM ══════════════════════════════════════════════════════════════════
REM  [1/4] Python 3.11 설치 확인
REM ══════════════════════════════════════════════════════════════════
echo ────────────────────────────────────────────────────────────────
echo [1/4] Python 3.11 설치 확인
echo ────────────────────────────────────────────────────────────────

if exist "%PYTHON_EXE%" goto :python_already_installed

echo [INFO] Python 3.11을 찾을 수 없습니다. 설치를 시작합니다...

if not exist "%PYTHON_INSTALLER%" (
    echo.
    echo [ERROR] 설치 파일을 찾을 수 없습니다:
    echo         %PYTHON_INSTALLER%
    goto :error
)

echo [INFO] 설치 파일 실행 중 (잠시 기다려 주세요)...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_launcher=0 PrependPath=0
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python 설치 실패 (errorlevel: %errorlevel%)
    goto :error
)

if not exist "%PYTHON_EXE%" (
    echo.
    echo [ERROR] 설치 후 python.exe를 찾을 수 없습니다: %PYTHON_EXE%
    goto :error
)
echo [OK] Python 3.11 설치 완료.
goto :python_done

:python_already_installed
echo [OK] 이미 설치되어 있습니다: %PYTHON_EXE%

:python_done
echo.

REM ══════════════════════════════════════════════════════════════════
REM  [2/4] 가상환경 생성 및 파일 복사
REM ══════════════════════════════════════════════════════════════════
echo ────────────────────────────────────────────────────────────────
echo [2/4] 가상환경 생성 및 파일 복사
echo ────────────────────────────────────────────────────────────────

if not exist "C:\venvs" (
    echo [INFO] C:\venvs 폴더 생성 중...
    mkdir "C:\venvs"
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] C:\venvs 폴더 생성 실패 (errorlevel: %errorlevel%)
        goto :error
    )
)

if not exist "%VENV_DIR%" goto :venv_create

echo [INFO] 기존 가상환경 삭제 중: %VENV_DIR%
rmdir /s /q "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 기존 가상환경 삭제 실패 (errorlevel: %errorlevel%)
    goto :error
)
echo [OK] 기존 가상환경 삭제 완료.

:venv_create
echo [INFO] Python 버전 확인 중...
"%PYTHON_EXE%" --version
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python 실행 실패 (errorlevel: %errorlevel%)
    goto :error
)

echo [INFO] 가상환경 생성 중: %VENV_DIR%
"%PYTHON_EXE%" -m venv "%VENV_DIR%" 2>&1
set VENV_ERR=%errorlevel%
if %VENV_ERR% neq 0 (
    echo.
    echo [ERROR] 가상환경 생성 실패 (errorlevel: %VENV_ERR%)
    echo [HINT] 위 python 오류 메시지를 확인해주세요.
    goto :error
)
echo [OK] 가상환경 생성 완료.

if not exist "%VENV_SOURCE%" (
    echo.
    echo [ERROR] 원본 가상환경 폴더를 찾을 수 없습니다:
    echo         %VENV_SOURCE%
    goto :error
)

echo [INFO] 파일 복사 중 (이미 있는 파일은 건너뜁니다)...
echo        원본: %VENV_SOURCE%
echo        대상: %VENV_DIR%
echo.

REM /E       : 하위 폴더 포함 전체 복사
REM /XO + /XN: 대상에 이미 존재하는 파일 날짜 무관하게 건너뜀
REM /NP      : 진행률 퍼센트 표시 안 함
robocopy "%VENV_SOURCE%" "%VENV_DIR%" /E /XO /XN /NP
set ROBO_ERR=%errorlevel%
if %ROBO_ERR% geq 8 (
    echo.
    echo [ERROR] 파일 복사 중 오류 발생 (errorlevel: %ROBO_ERR%)
    goto :error
)

echo.
echo [OK] 가상환경 파일 복사 완료.
echo.

REM ══════════════════════════════════════════════════════════════════
REM  [3/4] Windows Defender 예외 폴더 등록
REM ══════════════════════════════════════════════════════════════════
echo ────────────────────────────────────────────────────────────────
echo [3/4] Windows Defender 예외 폴더 등록
echo ────────────────────────────────────────────────────────────────
echo [INFO] 예외 경로: %VENV_DIR%

powershell -Command "Add-MpPreference -ExclusionPath '%VENV_DIR%'"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Defender 예외 등록 실패 (errorlevel: %errorlevel%)
    goto :error
)
echo [OK] Defender 예외 등록 완료.
echo.

REM ══════════════════════════════════════════════════════════════════
REM  [4/4] 바탕화면 바로가기 생성
REM ══════════════════════════════════════════════════════════════════
echo ────────────────────────────────────────────────────────────────
echo [4/4] 바탕화면 바로가기 생성
echo ────────────────────────────────────────────────────────────────
echo [INFO] 런처    : %LAUNCHER%
echo [INFO] 저장위치: %SHORTCUT%

if not exist "%LAUNCHER%" (
    echo [WARNING] 런처 파일이 현재 접근 불가능한 경로에 있습니다.
    echo           바로가기는 생성하지만 나중에 런처 파일 경로를 확인하세요.
)

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%LAUNCHER%'; $s.WorkingDirectory = 'W:\inhouse\flova\flova\exec'; $s.Save()"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 바로가기 생성 실패 (errorlevel: %errorlevel%)
    goto :error
)
echo [OK] 바탕화면 바로가기 생성 완료.
echo.

echo ══════════════════════════════════════════════════════════════════
echo   설치 완료! 바탕화면의 EZ-CorridorKey 바로가기로 실행하세요.
echo ══════════════════════════════════════════════════════════════════
echo.
pause
exit /b 0

REM ══════════════════════════════════════════════════════════════════
REM  공통 에러 핸들러
REM ══════════════════════════════════════════════════════════════════
:error
echo.
echo ══════════════════════════════════════════════════════════════════
echo   설치 중 오류가 발생했습니다. 위의 내용을 확인해주세요.
echo ══════════════════════════════════════════════════════════════════
echo.
pause
exit /b 1
