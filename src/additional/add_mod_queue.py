# -*- coding: utf-8 -*-
"""批量添加 Mod - 处理队列 (参考原版 add_mod2)

左侧为任务列表, 右侧为当前任务的编辑区; 选中多个任务时进入批量编辑模式。

线程约定:
    所有界面操作只在主线程执行;
    后台线程只负责压缩文件夹与计算 SHA, 结果通过 mainwindow.after 投递回主线程。
"""

# std
import os
import time
import shutil
import threading

# install
import ttkbootstrap
from ttkbootstrap.constants import *

# project
import core
from constant import K, T
from window import dpi

# self
from .add_mod import compute_file_sha1


GRADING_OPTIONS = ['G - 大众级', 'P - 指导级', 'R - 成人级']
GRADING_KEYS = [x[0] for x in GRADING_OPTIONS]
INDEX_FILENAME = 'self-index.json'

STATE_WAIT = '等待处理...'
STATE_COMPRESS = '正在压缩...'
STATE_CALCULATE = '正在计算...'
STATE_READY = '[就绪]'


class InputCache (object):
    """输入记忆, 下一个任务默认沿用上次确认导入时的输入"""
    object_ = ''
    grading = GRADING_OPTIONS[0]
    author = ''
    explain = ''
    tags = ''


_temp_lock = threading.Lock()
_temp_count = 0


def _new_temp_path() -> str:
    global _temp_count
    with _temp_lock:
        _temp_count += 1
        count = _temp_count

    name = f'{hex(int(time.time() * 10 ** 8))}_{count:05d}.7z'
    return os.path.join(core.env.directory.resources.cache, name)


def _post(func, *args):
    """将回调投递到主线程执行"""
    try: core.window.mainwindow.after(0, func, *args)
    except Exception: ...


def _get_authors() -> list[str]:
    authors = set()
    try:
        for SHA in core.module.mods_index.get_all_sha_list():
            item = core.module.mods_index.get_item(SHA) or {}
            author = str(item.get(K.INDEX.AUTHOR, '') or '').strip()
            if author: authors.add(author)

    except Exception: ...

    return sorted(authors)


def _grading_text(key: str) -> str:
    for text in GRADING_OPTIONS:
        if text[0] == key: return text
    return key


def is_supported(path: str) -> bool:
    """是否可以作为 Mod 导入 (文件夹 / 压缩包 / ini)"""
    if os.path.isdir(path): return True
    if not os.path.isfile(path): return False
    suffix = os.path.splitext(path)[1].lower()
    return suffix in K.MOD_TYPE.ARCHIVE_SUFFIXES or suffix in K.MOD_TYPE.PLAIN_SUFFIXES



class _EditForm (object):
    """编辑表单 (单个任务与批量编辑共用的界面布局)"""

    def _install_form(self, master, owner):
        S = dpi.scale
        self.owner = owner
        self.frame = ttkbootstrap.Frame(master)

        self.v_object = ttkbootstrap.StringVar(self.frame)
        self.v_name = ttkbootstrap.StringVar(self.frame)
        self.v_grading = ttkbootstrap.StringVar(self.frame)
        self.v_author = ttkbootstrap.StringVar(self.frame)
        self.v_explain = ttkbootstrap.StringVar(self.frame)
        self.v_tags = ttkbootstrap.StringVar(self.frame)

        self.information = ttkbootstrap.Frame(self.frame)
        self.information.pack(side=TOP, fill=X)
        self.information.columnconfigure(1, weight=1)

        labels = ['SHA:', '作用对象：', '模组名称：', '年龄分级：', '模组作者：', '附加描述：', '类型标签：']
        for row, text in enumerate(labels):
            ttkbootstrap.Label(self.information, text=text).grid(row=row, column=0, sticky=E, pady=(0 if row == 0 else S(5), 0))

        self.w_label_sha = ttkbootstrap.Label(self.information, text='')
        self.w_combobox_object = ttkbootstrap.Combobox(self.information, textvariable=self.v_object)
        self.w_entry_name = ttkbootstrap.Entry(self.information, textvariable=self.v_name)
        self.w_combobox_grading = ttkbootstrap.Combobox(self.information, textvariable=self.v_grading, values=GRADING_OPTIONS)
        self.w_combobox_author = ttkbootstrap.Combobox(self.information, textvariable=self.v_author, postcommand=self._load_authors)
        self.w_entry_explain = ttkbootstrap.Entry(self.information, textvariable=self.v_explain)
        self.w_entry_tags = ttkbootstrap.Entry(self.information, textvariable=self.v_tags)
        self.w_button_tags = ttkbootstrap.Button(self.information, text='+', bootstyle=(OUTLINE, SUCCESS), command=self.set_tags)

        widgets = [self.w_label_sha, self.w_combobox_object, self.w_entry_name, self.w_combobox_grading,
                   self.w_combobox_author, self.w_entry_explain, self.w_entry_tags]
        for row, widget in enumerate(widgets):
            widget.grid(row=row, column=1, sticky=EW, padx=(S(5), 0), pady=(0 if row == 0 else S(5), 0))

        self.w_button_tags.grid(row=6, column=2, sticky=W, padx=(S(5), 0), pady=(S(5), 0))

        self.w_label_mistake = ttkbootstrap.Label(self.frame, text='', bootstyle=DANGER, justify=LEFT)
        self.w_label_mistake.pack(side=TOP, fill=X, pady=(S(10), 0))
        self.w_label_warn = ttkbootstrap.Label(self.frame, text='', bootstyle=WARNING, justify=LEFT)
        self.w_label_warn.pack(side=TOP, fill=X, pady=(S(5), 0))

        _alt = core.window.annotation_toplevel.register
        _alt(self.w_combobox_object, T.ANNOTATION_OBJECT, 2)
        _alt(self.w_entry_name, T.ANNOTATION_NAME, 2)
        _alt(self.w_combobox_grading, T.ANNOTATION_GRADING, 2)
        _alt(self.w_combobox_author, T.ANNOTATION_AUTHOR, 2)
        _alt(self.w_entry_explain, T.ANNOTATION_EXPLAIN, 2)
        _alt(self.w_entry_tags, T.ANNOTATION_TAGS, 2)


    def _load_authors(self):
        self.w_combobox_author.configure(values=_get_authors())


    def set_tags(self, *_):
        core.additional.modify_item_data.select_tags_for_entry(self.w_entry_tags, self.owner.window)


    def set_object_values(self, values: list[str]):
        self.w_combobox_object.configure(values=values)


    def show(self):
        self.frame.pack(side=TOP, fill=BOTH, expand=True)


    def hide(self):
        self.frame.pack_forget()



class AddModUnit (_EditForm):
    """单个 Mod 添加任务"""

    def __init__(self, owner: 'AddModQueue', taskid: str, path: str, master):
        self.taskid = taskid
        self.path = os.path.normpath(path)
        self.is_dir = os.path.isdir(self.path)

        basename = os.path.basename(self.path)
        if self.is_dir:
            self.prefix, self.suffix = basename, '7z'
        else:
            stem, ext = os.path.splitext(basename)
            self.prefix, self.suffix = stem, ext[1:].lower()

        self.SHA = ''
        self.filepath = None    # 实际导入的文件 (文件夹会先压缩为临时 7z)
        self.tempfile = None
        self.state = STATE_WAIT
        self.ready = False
        self.mistaken = False
        self.closed = False
        self.computing = False

        self._install_form(master, owner)
        _alt = core.window.annotation_toplevel.register
        _alt(self.w_label_sha, T.ANNOTATION_SHA, 2)

        self.w_label_sha.configure(text='等待扫描...')
        self.v_name.set(self.prefix)
        self.v_grading.set(InputCache.grading or GRADING_OPTIONS[0])
        self.v_author.set(InputCache.author)
        self.v_explain.set(InputCache.explain)
        self.v_tags.set(InputCache.tags)

        self.v_object.trace_add('write', self._object_update)
        self.v_name.trace_add('write', lambda *_: self.owner.refresh_item(self))


    @property
    def name(self) -> str:
        return self.v_name.get().strip() or self.prefix


    def _set_state(self, state: str):
        self.state = state
        self.owner.refresh_item(self)


    def _set_mistake(self, text: str = ''):
        self.w_label_mistake.configure(text=text)


    def _object_update(self, *_):
        object_ = self.v_object.get().strip()
        if object_ and core.module.mods_manage.get_object_class(object_) is None:
            self.w_label_warn.configure(text='无法预测对象名称的分类，该对象将会归于未分类')
        else:
            self.w_label_warn.configure(text='')


    def _fail(self, state: str, message: str):
        self.mistaken = True
        self.ready = False
        self._set_mistake(message)
        self._set_state(f'[错误] {state}')


    # ---------- 后台计算 ----------

    def start(self):
        self.computing = True
        self._set_state(STATE_COMPRESS if self.is_dir else STATE_CALCULATE)
        self.w_label_sha.configure(text=self.state)
        threading.Thread(None, self._worker, 'AddModUnit.calculate', daemon=True).start()


    def _worker(self):
        """后台线程: 不得访问任何 tkinter 对象"""
        result = {'filepath': None, 'tempfile': None, 'SHA': None, 'error': None}

        try:
            if self.is_dir:
                if not os.path.isfile(core.env.file.local.t7z):
                    raise RuntimeError(('组件缺失', f'找不到 7zip 组件\n{core.env.file.local.t7z}'))

                os.makedirs(core.env.directory.resources.cache, exist_ok=True)
                tempfile = _new_temp_path()
                core.external.a7z(os.path.join(self.path, '*'), tempfile)

                if not os.path.isfile(tempfile):
                    raise RuntimeError(('压缩失败', '无法将该文件夹压缩为 Mod 文件\n请确认文件夹不为空且有写入缓存目录的权限'))

                result['tempfile'] = result['filepath'] = tempfile
                _post(self._on_progress, STATE_CALCULATE)

            else:
                if not os.path.isfile(self.path):
                    raise RuntimeError(('未找到文件', '无法找到目标文件或文件夹\n请取消该任务'))
                result['filepath'] = self.path

            if os.path.getsize(result['filepath']) <= 0:
                raise RuntimeError(('文件无效', '该文件的内容为空\n无法作为 Mod 导入'))

            result['SHA'] = compute_file_sha1(result['filepath'])

        except RuntimeError as e:
            arg = e.args[0] if e.args else None
            result['error'] = arg if isinstance(arg, tuple) else (e.__class__.__name__, str(e))

        except Exception as e:
            result['error'] = (e.__class__.__name__, f'无法扫描目标文件或文件夹\n{e}')

        _post(self._on_computed, result)


    def _on_progress(self, state: str):
        if self.closed: return
        self.w_label_sha.configure(text=state)
        self._set_state(state)


    def _on_computed(self, result: dict):
        self.computing = False
        self.tempfile = result['tempfile']
        self.filepath = result['filepath']

        if self.closed:
            self.clear_cache()
            return

        if result['error']:
            state, message = result['error']
            self.w_label_sha.configure(text='-')
            self._fail(state, message)
            return

        self.SHA = result['SHA']
        self.w_label_sha.configure(text=self.SHA)

        data = core.module.mods_index.get_item(self.SHA)

        if data is not None and self._is_local():
            self._fail('已存在的项目', f'该 SHA 已经存在\n{data.get(K.INDEX.OBJECT)} - {data.get(K.INDEX.NAME)}\n请取消该任务')
            return

        # 只有索引数据没有文件: 沿用已有数据
        if data is not None:
            self.v_object.set(data.get(K.INDEX.OBJECT, ''))
            self.v_name.set(data.get(K.INDEX.NAME, self.prefix))
            self.v_grading.set(_grading_text(data.get(K.INDEX.GRADING, 'G')))
            self.v_author.set(data.get(K.INDEX.AUTHOR, ''))
            self.v_explain.set(data.get(K.INDEX.EXPLAIN, ''))
            self.v_tags.set(' '.join(data.get(K.INDEX.TAGS, [])))

        self.ready = True
        self._set_mistake()
        self._set_state(STATE_READY)


    def _is_local(self) -> bool:
        return os.path.isfile(os.path.join(core.env.directory.resources.mods, self.SHA))


    # ---------- 操作 ----------

    def action_sure(self) -> bool:
        """确认导入, 返回是否已完成 (完成后任务会被移除)"""
        if self.mistaken or self.closed: return False

        if not self.ready:
            self._set_mistake('请等待计算完成')
            return False

        z_object = self.v_object.get().strip()
        z_name = self.v_name.get().strip()
        s_grading = self.v_grading.get().strip()
        z_grading = s_grading[:1].upper()
        z_author = self.v_author.get().strip()
        z_explain = self.v_explain.get().strip()
        z_tags = [x for x in self.v_tags.get().split(' ') if x]

        if not z_object: return self._invalid('未填写 作用对象')
        if not z_name: return self._invalid('未填写 模组名称')
        if not z_grading: return self._invalid('未填写 年龄分级')
        if z_grading not in GRADING_KEYS: return self._invalid('年龄分级 只能是 G P R 其中之一')

        data = core.module.mods_index.get_item(self.SHA)

        # 同一批次中重复的 Mod, 前一个已经导入
        if data is not None and self._is_local():
            self._fail('已存在的项目', f'该 SHA 已经存在\n{data.get(K.INDEX.OBJECT)} - {data.get(K.INDEX.NAME)}\n请取消该任务')
            return False

        datacontent = {
            K.INDEX.OBJECT: z_object,
            K.INDEX.TYPE: self.suffix,
            K.INDEX.NAME: z_name,
            K.INDEX.AUTHOR: z_author,
            K.INDEX.GRADING: z_grading,
            K.INDEX.EXPLAIN: z_explain,
            K.INDEX.TAGS: z_tags,
        }

        try:
            os.makedirs(core.env.directory.resources.mods, exist_ok=True)
            shutil.copyfile(self.filepath, os.path.join(core.env.directory.resources.mods, self.SHA))

        except Exception as e:
            self._set_mistake(f'无法写入文件 {e.__class__.__name__}\n{e}\n请重试或取消该任务')
            self._set_state('[错误] 无法写入文件')
            return False

        try:
            if data is not None:
                core.module.mods_index.item_data_update(self.SHA, datacontent)
            else:
                filepath = os.path.join(core.userenv.directory.mods_index, INDEX_FILENAME)
                core.module.mods_index.item_data_new(filepath, self.SHA, datacontent)

        except Exception as e:
            self._set_mistake(f'索引数据写入失败 {e.__class__.__name__}\n{e}')
            self._set_state('[错误] 无法写入索引')
            return False

        InputCache.object_ = z_object
        InputCache.grading = _grading_text(z_grading)
        InputCache.author = z_author
        InputCache.explain = z_explain
        InputCache.tags = ' '.join(z_tags)

        self.close()
        return True


    def _invalid(self, message: str) -> bool:
        self._set_mistake(message)
        self._set_state('[错误] 数据不完整')
        return False


    def close(self):
        self.closed = True
        if not self.computing: self.clear_cache()

        try: self.frame.destroy()
        except Exception: ...


    def clear_cache(self):
        if not self.tempfile: return
        try: os.remove(self.tempfile)
        except Exception: ...
        self.tempfile = None



class BatchEditUnit (_EditForm):
    """批量编辑: 对输入框的修改会同时写入所有选中的任务"""

    FIELDS = ('v_object', 'v_name', 'v_grading', 'v_author', 'v_explain', 'v_tags')

    def __init__(self, owner: 'AddModQueue', master):
        self.units: list[AddModUnit] = []
        self.pause_editing = True

        self._install_form(master, owner)
        self.w_label_sha.configure(text='批量编辑模式')
        core.window.annotation_toplevel.register(self.w_label_sha, T.ANNOTATION_ADD_MODS_SHA_BATCH, 2)
        self.w_label_warn.configure(text='进入批量编辑模式时，输入框显示的是出现次数最多的内容\n只有被编辑过的输入框才会应用到所有选中的任务')

        for attr in self.FIELDS:
            getattr(self, attr).trace_add('write', lambda *_, a=attr: self._apply(a))


    def initial(self, units: list[AddModUnit]):
        self.pause_editing = True
        self.units = units

        for attr in self.FIELDS:
            values = [getattr(unit, attr).get() for unit in units]
            getattr(self, attr).set(find_most_common(values))

        self.pause_editing = False


    def _apply(self, attr: str):
        if self.pause_editing: return
        value = getattr(self, attr).get()
        for unit in self.units:
            if unit.closed: continue
            getattr(unit, attr).set(value)



class AddModQueue (object):
    def __init__(self):
        self.window = None
        self.tasks: dict[str, AddModUnit] = {}
        self.serial = 0
        self.current = None


    def _exists(self) -> bool:
        try: return self.window is not None and bool(self.window.winfo_exists())
        except Exception: return False


    def _install(self):
        S = dpi.scale
        self.tasks = {}
        self.current = None

        self.window = ttkbootstrap.Toplevel('添加 Mods - 处理队列')
        self.window.withdraw()
        self.window.transient(core.window.mainwindow)
        self.window.protocol('WM_DELETE_WINDOW', self.bin_close)

        try:
            self.window.iconbitmap(default=core.env.file.local.iconbitmap)
            self.window.iconbitmap(bitmap=core.env.file.local.iconbitmap)
        except Exception: ...

        self.treeview = ttkbootstrap.Treeview(self.window, selectmode=EXTENDED, show=TREE)
        self.treeview.column('#0', width=S(200), stretch=False)
        self.treeview.pack(side=LEFT, fill=Y, padx=S(5), pady=S(5))
        self.treeview.bind('<<TreeviewSelect>>', self.bin_select_update)

        self.frame_content = ttkbootstrap.Frame(self.window)
        self.frame_content.pack(side=RIGHT, fill=BOTH, expand=True, padx=(0, S(5)), pady=S(5))

        self.frame_option = ttkbootstrap.Frame(self.frame_content)
        self.frame_option.pack(side=BOTTOM, fill=X)

        self.frame_unit = ttkbootstrap.Frame(self.frame_content)
        self.frame_unit.pack(side=TOP, fill=BOTH, expand=True, pady=(0, S(5)))

        self.button_sure = ttkbootstrap.Button(self.frame_option, text='确定', width=10, bootstyle=(OUTLINE, SUCCESS), command=self.bin_sure)
        self.button_cancel = ttkbootstrap.Button(self.frame_option, text='取消', width=10, bootstyle=(OUTLINE, WARNING), command=self.bin_cancel)
        self.button_select = ttkbootstrap.Button(self.frame_option, text='全选', width=10, bootstyle=(OUTLINE, INFO), command=self.bin_select_all)
        self.button_sure.pack(side=RIGHT)
        self.button_cancel.pack(side=RIGHT, padx=(0, S(5)))
        self.button_select.pack(side=LEFT)

        self.batch_edit = BatchEditUnit(self, self.frame_unit)

        _alt = core.window.annotation_toplevel.register
        _alt(self.button_sure, T.ANNOTATION_ADD_MODS_SURE, 2)
        _alt(self.button_cancel, T.ANNOTATION_ADD_MODS_CANCEL, 2)
        _alt(self.button_select, T.ANNOTATION_ADD_MODS_SELECT_ALL, 2)

        from window import dialogs
        dialogs.center_window(self.window, core.window.mainwindow, S(760), S(460))
        self.window.minsize(S(600), S(380))


    def add(self, *paths: str):
        if threading.current_thread() is not threading.main_thread():
            _post(self.add, *paths)
            return

        if not self._exists(): self._install()

        # 作用对象默认值与候选项取自主界面当前选择
        object_ = core.window.interface.mods_manage.sbin_get_select_objects() or InputCache.object_
        class_name = core.window.interface.mods_manage.sbin_get_select_classification()
        object_values = core.module.mods_manage.get_reference_object_list(class_name) if class_name else []

        new_units = []
        for path in paths:
            self.serial += 1
            taskid = f'TASK-{self.serial}'
            unit = AddModUnit(self, taskid, path, self.frame_unit)
            unit.set_object_values(object_values)
            unit.v_object.set(object_)
            self.tasks[taskid] = unit
            self.treeview.insert('', END, taskid, text='')
            self.refresh_item(unit)
            new_units.append(unit)

        for unit in new_units: unit.start()

        self.window.deiconify()
        self.window.lift()
        self.window.focus_set()

        if new_units:
            self.treeview.selection_set(new_units[-1].taskid)
            self.treeview.see(new_units[-1].taskid)


    def refresh_item(self, unit: AddModUnit):
        if unit.closed or not self.treeview.exists(unit.taskid): return
        self.treeview.item(unit.taskid, text=f'{unit.name}\n{unit.state}')


    def _show(self, form):
        if self.current is form: return
        if self.current is not None:
            try: self.current.hide()
            except Exception: ...
        self.current = form
        if form is not None: form.show()


    def _selected_units(self) -> list[AddModUnit]:
        return [self.tasks[x] for x in self.treeview.selection() if x in self.tasks]


    def bin_select_update(self, *_):
        units = self._selected_units()

        if not units:
            self._show(None)

        elif len(units) == 1:
            self._show(units[0])

        else:
            self._show(None)
            self.batch_edit.initial(units)
            self._show(self.batch_edit)


    def _remove(self, units: list[AddModUnit]):
        if not units: return

        children = list(self.treeview.get_children())
        indexes = [children.index(u.taskid) for u in units if u.taskid in children]
        last_index = max(indexes) if indexes else 0

        if self.current in units: self.current = None

        for unit in units:
            self.tasks.pop(unit.taskid, None)
            if self.treeview.exists(unit.taskid): self.treeview.delete(unit.taskid)

        remaining = list(self.treeview.get_children())
        if not remaining:
            self._show(None)
            self.bin_close()
            return

        # 移除后自动选中相邻的任务, 避免右侧空白
        if not self.treeview.selection():
            index = min(last_index - len(units) + 1, len(remaining) - 1)
            self.treeview.selection_set(remaining[max(0, index)])

        self.bin_select_update()


    def bin_sure(self, *_):
        units = self._selected_units()
        if not units: return

        finished = [unit for unit in units if unit.action_sure()]
        self._remove(finished)

        if finished: core.log.info(f'批量添加 Mod 完成 {len(finished)} 个')


    def bin_cancel(self, *_):
        units = self._selected_units()
        for unit in units: unit.close()
        self._remove(units)


    def bin_select_all(self, *_):
        self.treeview.selection_set(self.treeview.get_children())


    def bin_close(self, *_):
        """关闭窗口仅隐藏, 队列中的任务会保留到下次添加时继续处理"""
        try: core.window.annotation_toplevel.withdraw()
        except Exception: ...
        if self._exists(): self.window.withdraw()



def find_most_common(values: list[str]) -> str:
    """返回出现次数最多的非空字符串, 并列时以 " | " 连接"""
    counts = {}
    for value in values:
        if value: counts[value] = counts.get(value, 0) + 1

    if not counts: return ''

    top = max(counts.values())
    return ' | '.join(x for x in counts if counts[x] == top)



queue = AddModQueue()


def add_mods(paths: list[str]):
    queue.add(*paths)
