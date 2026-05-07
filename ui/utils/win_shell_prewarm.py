"""Windows 네이티브 파일 다이얼로그 cold-start 비용을 백그라운드에서 흡수합니다.

첫 QFileDialog 호출 시의 긴 지연은 IFileOpenDialog 경로에서 explorerframe,
thumbcache, shell namespace 확장 등이 지연 초기화되기 때문에 발생할 수 있습니다.
별도 STA 스레드에서 실제 COM 객체를 만들었다가 즉시 Release하면 사용자가 Browse를
누르는 시점에는 셸 관련 캐시가 이미 따뜻해진 상태가 됩니다.
"""
from __future__ import annotations

import logging
import sys
import threading

logger = logging.getLogger(__name__)

_COINIT_APARTMENTTHREADED = 0x2
_COINIT_DISABLE_OLE1DDE = 0x4
_CLSCTX_INPROC_SERVER = 0x1
_FOS_PICKFOLDERS = 0x20

_CLSID_FileOpenDialog = "{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}"
_IID_IFileOpenDialog = "{D57C7288-D4AD-4768-BE02-9D969532D960}"
_CLSID_FileSaveDialog = "{C0B4E2F3-BA21-4773-8DBA-335EC946EB8B}"
_IID_IFileSaveDialog = "{84BCCD23-5FDE-4CDB-AEA4-AF64B83D78AB}"

_PRELOAD_DLLS = (
    "shell32.dll",
    "shcore.dll",
    "propsys.dll",
    "explorerframe.dll",
    "thumbcache.dll",
    "windows.storage.dll",
    "wininet.dll",
    "urlmon.dll",
    "shdocvw.dll",
)

_started = False


def _worker() -> None:
    import ctypes
    from ctypes import byref, c_void_p, wintypes

    for name in _PRELOAD_DLLS:
        try:
            ctypes.WinDLL(name)
        except OSError:
            pass

    ole32 = ctypes.WinDLL("ole32", use_last_error=True)

    CLSIDFromString = ole32.CLSIDFromString
    CLSIDFromString.argtypes = [wintypes.LPCWSTR, c_void_p]
    CLSIDFromString.restype = ctypes.HRESULT

    CoInitializeEx = ole32.CoInitializeEx
    CoInitializeEx.argtypes = [c_void_p, wintypes.DWORD]
    CoInitializeEx.restype = ctypes.HRESULT

    CoCreateInstance = ole32.CoCreateInstance
    CoCreateInstance.argtypes = [
        c_void_p,
        c_void_p,
        wintypes.DWORD,
        c_void_p,
        c_void_p,
    ]
    CoCreateInstance.restype = ctypes.HRESULT

    CoUninitialize = ole32.CoUninitialize

    GUID = ctypes.c_byte * 16

    def _guid(value: str):
        guid = GUID()
        hr = CLSIDFromString(value, byref(guid))
        if hr < 0:
            raise OSError(f"CLSIDFromString failed: 0x{hr & 0xFFFFFFFF:08X}")
        return guid

    hr = CoInitializeEx(None, _COINIT_APARTMENTTHREADED | _COINIT_DISABLE_OLE1DDE)
    if hr < 0:
        logger.debug("shell prewarm: CoInitializeEx failed hr=0x%08X", hr & 0xFFFFFFFF)
        return

    try:
        for clsid_value, iid_value, warm_folder_picker in (
            (_CLSID_FileOpenDialog, _IID_IFileOpenDialog, True),
            (_CLSID_FileSaveDialog, _IID_IFileSaveDialog, False),
        ):
            try:
                clsid = _guid(clsid_value)
                iid = _guid(iid_value)
                ppv = c_void_p()
                hr = CoCreateInstance(
                    byref(clsid),
                    None,
                    _CLSCTX_INPROC_SERVER,
                    byref(iid),
                    byref(ppv),
                )
                if hr < 0 or not ppv:
                    logger.debug(
                        "shell prewarm: CoCreateInstance(%s) failed hr=0x%08X",
                        clsid_value,
                        hr & 0xFFFFFFFF,
                    )
                    continue

                vtbl = ctypes.cast(ppv, ctypes.POINTER(ctypes.POINTER(c_void_p)))

                if warm_folder_picker:
                    try:
                        set_options_fp = vtbl[0][9]
                        SetOptions = ctypes.WINFUNCTYPE(
                            ctypes.HRESULT,
                            c_void_p,
                            wintypes.DWORD,
                        )(set_options_fp)
                        SetOptions(ppv, _FOS_PICKFOLDERS)
                    except OSError:
                        pass

                release_fp = vtbl[0][2]
                Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(release_fp)
                Release(ppv)
            except Exception as exc:  # noqa: BLE001 - 워밍은 best-effort입니다.
                logger.debug("shell prewarm: %s warm failed: %s", clsid_value, exc)
        logger.debug("shell prewarm: done")
    finally:
        CoUninitialize()


def prewarm_file_dialog_async() -> None:
    """프로세스당 최대 1회, 백그라운드 daemon 스레드에서 워밍을 시작합니다."""
    global _started
    if _started or sys.platform != "win32":
        return
    _started = True
    threading.Thread(target=_worker, name="ShellPrewarm", daemon=True).start()
