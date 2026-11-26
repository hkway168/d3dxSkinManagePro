# -*- coding: utf-8 -*-

# std
import threading

# install
import windnd

# project
import core

# self
from . import hook_dropfiles
from . import modify_classification
from . import preview_actions
from . import modify_item_data


def safe_dropfiles(widget, func):
    """windnd 回调运行在窗口过程 (WNDPROC) 中, 在其中直接调用任何 tkinter 接口
    都会破坏 _tkinter 的线程状态并导致进程闪退 (PyEval_RestoreThread: NULL tstate)

    因此回调中只启动子线程, 由子线程通过 after 将处理函数投递回主循环执行
    """
    def _callback(items):
        items = list(items)
        threading.Thread(None, lambda: widget.after(0, func, items), 'dropfiles', daemon=True).start()

    windnd.hook_dropfiles(widget, func=_callback)


def initial():
    safe_dropfiles(core.window.frame_notebook, hook_dropfiles.hook_dropfiles)
    modify_classification.bind_context_menu(core.window.interface.mods_manage)
    core.window.interface.mods_manage.label_preview.bind('<Button-1>', preview_actions.bin_preview_click)
    core.window.interface.mods_manage.label_preview.bind('<Button-3>', preview_actions.bin_preview_right_click)
    core.window.interface.mods_manage.label_preview.bind('<Enter>', preview_actions.bin_preview_hint_update)
    core.window.interface.mods_manage.label_preview.bind('<Motion>', preview_actions.bin_preview_hint_update)
    core.window.interface.mods_manage.label_preview.bind('<Leave>', preview_actions.bin_preview_hint_leave)
    modify_item_data.bind_context_menu(core.window.interface.mods_manage.treeview_choices)



# frame_notebook.drop_target_register(tkinterdnd2.DND_FILES)
# frame_notebook.dnd_bind("<<Drop>>", lambda e: print(e))
