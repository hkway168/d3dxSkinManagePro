# -*- coding: utf-8 -*-
"""Mod 选择列表的排序规则

排序只作用于界面显示, 不改变 module.mods_manage 中的默认顺序 (分级 -> 名称)。
设置按用户保存在 home/<用户名>/choices_sort.json:
    key          主排序键
    reverse      是否倒序
    pinned_first 置顶的 Mod 排在最前
    loaded_first 正在使用的 Mod 排在最前
    cached_first 存在解压缓存的 Mod 排在最前
    pinned       置顶的 SHA 列表
    recent       最近使用记录 dict :: SHA : 时间戳
"""

# std
import os
import json
import time
import threading

# project
import core
from constant import *


KEY_DEFAULT = "default"
KEY_NAME = "name"
KEY_MTIME = "mtime"
KEY_SIZE = "size"
KEY_RECENT = "recent"

FLAG_PINNED_FIRST = "pinned_first"
FLAG_LOADED_FIRST = "loaded_first"
FLAG_CACHED_FIRST = "cached_first"

# 最近使用记录的上限, 超出时丢弃最早的记录
RECENT_LIMIT = 500

# 置顶 Mod 在列表中的名称前缀
PIN_MARK = "★ "

DEFAULT_SETTINGS = {
    "key": KEY_DEFAULT,
    "reverse": False,
    FLAG_PINNED_FIRST: True,
    FLAG_LOADED_FIRST: False,
    FLAG_CACHED_FIRST: False,
    "pinned": [],
    "recent": {},
}


_lock = threading.RLock()
_settings: dict | None = None
_settings_user = None


# -------------------------------------------------- 排序键
# 每个排序键的 "正序" 都是最符合直觉的方向, 例如添加时间为 新 -> 旧

def _text(value) -> str:
    return str(value or "").casefold()


def _stat(SHA: str) -> tuple[float, int]:
    try:
        st = os.stat(os.path.join(core.env.directory.resources.mods, SHA))
        return st.st_mtime, st.st_size

    except Exception:
        return 0.0, 0


def _key_default(SHA, item, recent):
    return (str(item.get(K.INDEX.GRADING, "")), str(item.get(K.INDEX.NAME, "")))


def _key_name(SHA, item, recent):
    return _text(item.get(K.INDEX.NAME))


def _key_mtime(SHA, item, recent):
    return -_stat(SHA)[0]


def _key_size(SHA, item, recent):
    return -_stat(SHA)[1]


def _key_recent(SHA, item, recent):
    # 从未使用过的为 0, 排在最后
    return -recent.get(SHA, 0)


# (键, 菜单显示名称, 排序函数)
SORT_KEYS = (
    (KEY_DEFAULT, "默认 (分级 → 名称)", _key_default),
    (KEY_NAME, "名称 (A → Z)", _key_name),
    (KEY_MTIME, "添加时间 (新 → 旧)", _key_mtime),
    (KEY_SIZE, "文件大小 (大 → 小)", _key_size),
    (KEY_RECENT, "最近使用 (近 → 远)", _key_recent),
)

_KEY_FUNCS = {key: func for key, _, func in SORT_KEYS}


def _key_available(key: str) -> bool:
    return key in _KEY_FUNCS


# -------------------------------------------------- 设置读写

def _path() -> str | None:
    try: path = core.userenv.file.choices_sort
    except Exception: return None
    return path if isinstance(path, str) else None


def _normalize(data) -> dict:
    settings = {k: (v.copy() if isinstance(v, (list, dict)) else v) for k, v in DEFAULT_SETTINGS.items()}
    if not isinstance(data, dict): return settings

    key = data.get("key")
    if isinstance(key, str) and key in _KEY_FUNCS: settings["key"] = key

    for name in ("reverse", FLAG_PINNED_FIRST, FLAG_LOADED_FIRST, FLAG_CACHED_FIRST):
        if isinstance(data.get(name), bool): settings[name] = data[name]

    pinned = data.get("pinned")
    if isinstance(pinned, list):
        settings["pinned"] = [x for x in pinned if isinstance(x, str)]

    recent = data.get("recent")
    if isinstance(recent, dict):
        settings["recent"] = {
            k: float(v) for k, v in recent.items()
            if isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)
        }

    return settings


def _get() -> dict:
    """获取当前用户的排序设置 (切换用户后自动重新读取)"""
    global _settings, _settings_user

    with _lock:
        user = core.userenv.user_name
        if _settings is not None and _settings_user == user: return _settings

        data = None
        path = _path()
        if path is not None and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as file_object:
                    data = json.load(file_object)

            except Exception as e:
                core.log.warn(f"读取选择列表排序设置失败 {e.__class__} {e}", L.WINDOS_MODS_MANAGE)

        _settings = _normalize(data)
        _settings_user = user
        return _settings


def _save() -> None:
    path = _path()
    if path is None: return

    with _lock:
        settings = _get()
        try:
            with open(path, "w", encoding="utf-8") as file_object:
                json.dump(settings, file_object, ensure_ascii=False, indent=4)

        except Exception as e:
            core.log.error(f"保存选择列表排序设置失败 {e.__class__} {e}", L.WINDOS_MODS_MANAGE)


def _refresh_view() -> None:
    try: core.window.interface.mods_manage.update_choices_list()
    except Exception as e: core.log.error(f"刷新选择列表失败 {e.__class__} {e}", L.WINDOS_MODS_MANAGE)


# -------------------------------------------------- 设置接口

def set_key(key: str) -> None:
    if not _key_available(key): return
    with _lock: _get()["key"] = key
    _save()
    _refresh_view()


def set_reverse(reverse: bool) -> None:
    with _lock: _get()["reverse"] = bool(reverse)
    _save()
    _refresh_view()


def toggle_flag(name: str) -> None:
    if name not in (FLAG_PINNED_FIRST, FLAG_LOADED_FIRST, FLAG_CACHED_FIRST): return
    with _lock:
        settings = _get()
        settings[name] = not settings[name]
    _save()
    _refresh_view()


def reset() -> None:
    """恢复默认排序 (保留置顶与最近使用记录)"""
    with _lock:
        settings = _get()
        for name in ("key", "reverse", FLAG_PINNED_FIRST, FLAG_LOADED_FIRST, FLAG_CACHED_FIRST):
            settings[name] = DEFAULT_SETTINGS[name]
    _save()
    _refresh_view()


def is_pinned(SHA: str) -> bool:
    with _lock: return SHA in _get()["pinned"]


def set_pinned(SHAs: list[str], pinned: bool) -> None:
    with _lock:
        lst = _get()["pinned"]
        for SHA in SHAs:
            if pinned and SHA not in lst: lst.append(SHA)
            if not pinned and SHA in lst: lst.remove(SHA)
    _save()
    _refresh_view()


def record_recent(SHA: str) -> None:
    """记录 Mod 的使用时间 (由用户手动加载 Mod 时调用)"""
    if not isinstance(SHA, str) or not SHA: return
    with _lock:
        recent = _get()["recent"]
        recent[SHA] = time.time()
        if len(recent) > RECENT_LIMIT:
            for old in sorted(recent, key=recent.get)[:len(recent) - RECENT_LIMIT]:
                del recent[old]
    _save()


def migrate_sha(old_SHA: str, new_SHA: str) -> None:
    """Mod 的 SHA 发生变化时, 将置顶与最近使用记录迁移到新 SHA"""
    changed = False
    with _lock:
        settings = _get()
        pinned = settings["pinned"]
        if old_SHA in pinned:
            pinned[pinned.index(old_SHA)] = new_SHA
            changed = True

        recent = settings["recent"]
        if old_SHA in recent:
            recent[new_SHA] = recent.pop(old_SHA)
            changed = True

    if changed: _save()


# -------------------------------------------------- 排序

def sort_sha_list(SHAs: list[str]) -> list[str]:
    """按当前排序设置返回排序后的新列表"""
    with _lock:
        settings = _get()
        key = settings["key"] if _key_available(settings["key"]) else KEY_DEFAULT
        reverse = settings["reverse"]
        pinned = set(settings["pinned"])
        recent = dict(settings["recent"])
        flags = {name: settings[name] for name in (FLAG_PINNED_FIRST, FLAG_LOADED_FIRST, FLAG_CACHED_FIRST)}

    func = _KEY_FUNCS[key]

    def main_key(SHA):
        item = core.module.mods_index.get_item(SHA)
        if not isinstance(item, dict): item = {}
        # 主键相同时依次按名称、SHA 排序, 保证每次刷新顺序稳定
        return (func(SHA, item, recent), _text(item.get(K.INDEX.NAME)), SHA)

    result = sorted(SHAs, key=main_key, reverse=reverse)

    # 优先显示规则不受倒序影响; 稳定排序保证组内维持主排序结果
    priority = []
    if flags[FLAG_PINNED_FIRST]: priority.append(lambda SHA: SHA not in pinned)
    if flags[FLAG_LOADED_FIRST]: priority.append(lambda SHA: not core.module.mods_manage.is_loaded_sha(SHA))
    if flags[FLAG_CACHED_FIRST]: priority.append(lambda SHA: not core.module.mods_manage.is_cached_sha(SHA))

    if priority:
        result.sort(key=lambda SHA: tuple(f(SHA) for f in priority))

    return result


def display_prefix(SHA: str) -> str:
    """列表中显示在名称前的标记"""
    return PIN_MARK if is_pinned(SHA) else ""


# -------------------------------------------------- 右键菜单

def _radio(on: bool) -> str:
    return "● " if on else "○ "


def _check(on: bool) -> str:
    return "■ " if on else "□ "


def add_to_menu(menu, SHAs: list[str] | None = None, separator: bool = True) -> None:
    """向 PopupMenu 追加排序菜单项; SHAs 为右键选中的 Mod, 用于置顶操作"""
    with _lock:
        settings = _get()
        key = settings["key"]
        reverse = settings["reverse"]
        flags = {name: settings[name] for name in (FLAG_PINNED_FIRST, FLAG_LOADED_FIRST, FLAG_CACHED_FIRST)}
        pinned = set(settings["pinned"])

    if separator: menu.add_separator()

    menu.add_cascade('排序方式', [
        *((f"{_radio(k == key)}{label}", lambda k=k: set_key(k), _key_available(k))
          for k, label, _ in SORT_KEYS),
        (None, None, False),
        (f"{_radio(not reverse)}正序", lambda: set_reverse(False)),
        (f"{_radio(reverse)}倒序", lambda: set_reverse(True)),
    ])

    menu.add_cascade('优先显示', [
        (f"{_check(flags[FLAG_PINNED_FIRST])}置顶的 Mod", lambda: toggle_flag(FLAG_PINNED_FIRST)),
        (f"{_check(flags[FLAG_LOADED_FIRST])}正在使用的 Mod", lambda: toggle_flag(FLAG_LOADED_FIRST)),
        (f"{_check(flags[FLAG_CACHED_FIRST])}有解压缓存的 Mod", lambda: toggle_flag(FLAG_CACHED_FIRST)),
        (None, None, False),
        ("恢复默认排序", reset),
    ])

    if SHAs:
        SHAs = list(SHAs)
        all_pinned = all(SHA in pinned for SHA in SHAs)
        suffix = f" ({len(SHAs)} 个)" if len(SHAs) > 1 else ""
        if all_pinned:
            menu.add_command(label=f'取消置顶{suffix}', command=lambda: set_pinned(SHAs, False))
        else:
            menu.add_command(label=f'置顶{suffix}', command=lambda: set_pinned(SHAs, True))


__all__ = [
    "sort_sha_list", "display_prefix", "add_to_menu",
    "set_key", "set_reverse", "toggle_flag", "reset",
    "is_pinned", "set_pinned", "record_recent", "migrate_sha",
]
