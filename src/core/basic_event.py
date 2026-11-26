# -*- coding: utf-8 -*-

import os

import core
from constant import *


def initial():
    core.log.info("初始化信号事件...", L.CORE)

    core.construct.event.register(E.ENTER_MAINPOOL, when_entering_mainpool)
    core.construct.event.register(E.USER_LOGGED_IN, user_logged_in)
    core.construct.event.register(E.USER_LOGGED_OUT, user_logged_out)

    core.construct.event.register(E.MODS_INDEX_UPDATE, lambda *_: core.sync.addtask("刷新模组管理", core.module.mods_manage.refresh))
    core.construct.event.register(E.MODS_MANAGE_CACHE_REFRESHED, update_all_list)
    core.construct.event.register(E.THUMBNAIL_LOADED, update_all_list)

    core.construct.event.register(E.MOD_LOADED, update_objects_list)
    core.construct.event.register(E.MOD_LOADED, update_choices_list)
    core.construct.event.register(E.MOD_UNLOADED, update_objects_list)
    core.construct.event.register(E.MOD_UNLOADED, update_choices_list)

    core.construct.event.register(E.WINDOW_MODS_MANAGE_TS_CLASS, update_objects_list)
    core.construct.event.register(E.WINDOW_MODS_MANAGE_TS_OBJECT, update_choices_list)
    core.construct.event.register(E.WINDOW_MODS_MANAGE_TS_OBJECT, update_preview)
    core.construct.event.register(E.WINDOW_MODS_MANAGE_TS_CHOICE, update_preview)

    core.module.tags_manage.initial()


def when_entering_mainpool():
    core.sync.addtask("初始化登录用户列表", core.window.login.initial)
    core.sync.addtask("登录就绪", core.window.ready_login)


def reload_thumbnail():
    """重新加载当前用户的缩略图 resources/thumbnail/<用户名>, 未登录时不加载任何缩略图"""
    path = core.userenv.file.thumbnail
    paths = [path] if isinstance(path, str) else []
    core.construct.taskpool.newtask(core.window.treeview_thumbnail.reload, (paths, ))


def migrate_thumbnail() -> str | None:
    """将旧的用户级缩略图移动到 resources/thumbnail/<用户名>, 返回需要提示的内容"""
    from additional import set_thumbnail

    source, target = core.userenv.file.legacy_thumbnail, core.userenv.file.thumbnail
    if not isinstance(source, str) or not isinstance(target, str): return None

    try:
        moved, conflicts, failed = set_thumbnail.migrate_legacy(source, target)

    except Exception as e:
        core.log.error(f"移动用户级缩略图失败 {e.__class__}: {e}", L.CORE)
        return f"移动用户级缩略图失败：\n{e}"

    lines = []
    if moved: lines.append(f"已移动 {moved} 张图片")
    for title, items in (("以下图片在目标文件夹中已有同名图片，未移动", conflicts), ("以下图片移动失败", failed)):
        if not items: continue
        lines.append(f"\n{title}（{len(items)} 张）：")
        lines.extend(f"● {x}" for x in items[:10])
        if len(items) > 10: lines.append("……")

    if not lines: return None

    core.log.info(f"移动用户级缩略图: 移动 {moved} 张, 同名未移动 {conflicts}, 失败 {failed}", L.CORE)
    if conflicts or failed: lines.append("\n未移动的图片仍保留在原文件夹中，但不会被读取，请手动处理")

    return (f"不再读取用户级缩略图文件夹：\n{os.path.abspath(source)}\n\n"
            f"其中的图片移动到：\n{os.path.abspath(target)}\n\n" + "\n".join(lines))


def check_thumbnail_directory():
    """未检测到 resources/thumbnail/<用户名> 文件夹时给予提示 (不自动创建)"""
    path = core.userenv.file.thumbnail
    if not isinstance(path, str) or os.path.isdir(path): return

    core.log.warning(f"未检测到缩略图文件夹 {path}", L.CORE)
    core.window.messagebox.showwarning(
        title="未检测到缩略图文件夹",
        message=f"未检测到当前用户对应的缩略图文件夹：\n{os.path.abspath(path)}\n\n"
                "请创建与用户名同名的文件夹并放入缩略图（可包含子文件夹），然后重新登录\n"
                "也可以右键分类 / 对象设置缩略图，届时会自动创建")


def user_logged_in():
    core.sync.addtask("加载所有 index 文件", core.module.index_manage.auto_load_all_index_file)
    core.sync.addtask("刷新模组管理", core.module.mods_manage.refresh)
    core.sync.addtask('更新 d3dx 信息', core.window.interface.d3dx_manage.update)

    # 先移动再加载; 提示框会阻塞当前线程, 放在最后
    message = migrate_thumbnail()
    reload_thumbnail()
    if message is not None: core.window.messagebox.showinfo(title="用户级缩略图", message=message)
    check_thumbnail_directory()


def user_logged_out():
    reload_thumbnail()


def update_all_list():
    update_choices_list()
    update_objects_list()
    update_classification_list()


def update_classification_list():
    core.window.mainwindow.after(0, core.window.interface.mods_manage.update_classification_list)


def update_objects_list():
    core.window.mainwindow.after(0, core.window.interface.mods_manage.update_objects_list)


def update_choices_list():
    core.window.mainwindow.after(0, core.window.interface.mods_manage.update_choices_list)
    # core.construct.taskpool.newtask(core.window.interface.modsmanage.update_choices_list)

def update_preview():
    core.window.mainwindow.after(0, core.window.interface.mods_manage.sbin_update_preview)
