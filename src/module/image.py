# -*- coding: utf-8 -*-

import os
import time
import threading
import concurrent.futures

import PIL.Image
import PIL.ImageTk
# import PIL.ImageDraw

from typing import Union

import core
from constant import *


# 缩略图目录中会被加载的图片格式
THUMBNAIL_SUFFIXES = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')

# 每批在主线程中创建的 PhotoImage 数量
THUMBNAIL_BATCH_SIZE = 40
# 加载过程中两次刷新列表的最小间隔 (秒)
THUMBNAIL_PUBLISH_INTERVAL = 0.5
# 并行解码图片的线程数 (Pillow 解码 / 缩放时会释放 GIL)
THUMBNAIL_MAX_WORKERS = max(1, min(8, os.cpu_count() or 2))


def image_resize(image_: Union[PIL.Image.Image, str], width: int, height: int, tkimg: bool = False) -> PIL.Image.Image:
    """调整图片大小, 保持原图片比例"""
    if isinstance(image_, PIL.Image.Image): picture = image_
    elif isinstance(image_, str):
        with PIL.Image.open(image_) as fileimage: picture = fileimage.copy()
    else: raise TypeError("The image_ type is not Image or str.")

    raw_width, raw_height = picture.size[0], picture.size[1]
    max_width, max_height = raw_width, height        
    min_width = max(raw_width, max_width)

    min_height = int(raw_height * min_width / raw_width)
    while min_height > height: min_height = int(min_height * .9533)
    while min_height < height: min_height += 1
    min_width = int(raw_width * min_height / raw_height)
    while min_width > width: min_width -= 1
    min_height = int(raw_height * min_width / raw_width)

    result = picture.resize((min_width, min_height))
    if tkimg: return PIL.ImageTk.PhotoImage(result)
    else: return result


def image_canvas(image_: Union[PIL.Image.Image, str], width: int, height: int, tkimg: bool = False) -> PIL.Image.Image:
    """调整图片大小, 使用指定比例, 透明背景"""
    if isinstance(image_, PIL.Image.Image): picture = image_
    elif isinstance(image_, str):
        with PIL.Image.open(image_) as fileimage: picture = fileimage.copy()
    else: raise TypeError("The image_ type is not Image or str.")

    background = PIL.Image.new('RGBA', (width, height), "#00000000")
    picture = image_resize(picture, width, height)
    bx, by = background.size; ix, iy = picture.size
    ox = (bx - ix) // 2; oy = (by - iy) // 2
    background.paste(picture, (ox, oy))

    if tkimg: return PIL.ImageTk.PhotoImage(background)
    else: return background


def _file_signature(path: str) -> tuple[int, int]:
    """文件签名 (修改时间, 大小), 用于判断图片是否被修改"""
    stat = os.stat(path)
    return (stat.st_mtime_ns, stat.st_size)


def _normalize_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def _run_in_main_thread(callobject, *args):
    """在主线程 (Tk 线程) 中执行 callobject 并等待结果

    主线程尚未进入 mainloop 时稍后重试; 主线程退出时抛出 RuntimeError, 避免子线程永久等待
    """
    if threading.current_thread() is threading.main_thread():
        return callobject(*args)

    done = threading.Event()
    box = {}

    def _call():
        try: box["result"] = callobject(*args)
        except BaseException as e: box["exception"] = e
        finally: done.set()

    for _ in range(50):
        if not threading.main_thread().is_alive(): raise RuntimeError("main thread has exited")
        try:
            core.window.mainwindow.after(0, _call)
            break

        except RuntimeError:
            time.sleep(0.2)

    else:
        raise RuntimeError("main thread is not in main loop")

    while not done.wait(0.2):
        if not threading.main_thread().is_alive(): raise RuntimeError("main thread has exited")

    if "exception" in box: raise box["exception"]
    return box.get("result")


def _create_photo_images(images: list[PIL.Image.Image]) -> list[PIL.ImageTk.PhotoImage]:
    return [PIL.ImageTk.PhotoImage(x) for x in images]



def get_preview_image(SHA: str | None, width: int, height: int):
    if SHA is None: return None
        # return PIL.ImageTk.PhotoImage(PIL.Image.new('RGBA', (width, height), "#00000000"))

    for suffix in ['.png', '.jpg']:
        target = os.path.join(core.env.directory.resources.preview, f'{SHA}{suffix}')
        if os.path.isfile(target):
            return core.module.image.image_resize(target, width, height, tkimg=True)

    for suffix in ['.png', '.jpg']:
        target = os.path.join(core.userenv.directory.work_mods, SHA, f'preview{suffix}')
        if os.path.isfile(target):
            with open(target, 'rb') as fileobject:
                with open(os.path.join(core.env.directory.resources.preview, f'{SHA}{suffix}'), 'wb') as tofileobject:
                    tofileobject.write(fileobject.read())

            return core.module.image.image_resize(target, width, height, tkimg=True)

    return None


class ImageTkThumbnailGroup(object):
    """Tk 图像 - 缩略图容器

    *注意: 这个对象的方法不是线程安全的
    """
    def __init__(self, width: int = 16, height: int = 16):
        self.__table = {}
        # 已创建的缩略图 {规范化文件路径: (文件签名, PhotoImage)}, 文件未变化时重新加载直接复用
        self.__memo = {}
        self.__paths = []
        self.__reload_lock = threading.Lock()
        self.__generation = 0
        self.__generation_lock = threading.Lock()
        self.setSize(width, height)
        self.__none = PIL.ImageTk.PhotoImage(PIL.Image.new('RGBA', (width, height), "#00000000"))


    def setSize(self, width: int, height: int) -> None:
        """设置预览图大小

        影响图片的大小和比例

        *注意: 你必须谨慎使用这个方法, 它会导致原有的图像失真 (不, 它现在会舍弃原有的图像)
        """
        if not isinstance(width, int): raise TypeError("The width type is not int.")
        if not isinstance(height, int): raise TypeError("The height type is not int.")

        if width < 10: raise ValueError("The width should not be less than 10.")
        if height < 10: raise ValueError("The height should not be less than 10.")

        self._width = width
        self._height = height

        self.__table = {}
        self.__memo = {}
        return

        newTable = {}
        for name, item in self.__table.items():
            newTable[name] = image_canvas(item, self._width, self._height)

        self.__table = newTable


    def add_image(self, image_: Union[PIL.Image.Image, str], name_: str = ...) -> None:
        core.log.debug(f"加载缩略图图像 {image_}", L.MODULE_IMAGE)
        if isinstance(image_, PIL.Image.Image):
            if name_ is Ellipsis:
                core.log.error(f"加载缩略图图像: 参数类型错误", L.MODULE_IMAGE)
                raise ValueError("name_ must be provided when image_ is an Image object.")

        if isinstance(image_, str):
            if not os.path.isfile(image_):
                core.log.error(f"加载缩略图图像: 文件不存在", L.MODULE_IMAGE)
                raise FileNotFoundError("File path not found.")

            filename = os.path.basename(image_)

            if name_ is Ellipsis:
                name_ = filename[:filename.rfind('.')]

        if not isinstance(name_, str):
            raise TypeError("The name_ type is not str.")

        img = image_canvas(image_, self._width, self._height, tkimg=True)
        self.__table[name_] = img


    @staticmethod
    def scan_dirs(path: str) -> dict[str, str]:
        """扫描目录及其所有子目录下的图片, 返回 {缩略图名称: 文件路径}

        文件名 (去掉后缀, 不含子目录路径) 即缩略图名称
        同一目录树中出现同名图片时: 层级越浅越优先, 同一层级按相对路径字母序靠前者优先
        """
        if not isinstance(path, str):
            raise TypeError("The path type is not str.")

        if not os.path.isdir(path):
            raise FileNotFoundError(f"Directory not found: {path}")

        candidates = []
        for dirpath, dirnames, filenames in os.walk(path):
            # 跳过隐藏目录, 并保证遍历顺序稳定
            dirnames[:] = sorted(x for x in dirnames if not x.startswith('.'))
            relative = os.path.relpath(dirpath, path)
            depth = 0 if relative == os.curdir else relative.count(os.sep) + 1

            for filename in filenames:
                stem, suffix = os.path.splitext(filename)
                if not stem or suffix.lower() not in THUMBNAIL_SUFFIXES: continue
                filepath = os.path.join(dirpath, filename)
                candidates.append((depth, os.path.relpath(filepath, path).lower(), stem, filepath))

        selected = {}
        for _, _, stem, filepath in sorted(candidates):
            selected.setdefault(stem, filepath)

        return selected


    def reload(self, paths: list[str]) -> None:
        """按顺序重新加载多个缩略图目录 (应在子线程中调用)

        后加载的同名缩略图会覆盖先加载的; 不存在的目录会被跳过
        - 文件未变化的缩略图直接复用内存中已创建的图像, 只有新增 / 修改的文件才需要读取
        - 加载过程中分批更新并刷新列表, 未加载到的名称暂时保留原有图像, 避免列表短暂丢失缩略图
        - 目录列表与上次不同 (切换用户) 时先清空原有图像, 避免显示其他用户的缩略图
        - 加载过程中有新的 reload 请求时, 旧的请求会提前结束, 已加载的图像由新请求复用
        """
        with self.__generation_lock:
            self.__generation += 1
            generation = self.__generation

        with self.__reload_lock:
            if generation != self.__generation: return
            completed = self.__reload(paths, generation)

        if completed:
            core.construct.event.set_event(E.THUMBNAIL_LOADED)


    def __reload(self, paths: list[str], generation: int) -> bool:
        width, height = self._width, self._height
        started = time.perf_counter()

        if self.__paths != paths:
            self.__paths = list(paths)
            self.__table = {}

        selected = {}
        for path in paths:
            if not os.path.isdir(path): continue
            try: selected.update(self.scan_dirs(path))
            except Exception as e: core.log.error(f"扫描缩略图目录 {path} 失败 {e.__class__}: {e}", L.MODULE_IMAGE)

        old_table = self.__table
        new_table = {}
        new_memo = {}
        pending = []

        for name, filepath in selected.items():
            key = _normalize_path(filepath)
            try: signature = _file_signature(filepath)
            except OSError as e:
                core.log.warning(f"读取缩略图 {filepath} 失败 {e.__class__}: {e}", L.MODULE_IMAGE)
                continue

            memo = self.__memo.get(key)
            if memo is not None and memo[0] == signature:
                new_table[name] = memo[1]
                new_memo[key] = memo

            else:
                pending.append((name, filepath, key, signature))

        reused = len(new_table)

        if pending:
            last_publish = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(THUMBNAIL_MAX_WORKERS, thread_name_prefix="thumbnail") as executor:
                futures = [executor.submit(image_canvas, filepath, width, height) for _, filepath, _, _ in pending]

                try:
                    for index in range(0, len(pending), THUMBNAIL_BATCH_SIZE):
                        batch, images = [], []
                        for item, future in zip(pending[index:index + THUMBNAIL_BATCH_SIZE], futures[index:index + THUMBNAIL_BATCH_SIZE]):
                            try: images.append(future.result())
                            except Exception as e:
                                core.log.warning(f"加载缩略图 {item[1]} 失败 {e.__class__}: {e}", L.MODULE_IMAGE)
                                continue
                            batch.append(item)

                        if generation != self.__generation: return False
                        if not batch: continue

                        photos = _run_in_main_thread(_create_photo_images, images)
                        for (name, _, key, signature), photo in zip(batch, photos):
                            new_table[name] = photo
                            new_memo[key] = (signature, photo)
                            self.__memo[key] = (signature, photo)

                        remaining = index + THUMBNAIL_BATCH_SIZE < len(pending)
                        if remaining and time.perf_counter() - last_publish >= THUMBNAIL_PUBLISH_INTERVAL:
                            self.__table = {**old_table, **new_table}
                            core.construct.event.set_event(E.THUMBNAIL_LOADED)
                            last_publish = time.perf_counter()

                finally:
                    for future in futures: future.cancel()

        if generation != self.__generation: return False

        # 近似匹配取第一个命中的名称, 因此保持扫描顺序, 使匹配结果与加载先后无关
        self.__table = {name: new_table[name] for name in selected if name in new_table}
        self.__memo = new_memo

        core.log.info(f"缩略图加载完成, 共 {len(new_table)} 张 (复用 {reused} 张, 读取 {len(new_table) - reused} 张), "
                      f"耗时 {time.perf_counter() - started:.2f}s", L.MODULE_IMAGE)
        return True


    def get(self, name: str) -> PIL.ImageTk.PhotoImage:
        if name in self.__table:
            return self.__table[name]

        algorithm = core.env.configuration.pro_thumbnail_approximate_algorithm
        if algorithm not in K.APPROXIMATE.ALL:
            algorithm = K.APPROXIMATE.KEY_IN_ONLY

        if algorithm == K.APPROXIMATE.EXACT_ONLY:
            return self.__none

        for key, value in self.__table.items():
            if algorithm == K.APPROXIMATE.KEY_IN_ONLY and key in name:
                return value

            if algorithm == K.APPROXIMATE.NAME_IN_ONLY and name in key:
                return value

            if algorithm == K.APPROXIMATE.BIDIRECTIONAL and (key in name or name in key):
                return value

        return self.__none

