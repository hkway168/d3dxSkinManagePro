# -*- coding: utf-8 -*-

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

    reload_thumbnail()


def reload_thumbnail():
    """重新加载缩略图: resources/thumbnail (全局) + home/<用户名>/thumbnail (用户级, 同名时优先)"""
    paths = [core.env.file.resources.redirection]
    if core.userenv.user_name is not Ellipsis and isinstance(core.userenv.file.redirection, str):
        paths.append(core.userenv.file.redirection)

    core.construct.taskpool.newtask(core.window.treeview_thumbnail.reload, (paths, ))


def user_logged_in():
    core.sync.addtask("加载所有 index 文件", core.module.index_manage.auto_load_all_index_file)
    core.sync.addtask("刷新模组管理", core.module.mods_manage.refresh)
    core.sync.addtask('更新 d3dx 信息', core.window.interface.d3dx_manage.update)
    reload_thumbnail()


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
