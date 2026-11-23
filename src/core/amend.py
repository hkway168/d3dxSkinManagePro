# -*- coding: utf-8 -*-

import core

import ttkbootstrap

from constant import K

# 原版 d3dxSkinManage 使用的字段默认值
# 本程序与原版可共用同一个 local/configuration, 主题与缩略图匹配算法的取值互不兼容,
# 因此本程序改用 pro_ 前缀的独立字段, 不再写入原版字段
ORIGINAL_STYLE_THEME = "darkly"
ORIGINAL_THUMBNAIL_APPROXIMATE = "similarity/key-in"


def env_config_amend():
    if not isinstance(core.env.configuration.log_level, (int, str)):
        core.env.configuration.log_level = 0

    if not isinstance(core.env.configuration.annotation_level, int):
        core.env.configuration.annotation_level = 3

    theme_names = ttkbootstrap.Style().theme_names()
    if not isinstance(core.env.configuration.pro_style_theme, str) or core.env.configuration.pro_style_theme not in theme_names:
        old = core.env.configuration.style_theme
        core.env.configuration.pro_style_theme = old if isinstance(old, str) and old in theme_names else "bootstrap-dark"

    # 旧版本曾把本程序的主题名写入原版字段, 原版无法识别, 还原为原版默认值
    if isinstance(core.env.configuration.style_theme, str) and core.env.configuration.style_theme in theme_names:
        core.env.configuration.style_theme = ORIGINAL_STYLE_THEME

    # 对象列表是否显示没有本地 Mod 的对象, 默认不显示
    if not isinstance(core.env.configuration.show_empty_objects, bool):
        core.env.configuration.show_empty_objects = False

    # 是否允许一个对象同时属于多个分类, 默认开启 (与原版行为一致)
    if not isinstance(core.env.configuration.pro_object_multi_class, bool):
        core.env.configuration.pro_object_multi_class = True

    # 打开文件 / 目录的方式 (移植自原版, 可在配置文件中改为其他文件管理器)
    if not isinstance(core.env.configuration.view_explorer_path, str):
        core.env.configuration.view_explorer_path = "explorer"

    if not isinstance(core.env.configuration.view_file_rule, str):
        core.env.configuration.view_file_rule = "/select,{path}"

    if not isinstance(core.env.configuration.view_directory_rule, str):
        core.env.configuration.view_directory_rule = "{path}"

    # 头像名称匹配算法, 默认使用与旧版本一致的 "名称包含" 匹配
    if core.env.configuration.pro_thumbnail_approximate_algorithm not in K.APPROXIMATE.ALL:
        old = core.env.configuration.thumbnail_approximate_algorithm
        core.env.configuration.pro_thumbnail_approximate_algorithm = old if old in K.APPROXIMATE.ALL else K.APPROXIMATE.KEY_IN_ONLY

    # 旧版本曾把本程序的取值写入原版字段, 原版无法识别 (会导致原版缩略图全部丢失), 还原为原版默认值
    if core.env.configuration.thumbnail_approximate_algorithm in K.APPROXIMATE.ALL:
        core.env.configuration.thumbnail_approximate_algorithm = ORIGINAL_THUMBNAIL_APPROXIMATE

    # 运行 fixtool 中 .py 修复脚本的 Python 解释器路径, 留空则自动查找 (py 启动器 / PATH 中的 python)
    if not isinstance(core.env.configuration.fixtool_python, str):
        core.env.configuration.fixtool_python = ""
