# -*- coding: utf-8 -*-
"""分类 / 对象缩略图: 选择本地图片或使用剪贴板图片, 保存到 resources/thumbnail/<用户名>

缩略图按名称匹配 (见 module.image.ImageTkThumbnailGroup), 分类与对象共用同一套名称:
    加载 resources/thumbnail/<用户名> 目录 (含子目录) 下的图片, 文件名 (去掉后缀) 即名称
    层级越浅越优先
    查找时先精确匹配名称, 再按 "头像匹配算法" 近似匹配
因此缩略图直接保存为该目录根层的 <名称>.png, 可覆盖子目录中的同名图片

旧的用户级缩略图目录 home/<用户名>/thumbnail 不再读取, 登录时由 migrate_legacy 将其中的图片移动过来
"""

# std
import io
import os
import shutil
import threading
import tkinter.filedialog

# install
import PIL.Image

# project
import core
from window import dpi

from module.image import ImageTkThumbnailGroup, THUMBNAIL_SUFFIXES
from .add_preview import get_clipboard_image


# 文件名中不允许出现的字符
ILLEGAL_CHARS = '\\/:*?"<>|'

# 保存时图片最长边的上限 (只缩小不放大), 避免大图拖慢缩略图加载
MAX_SIZE = 256

# 建议的图片尺寸
RECOMMEND_SIZE = 128

_migrate_lock = threading.Lock()


# ================================================================== 文件读写
def _directory() -> str | None:
    """当前用户的缩略图目录, 未登录时返回 None"""
    if core.userenv.user_name is Ellipsis: return None
    path = core.userenv.file.thumbnail
    return path if isinstance(path, str) else None


def check_name(name: str) -> str | None:
    """名称能否直接作为缩略图文件名, 不能时返回原因"""
    if not name: return '名称不能为空'
    if any(x in ILLEGAL_CHARS or ord(x) < 32 for x in name):
        return f'名称包含文件名不允许的字符 ( {" ".join(ILLEGAL_CHARS)} )'
    if name != name.strip() or name.endswith('.'):
        return '名称首尾不能是空格, 且不能以 "." 结尾'
    return None


def _images(directory: str, name: str) -> list[str]:
    """目录 (不含子目录) 下以 name 命名的图片文件名

    Windows 文件名不区分大小写, 因此按忽略大小写比较
    """
    try: filenames = os.listdir(directory)
    except FileNotFoundError: return []

    result = []
    for filename in filenames:
        stem, suffix = os.path.splitext(filename)
        if stem.lower() != name.lower() or suffix.lower() not in THUMBNAIL_SUFFIXES: continue
        if os.path.isfile(os.path.join(directory, filename)): result.append(filename)

    return result


def save_thumbnail(name: str, image: PIL.Image.Image) -> None:
    """将图片保存为 resources/thumbnail/<用户名>/<名称>.png, 并清理根层其他格式的同名图片"""
    directory = _directory()
    if directory is None: raise RuntimeError('尚未登录用户')

    errormsg = check_name(name)
    if errormsg is not None: raise ValueError(errormsg)

    image = image.convert('RGBA')
    image.thumbnail((MAX_SIZE, MAX_SIZE), PIL.Image.LANCZOS)

    os.makedirs(directory, exist_ok=True)
    target = os.path.join(directory, f'{name}.png')
    temp = f'{target}.tmp'

    # 新图片完整写入并就位后再清理其他格式的旧图片, 避免保存失败时丢失原有图片
    try:
        image.save(temp, format='PNG')
        os.replace(temp, target)

    except Exception:
        try: os.remove(temp)
        except OSError: ...
        raise

    for filename in _images(directory, name):
        if filename.lower() == f'{name}.png'.lower(): continue
        os.remove(os.path.join(directory, filename))


def copy_thumbnail(old: str, new: str) -> None:
    """分类重命名时, 将旧名称的缩略图复制给新名称 (新名称已有缩略图时不处理)

    分类与对象共用名称, 旧名称的缩略图可能仍被同名对象使用, 因此复制而不移动
    """
    directory = _directory()
    if directory is None or not os.path.isdir(directory) or check_name(new) is not None: return

    try:
        images = ImageTkThumbnailGroup.scan_dirs(directory)
        if old not in images or new in images: return

        with PIL.Image.open(images[old]) as fileimage: image = fileimage.copy()
        save_thumbnail(new, image)

    except Exception as e:
        core.log.error(f"复制缩略图 \"{old}\" -> \"{new}\" 失败 {e.__class__}: {e}")
        return

    core.basic_event.reload_thumbnail()


# ================================================================== 旧目录迁移
def _is_link(path: str) -> bool:
    """是否为符号链接 / 目录联接 (junction)"""
    parent = os.path.realpath(os.path.dirname(os.path.abspath(path)))
    expected = os.path.join(parent, os.path.basename(path))
    return os.path.normcase(os.path.realpath(path)) != os.path.normcase(expected)


def migrate_legacy(source: str, target: str) -> tuple[int, list[str], list[str]]:
    """将 source (含子目录) 中的图片按原有目录结构移动到 target

    - 只移动图片, 其他文件与隐藏目录保持不变; 不处理链接目录
    - target 的同一子目录中已有同名图片 (忽略后缀与大小写) 时不移动, 不会覆盖任何文件
    - 移动后变空的目录会被删除
    返回 (移动数量, 因同名未移动的相对路径, 移动失败的相对路径)
    """
    with _migrate_lock:
        if not os.path.isdir(source) or _is_link(source): return 0, [], []

        # 移动前先完成扫描与冲突判断, 使 source 内的同名不同格式图片不会互相视为冲突
        tasks, conflicts, failed = [], [], []
        for dirpath, dirnames, filenames in os.walk(source):
            dirnames[:] = sorted(x for x in dirnames if not x.startswith('.') and not _is_link(os.path.join(dirpath, x)))
            relative = os.path.relpath(dirpath, source)

            for filename in sorted(filenames):
                stem, suffix = os.path.splitext(filename)
                if not stem or suffix.lower() not in THUMBNAIL_SUFFIXES: continue

                item = os.path.normpath(os.path.join(relative, filename))
                if _images(os.path.join(target, relative), stem): conflicts.append(item)
                else: tasks.append(item)

        moved = 0
        for item in tasks:
            from_, to = os.path.join(source, item), os.path.join(target, item)
            try:
                os.makedirs(os.path.dirname(to), exist_ok=True)
                if os.path.lexists(to): raise FileExistsError(f'{to} 已存在')
                shutil.move(from_, to)
                moved += 1

            except Exception as e:
                core.log.error(f"移动缩略图 {from_} -> {to} 失败 {e.__class__}: {e}")
                failed.append(item)
                continue

            # os.rmdir 只能删除空目录
            dirpath = os.path.dirname(from_)
            while True:
                try: os.rmdir(dirpath)
                except OSError: break
                if os.path.normcase(dirpath) == os.path.normcase(source): break
                dirpath = os.path.dirname(dirpath)

        return moved, conflicts, failed


# ================================================================== 交互
def _set_status(text: str) -> None:
    try: core.window.status.set_status(text)
    except Exception: ...


def _check_ready(name: str) -> bool:
    """能否为 name 设置缩略图, 不能时给予提示"""
    if not name: return False
    if _directory() is None:
        core.window.messagebox.showinfo(title='未登录', message='请先登录用户')
        return False

    errormsg = check_name(name)
    if errormsg is not None:
        core.window.messagebox.showerror(title='无法设置缩略图', message=f'"{name}"\n{errormsg}\n\n缩略图以名称作为文件名, 请先修改名称。')
        return False

    return True


def select_thumbnail(name: str) -> None:
    """选择本地图片设为 name 的缩略图"""
    if not _check_ready(name): return

    patterns = ' '.join(f'*{x}' for x in THUMBNAIL_SUFFIXES)
    filepath = tkinter.filedialog.askopenfilename(
        title=f'选择 "{name}" 的缩略图（建议使用 {RECOMMEND_SIZE}×{RECOMMEND_SIZE} 及以上的正方形图片）',
        filetypes=[('图片', patterns), ('所有文件', '*')],
        parent=core.window.mainwindow)

    if not filepath: return
    _apply_thumbnail(name, filepath)


def paste_thumbnail(name: str) -> None:
    """将剪贴板中的图片 (截图或复制的图片文件) 设为 name 的缩略图"""
    if not _check_ready(name): return

    clipboard = get_clipboard_image()
    if clipboard is None:
        core.window.messagebox.showinfo(
            title='剪贴板中没有图片',
            message='请先复制一张图片 (截图或图片文件)\n再使用剪贴板图片设置缩略图')
        return

    _apply_thumbnail(name, io.BytesIO(clipboard[0]))


def _apply_thumbnail(name: str, source: str | io.BytesIO) -> None:
    """读取图片并设为 name 的缩略图, 需要时提示图片尺寸与覆盖"""
    try:
        with PIL.Image.open(source) as fileimage: image = fileimage.copy()

    except Exception as e:
        core.window.messagebox.showerror(title='图片读取失败', message=f'无法读取该图片\n{e}')
        return

    size = dpi.thumbnail_size()
    width, height = image.size

    tips = []
    if width != height:
        tips.append('图片不是正方形，将按比例缩放并在两侧留出透明边')
    if max(width, height) < size:
        tips.append('图片小于列表显示尺寸，显示时会被放大而变得模糊')
    if max(width, height) > MAX_SIZE:
        tips.append(f'图片较大，保存时将等比缩小至最长边 {MAX_SIZE} 像素')

    exists = _images(_directory(), name)

    if tips or exists:
        message = f'图片尺寸：{width}×{height}\n列表显示尺寸：{size}×{size}\n建议尺寸：{RECOMMEND_SIZE}×{RECOMMEND_SIZE} 及以上的正方形图片'
        if tips: message += '\n\n' + '\n'.join(f'● {x}' for x in tips)
        if exists: message += f'\n\n"{name}" 已有缩略图 {"、".join(exists)}，将被覆盖。'
        message += '\n\n是否继续？'
        if not core.window.messagebox.askyesno(title='设置缩略图', message=message): return

    try:
        save_thumbnail(name, image)

    except Exception as e:
        core.window.messagebox.showerror(title='操作失败', message=f'缩略图设置失败\n{e}')
        return

    core.basic_event.reload_thumbnail()
    _set_status(f"已设置 \"{name}\" 的缩略图")


def add_to_menu(menu, name: str | None) -> None:
    """为分类 / 对象右键菜单追加设置缩略图的菜单项, name 为右键所在行的名称"""
    if not name: return
    menu.add_separator()
    menu.add_command(label='设置缩略图…', command=lambda: select_thumbnail(name))
    menu.add_command(label='使用剪贴板图片设置缩略图', command=lambda: paste_thumbnail(name))
