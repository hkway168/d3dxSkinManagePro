# -*- coding: utf-8 -*-
"""跟随 ttkbootstrap 主题的右键弹出菜单

tkinter.Menu 在 Windows 下为系统原生样式, 无法与程序主题保持一致,
因此使用无边框 Toplevel 自绘, 外观与悬浮提示 (AnnotationToplevel) 统一。
支持一级子菜单 (add_cascade), 鼠标悬停时在右侧展开。
"""

import tkinter
import ttkbootstrap

import core

from . import dpi


class PopupMenu (object):
    def __init__(self, master):
        self.master = master
        self.toplevel = None
        self.frame = None
        self.subtoplevel = None
        self.subframe = None
        self.__items = []
        self.__rows = []
        self.__subrows = []
        self.__sub_index = None

    # -------------------------------------------------- 菜单项
    def clear(self):
        self.__items = []

    def add_command(self, label: str, command=None, enabled: bool = True):
        self.__items.append((label, command, enabled, None))

    def add_separator(self):
        self.__items.append((None, None, False, None))

    def add_cascade(self, label: str, items: list, enabled: bool = True):
        """添加子菜单, items 为 [(label, command), ...] 或 [(label, command, enabled), ...]"""
        children = []
        for item in items:
            if len(item) == 2: children.append((item[0], item[1], True))
            else: children.append(tuple(item[:3]))
        self.__items.append((label, None, enabled and bool(children), children))

    # -------------------------------------------------- 构建
    def __colors(self):
        try:
            c = core.window.style.colors
            return c.bg, c.fg, c.selectbg, c.selectfg, c.secondary

        except Exception:
            return "#222222", "#ffffff", "#555555", "#ffffff", "#777777"

    def __new_toplevel(self):
        toplevel = ttkbootstrap.Toplevel()
        toplevel.withdraw()
        toplevel.overrideredirect(True)
        toplevel.attributes("-topmost", True)

        frame = ttkbootstrap.Frame(toplevel, borderwidth=2, relief="solid")
        frame.pack(fill="both", expand=True)

        toplevel.bind("<FocusOut>", self.__on_focus_out)
        toplevel.bind("<Escape>", lambda *_: self.close())
        return toplevel, frame

    def __ensure_toplevel(self):
        if self.toplevel is None or not self.toplevel.winfo_exists():
            self.toplevel, self.frame = self.__new_toplevel()

    def __ensure_subtoplevel(self):
        if self.subtoplevel is None or not self.subtoplevel.winfo_exists():
            self.subtoplevel, self.subframe = self.__new_toplevel()

    def __fill(self, frame, items, on_enter=None):
        """在 frame 中绘制菜单项, 返回 (容器, 每项的控件列表)"""
        bg, fg, sbg, sfg, dfg = self.__colors()
        S = dpi.scale

        inner = tkinter.Frame(frame, bg=bg)
        inner.pack(fill="both", expand=True, padx=S(2), pady=S(2))
        inner.columnconfigure(0, weight=1)

        has_cascade = any(item[3] is not None for item in items)
        widgets = []

        for index, (label, command, enabled, children) in enumerate(items):
            if label is None:
                tkinter.Frame(inner, bg=dfg, height=1).grid(row=index, column=0, columnspan=2, sticky="ew", padx=S(8), pady=S(3))
                widgets.append(None)
                continue

            color = fg if enabled else dfg
            cursor = "hand2" if enabled else "arrow"
            text = tkinter.Label(
                inner, text=label, anchor="w", bg=bg, fg=color,
                font="TkDefaultFont", padx=S(16), pady=S(5), cursor=cursor,
            )
            arrow = tkinter.Label(
                inner, text="›" if children is not None else "", anchor="e", bg=bg, fg=color,
                font="TkDefaultFont", padx=S(10) if has_cascade else 0, pady=S(5), cursor=cursor,
            )
            text.grid(row=index, column=0, sticky="ew")
            arrow.grid(row=index, column=1, sticky="ew")

            cells = (text, arrow)
            widgets.append(cells)

            def highlight(_=None, cells=cells): [w.config(bg=sbg, fg=sfg) for w in cells]
            def restore(_=None, cells=cells, color=color): [w.config(bg=bg, fg=color) for w in cells]

            for w in cells:
                if on_enter is not None:
                    w.bind("<Enter>", lambda _, i=index: on_enter(i), add="+")
                if not enabled: continue
                w.bind("<Enter>", highlight, add="+")
                w.bind("<Leave>", restore, add="+")
                if children is None:
                    w.bind("<ButtonRelease-1>", lambda _, cmd=command: self.__invoke(cmd))

        return inner, widgets

    def __build(self):
        for row in self.__rows: row.destroy()
        self.__rows = []
        self.__row_widgets = []

        inner, self.__row_widgets = self.__fill(self.frame, self.__items, self.__on_row_enter)
        self.__rows.append(inner)

    # -------------------------------------------------- 子菜单
    def __on_row_enter(self, index: int):
        label, command, enabled, children = self.__items[index]
        if children is None or not enabled:
            self.__close_sub()
            return

        if self.__sub_index == index and self.__sub_visible(): return
        self.__open_sub(index, children)

    def __open_sub(self, index: int, children: list):
        self.__ensure_subtoplevel()

        for row in self.__subrows: row.destroy()
        self.__subrows = []

        items = [(label, command, enabled, None) for label, command, enabled in children]
        inner, _ = self.__fill(self.subframe, items)
        self.__subrows.append(inner)

        anchor = self.__row_widgets[index][0]
        self.subtoplevel.update_idletasks()
        w = self.subtoplevel.winfo_reqwidth()
        h = self.subtoplevel.winfo_reqheight()
        sw = self.subtoplevel.winfo_screenwidth()
        sh = self.subtoplevel.winfo_screenheight()

        px = self.toplevel.winfo_rootx()
        pw = self.toplevel.winfo_width()
        x = px + pw
        y = anchor.winfo_rooty() - dpi.scale(4)

        if x + w > sw: x = px - w
        if y + h > sh: y = sh - h

        self.subtoplevel.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.subtoplevel.deiconify()
        self.subtoplevel.lift()
        self.__sub_index = index

    def __close_sub(self):
        self.__sub_index = None
        if self.subtoplevel is None: return
        try: self.subtoplevel.withdraw()
        except Exception: ...

    def __sub_visible(self) -> bool:
        try: return bool(self.subtoplevel and self.subtoplevel.winfo_viewable())
        except Exception: return False

    # -------------------------------------------------- 显示 / 关闭
    def popup(self, x: int, y: int):
        if not self.__items: return

        self.__close_sub()
        self.__ensure_toplevel()
        self.__build()

        self.toplevel.update_idletasks()
        w = self.toplevel.winfo_reqwidth()
        h = self.toplevel.winfo_reqheight()
        sw = self.toplevel.winfo_screenwidth()
        sh = self.toplevel.winfo_screenheight()

        x = x - w if x + w > sw else x
        y = y - h if y + h > sh else y

        self.toplevel.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.toplevel.deiconify()
        self.toplevel.lift()
        self.toplevel.focus_force()

    def close(self):
        self.__close_sub()
        if self.toplevel is None: return
        try: self.toplevel.withdraw()
        except Exception: ...

    def is_visible(self) -> bool:
        try: return bool(self.toplevel and self.toplevel.winfo_viewable())
        except Exception: return False

    def __on_focus_out(self, *_):
        # 焦点离开菜单 (点击其他位置 / 切换窗口) 时关闭
        self.toplevel.after(10, self.__check_focus)

    def __check_focus(self):
        try: focus = self.toplevel.focus_get()
        except Exception: focus = None

        if focus is not None:
            path = str(focus)
            for toplevel in (self.toplevel, self.subtoplevel):
                if toplevel is not None and path.startswith(str(toplevel)): return

        self.close()

    def __invoke(self, command):
        self.close()
        if command is not None:
            self.master.after(0, command)
