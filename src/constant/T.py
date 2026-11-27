# -*- coding: utf-8 -*-


ANNOTATION_USER_DESCRIPTION = """这是该用户的描述文档
你可以修改 ./home/<USERNAME>/ 下的 description.txt 文件来修改这项描述"""

ANNOTATION_LOGOUT = """点击退出当前用户并返回登录界面
退出前会自动保存索引数据和用户配置"""

ANNOTATION_MANAGE_CLASSIFICATION = "\n".join([
    "左键单击 查看对应类别的对象",
    "右键单击 添加分类 / 管理分类 / 设置缩略图"
])

ANNOTATION_MANAGE_OBJECTS = "\n".join([
    "左键单击 查看对应对象的 Mod",
    "右键单击 添加对象 / 管理子对象 / 设置缩略图"
])

ANNOTATION_MANAGE_CHOICES = "\n".join([
    "左键单击 查看对应 Mod 的预览图",
    "左键双击 加载对应 Mod 至 3DMiGoto",
    "右键单击 Mod 修改信息 / 编辑切换键 / 缓存与原始文件 / 修复 / 置顶",
    "右键单击 排序方式 / 优先显示",
    "左键双击 \"卸载该对象\" 卸载 Mod"
])

ANNOTATION_MANAGE_SEARCH = """可通过以下字段的内容筛选 Mod
SHA、对象、名称、分级、作者、标签
使用空格分割多个关键字
使用 "!" 符号开头拒绝对应关键词
切换对象仍然有效"""

ANNOTATION_STYLE_THEME = """主题风格
挑选一个你喜欢的色彩搭配

该项设置立即生效"""

ANNOTATION_LOG_LEVEL = """日志等级
等级越高记录的信息越多

ALL - 记录所有级别的日志
OFF - 关闭日志记录器

该项设置在重启后生效"""

ANNOTATION_ANNOTATION_LEVEL = """描述提示词数量
显示操作描述的数量

若你已经了解该软件的相关操作
可以适当减少一些操作描述

该项设置立即生效"""

ANNOTATION_THUMBNAIL_APPROXIMATE = """头像匹配算法
决定分类 / 对象列表的缩略图如何与
resources\\thumbnail\\<用户名> 目录下的图片名称配对
(名称完全相同时始终优先精确命中)

精确匹配 - 仅使用名称完全相同的图片
图片名包含于对象名 - 图片名是对象名的一部分 (默认)
对象名包含于图片名 - 对象名是图片名的一部分
双向包含 - 上述任一成立即可, 更易误匹配

该项设置立即生效"""

ANNOTATION_SHOW_EMPTY_OBJECTS = """显示空对象
开启后，本地没有任何 Mod 的对象也会出现在对象列表中
关闭时分类后的数量也只统计有 Mod 的对象

默认关闭，该项设置立即生效"""

ANNOTATION_OBJECT_MULTI_CLASS = """对象可属于多个分类
开启：同一对象可同时出现在多个分类中（与原版 d3dxSkinManage 一致）
关闭：一个对象只归入排序最靠前的分类，
      添加已在其他分类中的对象时会询问是否移动

切换不会修改分类文件，只有在关闭状态下编辑分类时才会按单分类规则保存
默认开启，该项设置立即生效"""

ANNOTATION_XXMI_ROOT = """XXMI Launcher 所在目录
3DMigoto 本体由 XXMI Launcher 负责下载与更新
请选择包含「XXMI Launcher Config.json」
或「Resources\\Bin\\XXMI Launcher.exe」的目录

该项为全局设置, 所有用户共用"""

ANNOTATION_XXMI_IMPORTER = """模组导入器
选择与当前游戏对应的导入器
GIMI 原神 / SRMI 星穹铁道 / ZZMI 绝区零
WWMI 鸣潮 / HIMI 崩坏3 / EFMI 终末地

选择后会把该导入器的目录指向当前用户的 work 目录"""

ANNOTATION_XXMI_STATUS = """当前 XXMI Launcher 的对接状态
已就绪表示导入器目录已指向当前用户的 work 目录
且 work 目录中已存在 XXMI 部署的 3DMigoto 文件"""

ANNOTATION_XXMI_LAUNCH = """启动 XXMI Launcher 图形界面
首次使用或需要更新 3DMigoto 时, 在其中点击安装/更新
注意: XXMI Launcher 退出时会回写配置
修改配置前请先关闭它"""

ANNOTATION_D3DX_START = "由 XXMI Launcher 注入并启动游戏\n启动前请确认 3DMigoto 已安装至工作目录"

ANNOTATION_D3DX_OPEN_WORK_DIR = "在文件资源管理器中打开 3DMiGoto 的工作目录"

ANNOTATION_D3DX_SET_GAME_PATH = "用户必须使用文件选择工具修改游戏路径\n直接修改输入框的内容是不生效的"

ANNOTATION_D3DX_GAME_WORK_DIR = "在文件资源管理器中打开游戏所在目录"

ANNOTATION_CLASS_NAME = "分类名称\n同时也是分类参照的文件名\n不能包含特殊字符"
ANNOTATION_ADD_OBJECT = "分类中的具体对象\n下拉列表仅显示尚未分类的对象, 也可直接输入\n保存后显示在该分类的对象列表中"

ANNOTATION_MODIFY_CLASS_OK = "修改数据并保存"
ANNOTATION_MODIFY_CLASS_CANCEL = "什么都不做"
ANNOTATION_MODIFY_CLASS_DELETE = "删除该分类"

ANNOTATION_SHA = """Mod 压缩包的文件散列值（哈希值）
使用 SHA-1 算法并被用作为 Mod 的唯一标识符"""

ANNOTATION_OBJECT = "标识 Mod 所作用的对象\n* 必要"

ANNOTATION_NAME = "标识 Mod 的名称\n用于标记和区分同作用对象的 Mod\n* 必要"

ANNOTATION_AUTHOR = "标识 Mod 的作者"

ANNOTATION_GRADING = """标识年龄分级
G - 表示大众级 : 没有不适宜或可以被大众所接受的内容
P - 表示指导级 : 带有不适宜、性暗示或诱惑的内容
R - 表示成人级 : 带有性、暴力、血腥、恐怖或令人感到不适的内容
* 必要"""

ANNOTATION_EXPLAIN = "对 Mod 的额外描述内容"

ANNOTATION_TAGS = """描述该 Mod 所包含的内容标签
使用空格分隔多个 标签"""

ANNOTATION_ADD_MOD_OK = "确认导入该 Mod"

ANNOTATION_ADD_MODS_SHA_BATCH = """批量编辑模式
对输入框的修改会同时应用到所有选中的任务"""
ANNOTATION_ADD_MODS_SURE = "导入所有选中的任务\n未就绪或有错误的任务会被跳过"
ANNOTATION_ADD_MODS_CANCEL = "取消所有选中的任务"
ANNOTATION_ADD_MODS_SELECT_ALL = "选中队列中的所有任务\n选中多个任务时进入批量编辑模式"

ANNOTATION_MODIFY_ITEM_OK = "修改数据并保存"
ANNOTATION_MODIFY_ITEM_CANCEL = "什么都不做"
ANNOTATION_MODIFY_ITEM_DELETE = "删除 Mod 文件、解压缓存和索引数据"
