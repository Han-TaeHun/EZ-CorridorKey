@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title EZ-CorridorKey 워크스테이션 설치

set LOG_FILE=%~dp0install_log.txt
echo ===== INSTALL START ===== > "%LOG_FILE%"

REM ══════════════════════════════════════════════════════════════════
REM 관리자 권한 확인 및 자동 승격
REM ══════════════════════════════════════════════════════════════════
net session >nul 2>&1
if errorlevel 1 (
    echo [INFO] 관리자 권한이 필요합니다. >> "%LOG_FILE%"
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\" \"%USERPROFILE%\"' -Verb RunAs"
    exit /b
)

set "ORIG_USERPROFILE=%~1"
if "%ORIG_USERPROFILE%"=="" set "ORIG_USERPROFILE=%USERPROFILE%"

REM ── 경로 정의 ───────────────────────────────────────────────────
set "PYTHON_DIR=C:\Programs\Python311"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PYTHON_INSTALLER=W:\inhouse\python\python-3.11.9-amd64.exe"
set "VENV_DIR=C:\venvs\EZ-CorridorKey"
set "VENV_SOURCE=W:\inhouse\nuke_plugin\EZ-CorridorKey\EZ-CorridorKey\.venv"
set "LAUNCHER=W:\inhouse\flova\flova\exec\EZ-CorridorKey_launcher.bat"
set "SHORTCUT=%ORIG_USERPROFILE%\Desktop\EZ-CorridorKey.lnk"

echo.
echo ===== 환경 정보 =====
echo Python: %PYTHON_DIR%
echo Venv  : %VENV_DIR%
echo.

REM ══════════════════════════════════════════════════════════════════
REM [0] 네트워크 드라이브 확인
REM ══════════════════════════════════════════════════════════════════
echo [CHECK] W 드라이브 접근 확인...
dir W:\ >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 관리자 권한에서 W: 드라이브 접근 불가 >> "%LOG_FILE%"
    echo 관리자 CMD에서는 네트워크 드라이브가 보이지 않을 수 있습니다.
    pause
    goto :error
)

REM ══════════════════════════════════════════════════════════════════
REM [1/4] Python 설치 확인
REM ══════════════════════════════════════════════════════════════════
echo [1/4] Python 확인...

if exist "%PYTHON_EXE%" (
    echo [OK] Python 이미 존재
) else (
    echo [INFO] Python 설치 시작...
    if not exist "%PYTHON_INSTALLER%" (
        echo [ERROR] 설치 파일 없음 >> "%LOG_FILE%"
        goto :error
    )

    "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_launcher=0 PrependPath=0 >> "%LOG_FILE%" 2>&1

    if errorlevel 1 (
        echo [ERROR] Python 설치 실패 >> "%LOG_FILE%"
        goto :error
    )
)

echo.

REM ══════════════════════════════════════════════════════════════════
REM [2/4] 가상환경 생성
REM ══════════════════════════════════════════════════════════════════
echo [2/4] 가상환경 생성...

if not exist C:\venvs mkdir C:\venvs

if exist "%VENV_DIR%" (
    echo [INFO] 기존 venv 삭제...
    rmdir /s /q "%VENV_DIR%"
)

echo [INFO] venv 생성 실행...
"%PYTHON_EXE%" -m venv "%VENV_DIR%" >> "%LOG_FILE%" 2>&1

echo [DEBUG] errorlevel: %errorlevel%
if errorlevel 1 (
    echo [ERROR] venv 생성 실패 >> "%LOG_FILE%"
    pause
    goto :error
)

echo [OK] venv 생성 완료
echo.

REM ══════════════════════════════════════════════════════════════════
REM [2-1] venv 파일 복사
REM ══════════════════════════════════════════════════════════════════
echo [INFO] venv 파일 복사...

if not exist "%VENV_SOURCE%" (
    echo [ERROR] 원본 venv 없음 >> "%LOG_FILE%"
    goto :error
)

robocopy "%VENV_SOURCE%" "%VENV_DIR%" /E /XO /XN /NP >> "%LOG_FILE%"
set ROBO_ERR=%errorlevel%

if %ROBO_ERR% geq 8 (
    echo [ERROR] robocopy 실패 (%ROBO_ERR%) >> "%LOG_FILE%"
    goto :error
)

echo [OK] 파일 복사 완료
echo.

REM ══════════════════════════════════════════════════════════════════
REM [3/4] Defender 예외 등록
REM ══════════════════════════════════════════════════════════════════
echo [3/4] Defender 예외 등록...

powershell -Command "Add-MpPreference -ExclusionPath '%VENV_DIR%'" >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo [ERROR] Defender 예외 실패 >> "%LOG_FILE%"
    goto :error
)

echo [OK] Defender 설정 완료
echo.

REM ══════════════════════════════════════════════════════════════════
REM [4/4] 바로가기 생성
REM ══════════════════════════════════════════════════════════════════
echo [4/4] 바로가기 생성...

powershell -Command ^
"$ws = New-Object -ComObject WScript.Shell; ^
$s = $ws.CreateShortcut('%SHORTCUT%'); ^
$s.TargetPath = '%LAUNCHER%'; ^
$s.WorkingDirectory = 'W:\inhouse\flova\flova\exec'; ^
$s.Save()" >> "%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo [ERROR] 바로가기 생성 실패 >> "%LOG_FILE%"
    goto :error
)

echo [OK] 설치 완료
pause
exit /b 0

REM ══════════════════════════════════════════════════════════════════
REM 에러 처리
REM ══════════════════════════════════════════════════════════════════
:error
echo.
echo ===== ERROR 발생 =====
echo 로그 파일 확인: %LOG_FILE%
pause
exit /b 1
