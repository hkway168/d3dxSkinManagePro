# -*- coding: utf-8 -*-
"""编辑 Mod 切换键 (移植自 黎愔 的 modify_key_swap 插件 v1.4.4)

在 Mod 选择列表的右键菜单中提供 "编辑 Mod 切换键":
读取 Mod 解压缓存中 ini 文件的 [Constants] 与 [Key*] 节, 可修改
初始 Mod 索引 (global $var)、循环索引列表 ($var = 0,1,2) 以及 key / back 切换按键。
"""

# std
import os
import re
import threading

# install
import win32gui
import ttkbootstrap

# project
import core
from constant import *

from . import modify_item_data


LOG_NAME = "modify-key-swap"

# 非组合键中可被识别的特殊键 (可不加 VK_ 前缀, 大小写不敏感)
KEYS = ['VK_RIGHT', 'VK_LEFT', 'VK_UP', 'VK_DOWN',
        'VK_NUMPAD0', 'VK_NUMPAD1', 'VK_NUMPAD2', 'VK_NUMPAD3', 'VK_NUMPAD4',
        'VK_NUMPAD5', 'VK_NUMPAD6', 'VK_NUMPAD7', 'VK_NUMPAD8', 'VK_NUMPAD9',
        'VK_MULTIPLY', 'VK_ADD', 'VK_SUBTRACT', 'VK_DECIMAL', 'VK_DIVIDE',
        'VK_LBUTTON', 'VK_RBUTTON']

# 组合键中可被识别的特殊字符
COMBINATIONS = ['shift', 'ctrl', 'alt', 'no_shift', 'no_ctrl', 'no_alt']

KEY_SECTION_PATTERN = re.compile(r'^\s*\[\s*key', re.IGNORECASE | re.MULTILINE)

CANVAS_MAX_HEIGHT = 390


class selfstatus (object):
    action = threading.Lock()


# ---------------------------------------------------------------- ini 读取与解析

def read_ini(path: str) -> tuple[str, str] | None:
    """读取 ini 文件, 返回 (内容, 编码), 失败返回 None"""
    for encoding in ('utf-8', 'gbk'):
        try:
            with open(path, 'r', encoding=encoding) as f:
                return f.read(), encoding

        except UnicodeDecodeError:
            continue

        except Exception as e:
            core.log.error(f"读取 {path} 失败 {e.__class__} {e}", LOG_NAME)
            return None

    core.log.error(f"读取 {path} 失败: 无法识别文件编码", LOG_NAME)
    return None


def get_mod_ini_files(SHA: str) -> list[str]:
    """Mod 解压缓存中的 ini 文件 (跳过 disabled 开头的文件)"""
    if not SHA: return []

    dirpath = modify_item_data.get_cache_path(SHA)
    if dirpath is None: return []

    result = []
    for root, _, files in os.walk(dirpath):
        result += [os.path.join(root, x) for x in files
                   if x.lower().endswith('.ini') and not x.lower().startswith('disabled')]

    return result


def has_key_swap(SHA: str) -> bool:
    """Mod 缓存的 ini 中是否存在 [Key*] 节 (即合并 Mod)"""
    for ini_file in get_mod_ini_files(SHA):
        data = read_ini(ini_file)
        if data is not None and KEY_SECTION_PATTERN.search(data[0]):
            return True

    return False


def is_swap_key(key: str, value: str) -> bool:
    """形如 $var = 0,1,2 的循环索引变量"""
    if not key.startswith('$'): return False

    indexs = value.split(',')
    if len(indexs) == 1: return False

    for index in indexs:
        index = index.strip()
        if not index.isdigit(): return False
        if index[0] == '0' and len(index) > 1: return False

    return True


def get_sections_data(SHA: str) -> tuple[dict, dict, dict]:
    """解析 Mod 中所有 ini 文件

    返回 (sections_data, sections_origin_data, encodings)
    sections_data:        {ini: {section: {'section': name, 'key': [...], 'back': [...], '$var': '0,1', ...}}}
                          其中 Constants 节为 {var: 初始值}
    sections_origin_data: {ini: {section: [原始文本, ...]}}  (Constants 可能出现多次)
    encodings:            {ini: 编码}
    """
    sections_origin_data = {}
    sections_data = {}
    encodings = {}

    for ini_file in get_mod_ini_files(SHA):
        data = read_ini(ini_file)
        if data is None: continue

        content, encodings[ini_file] = data
        origin = sections_origin_data[ini_file] = {}
        parsed = sections_data[ini_file] = {}
        current_section = None

        for line in content.splitlines(keepends=True):
            line_ = line.strip()

            if line_.startswith('[') and line_.endswith(']'):
                current_section = line_[1:-1].strip()

                if current_section == 'Constants':
                    if current_section not in origin:
                        origin[current_section] = []
                        parsed[current_section] = {'section': current_section}

                    origin[current_section].append(line)

                elif current_section.lower().startswith('key') and current_section not in origin:
                    origin[current_section] = [line]
                    parsed[current_section] = {'section': current_section}

                else:
                    current_section = None

                continue

            if current_section is None: continue

            origin[current_section][-1] += line

            data = line.split('=')
            if len(data) != 2: continue

            key, value = data[0].strip(), data[1].strip()

            if current_section == 'Constants':
                if not key.startswith('global'): continue
                key = key.replace('global persist', '').replace('global', '').strip()
                parsed[current_section].setdefault(key, value)
                continue

            lower = key.lower()
            if lower in ('key', 'back'):
                parsed[current_section].setdefault(lower, []).append(value)

            elif is_swap_key(key, value):
                parsed[current_section].setdefault(key, value)

    return sections_data, sections_origin_data, encodings


# ---------------------------------------------------------------- 悬浮提示

# 鼠标在选择列表上移动时会频繁触发, 缓存解析结果, 离开列表或保存后清空
_hover_cache: dict[str, str] = {}
_hover_lock = threading.Lock()


def clear_hover_cache(*_):
    with _hover_lock:
        _hover_cache.clear()


def build_hover_text(SHA: str) -> str:
    """生成 Mod 切换键的提示文本, 无切换键时返回空字符串"""
    sections_data = get_sections_data(SHA)[0]

    key_swaps = [(name, section) for sections in sections_data.values()
                 for name, section in sections.items()
                 if name != 'Constants' and ('key' in section or 'back' in section)]

    count = len(key_swaps)
    text = ''

    for name, section in key_swaps:
        text += f'\n\n{name}:' if count < 5 else f'\n{name}:'
        text += '\n' if count < 10 else '    '

        key = section.get('key')
        back = section.get('back')
        if key: text += f'key = {"、".join(key)}    '
        if back: text += f'back = {"、".join(back)}'

    return text


def get_hover_text(SHA: str) -> str:
    """获取 Mod 切换键提示文本 (带缓存, 不抛出异常)"""
    with _hover_lock:
        if SHA in _hover_cache: return _hover_cache[SHA]

    try:
        text = build_hover_text(SHA) if modify_item_data.get_cache_path(SHA) else ''

    except Exception as e:
        core.log.error(f"读取切换键提示失败 {SHA} {e.__class__} {e}", LOG_NAME)
        text = ''

    with _hover_lock:
        _hover_cache[SHA] = text

    return text


# ---------------------------------------------------------------- 界面

def show_keys(key_lst: list, step: int) -> str:
    content = ''
    for index, key in enumerate(key_lst):
        content += key
        if index != len(key_lst) - 1:
            content += '、'
            if (index + 1) % step == 0: content += '\n'
    return content


KEY_ANNOTATION = (f'除正常字母、数字、符号外，还包括以下特殊键：\n切换键：\n{show_keys(KEYS, 4)}'
                  f'\n\n组合键：\n{show_keys(COMBINATIONS, 10)}')


class KeySwapLabelFrame (object):
    """单个 [Key*] 节的编辑区域"""

    def __init__(self, master, ini_file: str, key_section: dict, constants: dict, owner: 'ModifyKeySwap'):
        self.master = master
        self.ini_file = ini_file
        self.key_section = key_section
        self.constants = constants
        self.owner = owner
        self.swap_key_name = self.sbin_get_swap_key_name()

        self.value_initial = ttkbootstrap.StringVar(value=self.constants.get(self.swap_key_name, '') if self.swap_key_name else '')
        self.value_swap = ttkbootstrap.StringVar(value=self.key_section[self.swap_key_name] if self.swap_key_name else '')
        self.value_keys = [ttkbootstrap.StringVar(value=key) for key in self.key_section.get('key', [''])]
        self.value_backs = [ttkbootstrap.StringVar(value=back) for back in self.key_section.get('back', [''])]

        self.labelframe_key_swap = ttkbootstrap.LabelFrame(self.master, text=self.key_section['section'])

        self.Frame_swap = ttkbootstrap.Frame(self.labelframe_key_swap)
        self.Label_initial = ttkbootstrap.Label(self.Frame_swap, text='初始 Mod 值：')
        self.Combobox_initial = ttkbootstrap.Combobox(self.Frame_swap, width=5, postcommand=self.sbin_get_swap_vars, textvariable=self.value_initial)
        self.Label_swap = ttkbootstrap.Label(self.Frame_swap, text=f'{self.swap_key_name}：')
        self.Entry_swap = ttkbootstrap.Entry(self.Frame_swap, textvariable=self.value_swap, width=35)

        self.Frame_key = ttkbootstrap.Frame(self.labelframe_key_swap)
        self.Label_key = ttkbootstrap.Label(self.Frame_key, text='Key：')
        self.Frame_Enter_keys = ttkbootstrap.Frame(self.Frame_key)
        self.Entry_keys = [ttkbootstrap.Entry(self.Frame_Enter_keys, textvariable=x, width=15) for x in self.value_keys]

        self.Label_back = ttkbootstrap.Label(self.Frame_key, text='Back：')
        self.Frame_Enter_backs = ttkbootstrap.Frame(self.Frame_key)
        self.Entry_backs = [ttkbootstrap.Entry(self.Frame_Enter_backs, textvariable=x, width=15) for x in self.value_backs]

        if self.swap_key_name:
            self.Frame_swap.pack(side='top', fill='x')
            self.Label_initial.pack(side='left', padx=(10, 0), pady=(5, 10))
            self.Combobox_initial.pack(side='left', pady=(5, 10))
            self.Label_swap.pack(side='left', padx=(10, 0), pady=(5, 10))
            self.Entry_swap.pack(side='left', fill='x', padx=(0, 10), pady=(5, 10), expand=1)

        self.Frame_key.pack(side='top', fill='x')
        self.Label_key.pack(side='left', padx=(10, 0), pady=(5, 10))
        self.Frame_Enter_keys.pack(side='left', fill='x', pady=(5, 10), expand=1)
        for entry in self.Entry_keys:
            entry.pack(side='left', fill='x', padx=(0, 5), pady=(5, 10), expand=1)

        self.Label_back.pack(side='left', padx=(5, 0), pady=(5, 10))
        self.Frame_Enter_backs.pack(side='left', fill='x', padx=(0, 5), pady=(5, 10), expand=1)
        for entry in self.Entry_backs:
            entry.pack(side='left', fill='x', padx=(0, 5), pady=(5, 10), expand=1)

        self.value_initial.trace_add('write', lambda *_: self.bin_check_initial(check_all=True))
        self.value_swap.trace_add('write', lambda *_: self.bin_check_swap(check_all=True))
        for index, var in enumerate(self.value_keys):
            var.trace_add('write', lambda *_, v=var, n=(index != 0): self.bin_check_key(v, allow_null=n, check_all=True))
        for var in self.value_backs:
            var.trace_add('write', lambda *_, v=var: self.bin_check_back(v, check_all=True))

        _alt_set = core.window.annotation_toplevel.register
        _alt_set(self.Combobox_initial, '合并 Mod 初始加载时显示的 Mod 的索引', 2)
        _alt_set(self.Entry_swap, '循环 合并 Mod 的索引顺序\n\n每个索引之间必须以 , 进行分隔\n\n不建议小白修改此值', 2)
        for entry in self.Entry_keys:
            _alt_set(entry, f'正向切换按键，各个按键间以空格分隔\n\n{KEY_ANNOTATION}', 2)
        for entry in self.Entry_backs:
            _alt_set(entry, f'逆向切换按键，各个按键间以空格分隔\n\n{KEY_ANNOTATION}', 2)


    def set_error(self, text: str):
        self.owner.Label_except['text'] = text


    def sbin_get_swap_vars(self):
        if self.bin_check_swap(check_all=False) == -1:
            self.Combobox_initial['values'] = []
        else:
            self.Combobox_initial['values'] = [x.strip() for x in self.value_swap.get().split(',')]


    def sbin_get_swap_key_name(self) -> str:
        swap_keys = [key for key in self.key_section.keys() if key.startswith('$')]
        return swap_keys[0] if len(swap_keys) == 1 else ''


    def bin_check_initial(self, check_all=False):
        if not self.swap_key_name: return

        section = self.key_section['section']
        initial = self.value_initial.get()

        if initial == '':
            self.set_error(f'{section} {self.swap_key_name}：初始值不能为空')
            return -1

        if not initial.isdigit():
            self.set_error(f'{section} 初始 Mod 值：不能输入非自然数 {initial}')
            return -1

        if initial[0] == '0' and len(initial) > 1:
            self.set_error(f'{section} {self.swap_key_name}：数字 {initial} 不能以 0 开头')
            return -1

        self.set_error('')
        if check_all: self.owner.sbin_check_all()


    def bin_check_swap(self, check_all=False):
        if not self.swap_key_name: return

        section = self.key_section['section']
        indexs = self.value_swap.get().split(',')

        if len(indexs) == 1:
            self.set_error(f'{section} {self.swap_key_name}：循环索引列表不能只有一个值')
            return -1

        for index in indexs:
            index = index.strip()

            if index == '':
                self.set_error(f'{section} {self.swap_key_name}：循环索引列表不能为空或异常输入 ,')
                return -1

            if not index.isdigit():
                self.set_error(f'{section} {self.swap_key_name}：不能输入非自然数 {index}')
                return -1

            if index[0] == '0' and len(index) > 1:
                self.set_error(f'{section} {self.swap_key_name}：数字 {index} 不能以 0 开头')
                return -1

        self.set_error('')
        if check_all: self.owner.sbin_check_all()


    def bin_check_key(self, var, allow_null=False, check_all=False):
        error = self.sbin_check_keys(var.get(), allow_null=allow_null)

        if error:
            self.set_error(f'{self.key_section["section"]} key：{error}')
            return -1

        self.set_error('')
        if check_all: self.owner.sbin_check_all()


    def bin_check_back(self, var, check_all=False):
        error = self.sbin_check_keys(var.get(), allow_null=True)

        if error:
            self.set_error(f'{self.key_section["section"]} back：{error}')
            return -1

        self.set_error('')
        if check_all: self.owner.sbin_check_all()


    @staticmethod
    def sbin_check_keys(text: str, allow_null=False) -> str:
        keys = [key for key in text.split(' ') if key]

        if not keys:
            return '' if allow_null else '切换键不能为空'

        combinations = keys[:-1]
        checked = []

        for combination in combinations:
            lower = combination.lower()
            if lower not in COMBINATIONS: return f'组合键 {combination} 不符合要求'
            if lower in checked: return f'组合键 {combination} 重复'
            checked.append(lower)

        for lower in checked:
            inverse = lower[3:] if lower.startswith('no_') else f'no_{lower}'
            if inverse in checked:
                return f'不能同时存在组合键 {lower} 与 {inverse}'

        last = keys[-1]
        if len(last) != 1 and last.upper() not in KEYS and f'VK_{last}'.upper() not in KEYS:
            return f'切换键 {last} 不符合要求'

        return ''


    @staticmethod
    def sbin_check_key_equal(var1, var2) -> str:
        text1, text2 = var1.get(), var2.get()
        keys1 = [key for key in text1.split(' ') if key]
        keys2 = [key for key in text2.split(' ') if key]

        if not keys1 or not keys2 or len(keys1) != len(keys2): return ''

        if {x.lower() for x in keys1[:-1]} != {x.lower() for x in keys2[:-1]}: return ''

        if keys1[-1].upper().replace('VK_', '') != keys2[-1].upper().replace('VK_', ''): return ''

        return f'{text1} 不能与 {text2} 相同'


    def sbin_check_all(self):
        if self.bin_check_initial() == -1: return -1
        if self.bin_check_swap() == -1: return -1

        for index, var in enumerate(self.value_keys):
            if self.bin_check_key(var, allow_null=(index != 0)) == -1: return -1

        for var in self.value_backs:
            if self.bin_check_back(var) == -1: return -1

        all_keys = self.value_keys + self.value_backs
        for i in range(len(all_keys)):
            for j in range(i + 1, len(all_keys)):
                error = self.sbin_check_key_equal(all_keys[i], all_keys[j])
                if error:
                    self.set_error(f'{self.key_section["section"]}: {error}')
                    return -1


class ModifyKeySwap (object):
    def __init__(self, SHA: str):
        if not selfstatus.action.acquire(timeout=0.01):
            core.window.messagebox.showerror(title='互斥锁请求超时', message='已有一个 "编辑 Mod 切换键" 窗口正在使用\n请先关闭该窗口')
            return

        try:
            self.SHA = SHA
            self.sections_data, self.sections_origin_data, self.encodings = get_sections_data(SHA)
            self.LabelFrame_key_swaps: list[KeySwapLabelFrame] = []
            self.install()

        except Exception:
            selfstatus.action.release()
            raise


    def install(self):
        self.windows = ttkbootstrap.Toplevel('编辑 Mod 切换键')
        # 先隐藏, 待计算好位置后再显示
        self.windows.withdraw()
        self.windows.transient(core.window.mainwindow)

        try:
            self.windows.iconbitmap(default=core.env.file.local.iconbitmap)
            self.windows.iconbitmap(bitmap=core.env.file.local.iconbitmap)
        except Exception:
            ...

        self.Label_description = ttkbootstrap.Label(self.windows, text='')
        self.Label_except = ttkbootstrap.Label(self.windows, anchor='w', text='', foreground='red')

        self.Frame_container = ttkbootstrap.Frame(self.windows)
        self.Canvas_key_swap = ttkbootstrap.Canvas(self.Frame_container, highlightthickness=0)
        self.Frame_key_swap = ttkbootstrap.Frame(self.Canvas_key_swap)

        recognition_failure = False
        try:
            for ini_file, sections in self.sections_data.items():
                constants = sections.get('Constants')
                if constants is None: continue

                for name, section in sections.items():
                    if name == 'Constants' or 'key' not in section: continue
                    self.LabelFrame_key_swaps.append(KeySwapLabelFrame(self.Frame_key_swap, ini_file, section, constants, self))

        except Exception as e:
            core.window.status.set_status(f'识别切换键失败 {e.__class__.__name__}: {e}', LEVEL=1)
            core.log.error(f'识别切换键失败 {self.SHA} {e.__class__} {e}', LOG_NAME)
            recognition_failure = True

        self.Button_save = ttkbootstrap.Button(self.windows, text='保存', width=10, bootstyle="info-outline", command=self.bin_save)
        self.Button_cancel = ttkbootstrap.Button(self.windows, text='取消', width=10, bootstyle="success-outline", command=self.bin_cancel)

        if recognition_failure:
            self.Label_description.config(text='识别文件失败，请检查该 Mod 是否为合并 Mod')
            self.Label_description.pack(side='top', fill='x', padx=10, pady=10)

        elif not self.LabelFrame_key_swaps:
            self.Label_description.config(text='未识别到任何 Key')
            self.Label_description.pack(side='top', fill='x', padx=10, pady=10)

        self.Frame_container.pack(side='top', fill='both', expand=True)

        for labelframe in self.LabelFrame_key_swaps:
            labelframe.labelframe_key_swap.pack(side='top', fill='x', padx=10, pady=(10, 0))

        self.Canvas_key_swap.create_window((0, 0), window=self.Frame_key_swap, anchor='nw')
        self.Canvas_key_swap.pack(side='left', fill='both', expand=True)

        self.windows.update_idletasks()
        frame_width = self.Frame_key_swap.winfo_reqwidth()
        frame_height = self.Frame_key_swap.winfo_reqheight()
        self.scrollable = frame_height > CANVAS_MAX_HEIGHT

        if self.scrollable:
            self.Scrollbar_key_swap = ttkbootstrap.Scrollbar(self.Frame_container, command=self.Canvas_key_swap.yview)
            self.Scrollbar_key_swap.pack(side='right', fill='y')
            self.Canvas_key_swap.config(yscrollcommand=self.Scrollbar_key_swap.set)
            self.windows.bind('<MouseWheel>', self.scroll)

        self.Canvas_key_swap.config(width=frame_width, height=min(frame_height, CANVAS_MAX_HEIGHT),
                                    scrollregion=(0, 0, frame_width, frame_height))

        if not recognition_failure and self.LabelFrame_key_swaps:
            self.Button_save.pack(side='right', padx=10, pady=10)
        self.Button_cancel.pack(side='right', padx=(10, 0), pady=10)
        self.Label_except.pack(side='right', fill='x', expand=True, padx=(10, 0), pady=10)

        self.windows.protocol('WM_DELETE_WINDOW', self.bin_cancel)

        _alt_set = core.window.annotation_toplevel.register
        _alt_set(self.Button_save, '修改数据并保存', 2)
        _alt_set(self.Button_cancel, '什么都不做', 2)

        # 窗口隐藏时 winfo_width 无效, 使用布局请求的尺寸
        self.windows.update_idletasks()

        width = self.windows.winfo_reqwidth()
        height = self.windows.winfo_reqheight()

        buttons = self.Button_save.winfo_reqwidth() + self.Button_cancel.winfo_reqwidth() + 40
        self.Label_except.config(wraplength=max(width - buttons, 100))

        mx = self.windows.winfo_screenwidth() - width
        my = self.windows.winfo_screenheight() - height

        _x, _y = win32gui.GetCursorInfo()[2]

        x = min(max(_x - width // 2, 0), max(mx, 0))
        y = min(max(_y - height // 2 - 20, 0), max(my, 0))

        self.windows.geometry(f'+{x}+{y}')
        self.windows.resizable(False, False)
        self.windows.deiconify()


    def scroll(self, event):
        self.Canvas_key_swap.yview_scroll(-1 if event.delta > 0 else 1, 'units')


    def sbin_check_all(self):
        for labelframe in self.LabelFrame_key_swaps:
            if labelframe.sbin_check_all() == -1: return -1
        return 0


    def sbin_build_ini(self, ini_file: str, sections: dict) -> dict[str, list[str]]:
        """根据输入生成该 ini 中需要替换的节 {节名: [新文本, ...]}"""
        new_sections = {}

        for key_swap in self.LabelFrame_key_swaps:
            if key_swap.ini_file != ini_file: continue

            section_name = key_swap.key_section['section']
            section_lines = sections[section_name][0].split('\n')

            # 修改 [Key*] 节: $var 循环列表, 重新写入 key / back
            key_line_index_lst = []
            for i, line in enumerate(section_lines):
                data = line.split('=')
                if len(data) != 2: continue

                key = data[0].strip()
                if key.lower() in ('key', 'back'):
                    key_line_index_lst.append(i)

                elif key_swap.swap_key_name and key == key_swap.swap_key_name:
                    section_lines[i] = f'{key_swap.swap_key_name} = {key_swap.value_swap.get().strip()}'

            insert_index = max(key_line_index_lst)
            for name, values in (('key', key_swap.value_keys), ('back', key_swap.value_backs)):
                for var in values:
                    value = var.get().strip()
                    if not value: continue
                    insert_index += 1
                    section_lines.insert(insert_index, f'{name} = {value}')

            for i in sorted(key_line_index_lst, reverse=True):
                del section_lines[i]

            new_sections[section_name] = ['\n'.join(section_lines)]

            # 修改 [Constants] 节中 $var 的初始值
            if not key_swap.swap_key_name: continue

            constants = new_sections.get('Constants', sections['Constants'])
            new_constants = []
            for block in constants:
                lines = block.split('\n')
                for j, line in enumerate(lines):
                    data = line.split('=')
                    if len(data) != 2: continue

                    key = data[0].strip()
                    if not key.startswith('global'): continue

                    initial = key_swap.value_initial.get().strip()
                    if key.replace('global persist', '').strip() == key_swap.swap_key_name and key.startswith('global persist'):
                        lines[j] = f'global persist {key_swap.swap_key_name} = {initial}'
                        break

                    if key.replace('global', '').strip() == key_swap.swap_key_name:
                        lines[j] = f'global {key_swap.swap_key_name} = {initial}'
                        break

                new_constants.append('\n'.join(lines))

            new_sections['Constants'] = new_constants

        return new_sections


    def sbin_save(self) -> list[str]:
        """写入所有修改, 返回失败的文件列表"""
        failed = []

        for ini_file, sections in self.sections_origin_data.items():
            if 'Constants' not in sections: continue

            try:
                new_sections = self.sbin_build_ini(ini_file, sections)
                if not new_sections: continue

                data = read_ini(ini_file)
                if data is None:
                    failed.append(ini_file)
                    continue

                origin, encoding = data
                content = origin
                for name, blocks in new_sections.items():
                    for old, new in zip(sections[name], blocks):
                        content = content.replace(old, new)

                if content == origin: continue

                with open(ini_file, 'w', encoding=encoding) as f:
                    f.write(content)

                core.log.info(f"已修改切换键 {ini_file}", LOG_NAME)

            except Exception as e:
                core.log.error(f"修改切换键失败 {ini_file} {e.__class__} {e}", LOG_NAME)
                failed.append(ini_file)

        return failed


    def bin_save(self, *_):
        if self.sbin_check_all() == -1: return

        failed = self.sbin_save()
        if failed:
            core.window.messagebox.showerror(title='保存失败', message='以下文件修改失败:\n' + '\n'.join(failed), parent=self.windows)
            return

        clear_hover_cache()
        core.window.status.set_status('切换键已保存, 游戏中按 F10 重新加载后生效')
        self.bin_cancel()


    def bin_cancel(self, *_):
        self.windows.destroy()
        core.window.annotation_toplevel.withdraw()
        selfstatus.action.release()


def modify_key_swap(SHA: str):
    if not SHA or core.module.mods_index.get_item(SHA) is None: return

    try:
        ModifyKeySwap(SHA)

    except Exception as e:
        core.log.error(f"打开编辑切换键窗口失败 {SHA} {e.__class__} {e}", LOG_NAME)
        core.window.messagebox.showerror(title='程序异常', message=f'打开编辑切换键窗口失败\n{e.__class__.__name__}: {e}')


__all__ = ["modify_key_swap", "has_key_swap", "get_hover_text", "clear_hover_cache"]
