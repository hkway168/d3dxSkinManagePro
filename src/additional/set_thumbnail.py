# -*- coding: utf-8 -*-
"""分类 / 对象缩略图: 选择本地图片, 保存到用户级缩略图目录 home/<用户名>/thumbnail

缩略图按名称匹配 (见 module.image.ImageTkThumbnailGroup), 分类与对象共用同一套名称:
    加载 resources/thumbnail 与 home/<用户名>/thumbnail 目录 (含子目录) 下的图片, 文件名 (去掉后缀) 即名称
    同一目录中层级越浅越优先, 用户目录整体优先于 resources/thumbnail
    查找时先精确匹配名称, 再按 "头像匹配算法" 近似匹配
因此缩略图直接保存为用户目录根层的 <名称>.png, 可覆盖子目录与 resources/thumbnail 中的同名图片
"""

# std
import os
import tkinter.filedialog

# install
import PIL.Image

# project
import core
from window import dpi

from module.image import THUMBNAIL_SUFFIXES


# 文件名中不允许出现的字符
ILLEGAL_CHARS = '\\/:*?"<>|'

# 保存时图片最长边的上限 (只缩小不放大), 避免大图拖慢缩略图加载
MAX_SIZE = 256

# 建议的图片尺寸
RECOMMEND_SIZE = 128


# ================================================================== 文件读写
def _directory() -> str | None:
    """用户级缩略图目录, 未登录时返回 None"""
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


def has_thumbnail(name: str) -> bool:
    """用户级缩略图目录中是否已有 name 的缩略图"""
    directory = _directory()
    if directory is None or not name: return False
    return any(os.path.splitext(x)[0] == name for x in _images(directory, name))


def save_thumbnail(name: str, image: PIL.Image.Image) -> None:
    """将图片保存为 home/<用户名>/thumbnail/<名称>.png, 并清理其他格式的同名图片"""
    directory = _directory()
    if directory is None: raise RuntimeError('尚未登录用户')

    errormsg = check_name(name)
    if errormsg is not None: raise ValueError(errormsg)

    image = image.convert('RGBA')
    image.thumbnail((MAX_SIZE, MAX_SIZE), PIL.Image.LANCZOS)

    os.makedirs(directory, exist_ok=True)
    for filename in _images(directory, name):
        os.remove(os.path.join(directory, filename))

    image.save(os.path.join(directory, f'{name}.png'), format='PNG')


def copy_thumbnail(old: str, new: str) -> None:
    """分类重命名时, 将旧名称的缩略图复制给新名称 (新名称已有缩略图时不处理)

    分类与对象共用名称, 旧名称的缩略图可能仍被同名对象使用, 因此复制而不移动
    """
    directory = _directory()
    if directory is None or has_thumbnail(new) or check_name(new) is not None: return

    sources = [x for x in _images(directory, old) if os.path.splitext(x)[0] == old]
    if not sources: return

    try:
        with PIL.Image.open(os.path.join(directory, sources[0])) as fileimage: image = fileimage.copy()
        save_thumbnail(new, image)

    except Exception as e:
        core.log.error(f"复制缩略图 \"{old}\" -> \"{new}\" 失败 {e.__class__}: {e}")
        return

    core.basic_event.reload_thumbnail()


# ================================================================== 交互
def _set_status(text: str) -> None:
    try: core.window.status.set_status(text)
    except Exception: ...


def select_thumbnail(name: str) -> None:
    """选择本地图片设为 name 的缩略图, 并提示图片尺寸"""
    if not name: return
    if _directory() is None:
        core.window.messagebox.showinfo(title='未登录', message='请先登录用户')
        return

    errormsg = check_name(name)
    if errormsg is not None:
        core.window.messagebox.showerror(title='无法设置缩略图', message=f'"{name}"\n{errormsg}\n\n缩略图以名称作为文件名, 请先修改名称。')
        return

    patterns = ' '.join(f'*{x}' for x in THUMBNAIL_SUFFIXES)
    filepath = tkinter.filedialog.askopenfilename(
        title=f'选择 "{name}" 的缩略图（建议使用 {RECOMMEND_SIZE}×{RECOMMEND_SIZE} 及以上的正方形图片）',
        filetypes=[('图片', patterns), ('所有文件', '*')],
        parent=core.window.mainwindow)

    if not filepath: return

    try:
        with PIL.Image.open(filepath) as fileimage: image = fileimage.copy()

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

    exists = has_thumbnail(name)

    if tips or exists:
        message = f'图片尺寸：{width}×{height}\n列表显示尺寸：{size}×{size}\n建议尺寸：{RECOMMEND_SIZE}×{RECOMMEND_SIZE} 及以上的正方形图片'
        if tips: message += '\n\n' + '\n'.join(f'● {x}' for x in tips)
        if exists: message += f'\n\n"{name}" 已有自定义缩略图，将被覆盖。'
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
    """为分类 / 对象右键菜单追加 "设置缩略图" 菜单项, name 为右键所在行的名称"""
    if not name: return
    menu.add_separator()
    menu.add_command(label='设置缩略图…', command=lambda: select_thumbnail(name))
