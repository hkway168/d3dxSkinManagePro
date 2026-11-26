# -*- coding: utf-8 -*-

import tkinter

import core

from .add_preview import apply_preview, get_clipboard_image, has_preview


class FullScreenPreview (object):
    """全屏显示预览图, 单击或按 Esc 关闭"""
    def __init__(self, tkimg):
        self.tkimg = tkimg

        self.windows = tkinter.Toplevel(core.window.mainwindow)
        self.windows.configure(background='black', cursor='hand2')
        self.windows.attributes('-fullscreen', True)
        self.windows.attributes('-topmost', True)

        self.label_image = tkinter.Label(self.windows, image=self.tkimg, background='black', borderwidth=0)
        self.label_image.pack(side='top', fill='both', expand=True)

        for widget in (self.windows, self.label_image):
            widget.bind('<Button-1>', self.close)
            widget.bind('<Button-3>', self.close)

        self.windows.bind('<Escape>', self.close)
        self.windows.focus_force()


    def close(self, *args):
        self.windows.destroy()


def show_full_screen_preview(SHA: str) -> bool:
    """全屏显示 Mod 的预览图, 返回是否成功显示"""
    width = core.window.mainwindow.winfo_screenwidth()
    height = core.window.mainwindow.winfo_screenheight()

    try:
        tkimg = core.module.image.get_preview_image(SHA, width, height)
    except Exception as e:
        core.window.messagebox.showerror(title='预览失败', message=f'无法读取预览图\n{e}')
        return True

    if tkimg is None: return False

    FullScreenPreview(tkimg)
    return True


def get_current_sha() -> str | None:
    """获取预览区域当前对应的 Mod SHA, 未选中时返回 None"""
    SHA = str(core.window.interface.mods_manage.label_SHA['text'])

    if not SHA or SHA == 'SHA' or core.module.mods_index.get_item(SHA) is None:
        return None

    return SHA


PREVIEW_HINT = '左键单击 查看全屏预览图\n右键单击 从剪切板拉取图片\n\n或将图片文件拖拽至窗口添加'


def bin_preview_click(*args):
    """左键预览区域: 有预览图时全屏预览"""
    SHA = get_current_sha()
    if SHA is None: return
    if has_preview(SHA): show_full_screen_preview(SHA)


def _is_preview_empty() -> bool:
    """当前选中了 Mod 且预览区域没有显示图片"""
    if get_current_sha() is None: return False
    return not str(core.window.interface.mods_manage.label_preview['image'])


def bin_preview_hint_update(*args):
    """鼠标在预览区域时: 无预览图则显示提示, 否则隐藏"""
    annotation = core.window.annotation_toplevel

    if not _is_preview_empty():
        annotation.withdraw()
        return

    annotation.update_content(PREVIEW_HINT)
    annotation.deiconify()
    annotation.update_position()


def bin_preview_hint_leave(*args):
    core.window.annotation_toplevel.withdraw()


def bin_preview_right_click(*args):
    """右键预览区域: 将剪贴板中的图片设为预览图"""
    SHA = get_current_sha()
    if SHA is None: return

    clipboard = get_clipboard_image()
    if clipboard is None:
        core.window.messagebox.showinfo(
            title='剪贴板中没有图片',
            message='请先复制一张图片 (截图或图片文件)\n再右键预览区域将其设为预览图')
        return

    content, suffix = clipboard
    apply_preview(SHA, content, suffix)
