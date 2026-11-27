# -*- coding: utf-8 -*-

import tkinter
import tkinter.font
import ttkbootstrap

from constant import help_doc
from .. import dpi


NAV_STYLE = "HelpNav.Treeview"


class About (object):
    def install(self, master):
        self.master = master
        S = dpi.scale

        self.frame = ttkbootstrap.Frame(self.master)
        self.frame.pack(side="top", fill="both", expand=True, padx=S(10), pady=S(10))

        # 左侧目录导航
        self.frame_nav = ttkbootstrap.Frame(self.frame, width=S(200))
        self.frame_nav.pack_propagate(False)
        self.frame_nav.pack(side="left", fill="y", padx=(0, S(10)))

        self.scrollbar_nav = ttkbootstrap.Scrollbar(self.frame_nav, orient="vertical")
        self.treeview_nav = ttkbootstrap.Treeview(
            self.frame_nav,
            show="tree headings",
            selectmode="browse",
            style=NAV_STYLE,
            yscrollcommand=self.scrollbar_nav.set,
        )
        self.treeview_nav.column("#0", width=S(180), minwidth=S(100), stretch=True, anchor="w")
        self.treeview_nav.heading("#0", text="目录")
        self.scrollbar_nav.config(command=self.treeview_nav.yview)

        self.scrollbar_nav.pack(side="right", fill="y", padx=(S(2), 0))
        self.treeview_nav.pack(side="left", fill="both", expand=True)

        # 右侧正文内容
        self.frame_content = ttkbootstrap.Frame(self.frame)
        self.frame_content.pack(side="left", fill="both", expand=True)

        self.title_font = self._make_title_font()
        self.label_title = ttkbootstrap.Label(self.frame_content, text="", font=self.title_font, anchor="w")
        self.label_title.pack(side="top", fill="x", padx=S(10), pady=(S(4), S(6)))

        self.separator = ttkbootstrap.Separator(self.frame_content, orient="horizontal")
        self.separator.pack(side="top", fill="x", padx=S(10), pady=(0, S(6)))

        self.frame_text = ttkbootstrap.Frame(self.frame_content)
        self.frame_text.pack(side="top", fill="both", expand=True)

        self.scrollbar = ttkbootstrap.Scrollbar(self.frame_text, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")

        self.text_help = tkinter.Text(
            self.frame_text,
            wrap="word",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=S(10),
            pady=S(6),
            spacing2=S(2),
            spacing3=S(4),
            yscrollcommand=self.scrollbar.set,
        )
        self.text_help.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.text_help.yview)

        self._sections = help_doc.HELP_SECTIONS
        for index, (title, _) in enumerate(self._sections):
            self.treeview_nav.insert("", "end", iid=str(index), text=title)

        self.treeview_nav.bind("<<TreeviewSelect>>", self._on_select)

        if self._sections:
            self.treeview_nav.selection_set("0")
            self.treeview_nav.focus("0")
            self._show_section(0)


    def _make_title_font(self):
        try:
            base = tkinter.font.Font(root=self.master, name="TkDefaultFont", exists=True)
            font = base.copy()
            font.configure(size=base.actual("size") + 3, weight="bold")
            return font

        except Exception:
            return ("TkDefaultFont", 12, "bold")


    def _on_select(self, *_):
        selected = self.treeview_nav.selection()
        if not selected: return
        try: index = int(selected[0])
        except ValueError: return
        self._show_section(index)


    def _show_section(self, index: int):
        if not (0 <= index < len(self._sections)): return
        title, content = self._sections[index]
        self.label_title.config(text=title)
        self.text_help.config(state="normal")
        self.text_help.delete("1.0", "end")
        self.text_help.insert("1.0", content.strip())
        self.text_help.yview_moveto(0)
        self.text_help.config(state="disabled")


    def __init__(self, master):
        self.master = master
        try: self.install(master)
        except Exception: ...
