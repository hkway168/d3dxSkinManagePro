# -*- coding: utf-8 -*-
"""窗口图标 (Windows)

Tk 的 wm iconbitmap 从 ICO 中挑选帧时按固定的 16 / 32 像素匹配,
而程序启用了 DPI 感知, 高缩放比下标题栏需要 24 / 40 等尺寸,
Tk 交出的小帧会被系统拉伸, 图标因此发虚。

这里改用 Win32 的 LoadImage 按当前 DPI 实际需要的像素尺寸取帧,
再通过 WM_SETICON 分别设置标题栏 (小) 与 Alt+Tab / 任务栏 (大) 图标。
"""

import ctypes
import sys


WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010

SM_CXICON, SM_CYICON = 11, 12
SM_CXSMICON, SM_CYSMICON = 49, 50

GA_ROOT = 2

# 已加载的 HICON 缓存, 按 (路径, 宽, 高) 复用
# 图标句柄需在窗口存续期间保持有效, 缓存同时避免重复调用造成句柄泄漏
_cache: dict[tuple[str, int, int], int] = {}


def _user32():
    """
    独立加载 user32, 并声明句柄相关的参数 / 返回值类型。

    ctypes 默认按 int 处理返回值, 64 位下会截断句柄;
    这里不使用 ctypes.windll 缓存的实例, 避免影响其它模块的调用约定。
    """
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetAncestor.restype = ctypes.c_void_p

    user32.LoadImageW.argtypes = [
        ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint,
        ctypes.c_int, ctypes.c_int, ctypes.c_uint,
    ]
    user32.LoadImageW.restype = ctypes.c_void_p

    user32.SendMessageW.argtypes = [
        ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
    ]
    user32.SendMessageW.restype = ctypes.c_void_p

    return user32


def _icon_sizes(user32, hwnd: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """返回 ((小图标宽, 高), (大图标宽, 高)), 优先取窗口所在显示器的 DPI"""
    try:
        dpi = user32.GetDpiForWindow(hwnd)
        if dpi:
            metric = user32.GetSystemMetricsForDpi
            return (
                (metric(SM_CXSMICON, dpi), metric(SM_CYSMICON, dpi)),
                (metric(SM_CXICON, dpi), metric(SM_CYICON, dpi)),
            )

    except Exception:
        # GetDpiForWindow / GetSystemMetricsForDpi 需要 Windows 10 1607 以上
        ...

    metric = user32.GetSystemMetrics
    return (
        (metric(SM_CXSMICON), metric(SM_CYSMICON)),
        (metric(SM_CXICON), metric(SM_CYICON)),
    )


def _load(user32, path: str, width: int, height: int) -> int:
    key = (path, width, height)
    if key not in _cache:
        _cache[key] = user32.LoadImageW(None, path, IMAGE_ICON, width, height, LR_LOADFROMFILE)

    return _cache[key]


def apply(window, path: str) -> bool:
    """
    为 window 设置标题栏与任务栏图标, 成功返回 True。

    非 Windows 平台或接口不可用时返回 False, 由调用方回退到 wm iconbitmap。
    """
    if sys.platform != "win32":
        return False

    try:
        user32 = _user32()
        window.update_idletasks()
        hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT)
        if not hwnd:
            return False

        small, big = _icon_sizes(user32, hwnd)
        handles = (
            (ICON_SMALL, _load(user32, path, *small)),
            (ICON_BIG, _load(user32, path, *big)),
        )
        if not all(handle for _, handle in handles):
            return False

        for which, handle in handles:
            user32.SendMessageW(hwnd, WM_SETICON, which, handle)

        return True

    except Exception:
        return False
