# d3dxSkinManagePro

## 简介

3DMigoto Mods 管理工具，基于 [numlinka/d3dxSkinManage](https://d3dxskinmanage.numlinka.com/) v1.5.6 修改。

本分支为**纯本地运行**版本：已移除启动自动更新、在线 Mod 仓库与下载功能，不再依赖网络。

原版的插件机制也已移除（不再有 `plugins` 目录），常用插件的功能已直接内置到程序中。

## 主要改动

- **多用户管理**：登录界面可直接创建用户（用户名、描述、头像、游戏路径，可从已有用户复制分类配置），支持注销返回登录界面。
- **对接 XXMI Launcher**：不再内置 3DMigoto 版本压缩包，改为将 [XXMI Launcher](https://github.com/SpectrumQT/XXMI-Launcher) 对应导入器（GIMI / SRMI / ZZMI / WWMI / HIMI / EFMI）的目录指向当前用户的 `work` 目录，由其负责 3DMigoto 的下载、更新与注入启动。
- **高 DPI 适配**：适配 4K 等高缩放比例屏幕，行高、列宽、缩略图按系统 DPI 自动换算。
- **分类管理增强**：分类支持添加、置顶 / 上移 / 下移 / 置底、重命名、删除；对象支持排序、移出分类。
- **Mod 状态着色**：选择列表中正在使用的 Mod 显示为绿色，仅存在解压缓存的 Mod 显示为黄色。
- **Mod 右键菜单**：修改 Mod 信息、编辑 Mod 切换键、查看 / 删除缓存文件、查看原始文件、应用到原始文件、使用脚本修复 Mod；分类 / 对象右键可卸载本分类或全部 Mods。
- **编辑 Mod 切换键**（移植自黎愔的 modify_key_swap 插件）：
  - 合并 Mod（解压缓存的 ini 中含 `[Key*]` 节）可在右键菜单中编辑初始 Mod 值、循环索引列表以及 `key` / `back` 切换按键，保存时校验按键格式并保留 ini 原有编码；
  - 鼠标悬浮在合并 Mod 上时，提示框中会列出它的切换键。
- **预览图增强**：
  - 左键预览区域全屏查看，单击或 `Esc` 关闭；
  - 右键预览区域将剪贴板图片设为预览图；
  - 拖入图片设置预览图，支持 `.png` / `.jpg` / `.jpeg` / `.bmp` / `.gif` / `.webp`，非 png/jpg 自动转换；
  - 替换已有预览图前会提示是否覆盖，并自动清理旧文件。
- **Mod 修复**：可在 Mod 的解压缓存中运行修复脚本，修复满意后通过「应用到原始文件」写回，详见 [Mod 修复](#mod-修复)。
- **工具页**：强迫症预览图裁剪、缓存清理（扫描并清理已无用的解压缓存与残留临时文件）、可选标签编辑。
- **主题化右键菜单**：右键菜单跟随 ttkbootstrap 主题样式。
- **内置使用帮助**：「关于」页面替换为完整的使用说明。
- **一键打包**：提供 `buildtools/build.bat`，自动创建虚拟环境、安装依赖并用 PyInstaller 打包。

## 运行

### 运行环境

```
Python 3.10+
Windows 10+
```

### 依赖库

```
pillow
pywin32
ttkbootstrap>=2.2.7
windnd
pygetwindow
pynput
```

安装：

```
pip install -r requirements.txt
```

### 运行

```
python ./src/d3dxSkinManagePro.py
```

> 导入与加载 Mod 依赖 7-Zip，请确保 `local/7zip/7z.exe`（及 `7z.dll`）存在。

## 打包

双击运行 `buildtools/build.bat`，或在命令行中执行：

```
buildtools\build.bat [onedir] [nopause]
```

| 参数      | 说明                                        |
| --------- | ------------------------------------------- |
| `onedir`  | 生成目录版（启动更快），默认生成单文件 exe  |
| `nopause` | 结束时不暂停                                |

脚本流程：

1. 检查 Python 3.10+；
2. 在项目根目录创建 `.venv` 虚拟环境；
3. 安装 `requirements.txt` 与 PyInstaller，并通过 `buildtools/check_imports.py` 检查 `src` 中的第三方模块是否均已安装；
4. PyInstaller 打包（若存在 `local/iconbitmap.ico` 则作为程序图标）；
5. 复制 `local/7zip` 与图标等运行组件。

输出目录：`dist/d3dxSkinManagePro/`

## 快速上手

> 前置条件：先安装 [XXMI Launcher](https://github.com/SpectrumQT/XXMI-Launcher)，3DMigoto 本体由它负责下载与更新。

1. 在登录界面创建或选择一个用户并登录（每个用户的数据相互独立）。
2. 进入「环境设置」，点击「选择 XXMI 目录」，选择模组导入器，并通过「文件选择工具」选择游戏主程序。
3. 点击「启动 XXMI Launcher」，在其中完成 3DMigoto 的安装 / 更新（会部署到当前用户的 `work` 目录）。
4. 回到「Mods 管理」，在分类列表右键「添加分类」，在对象列表右键「添加对象」。
5. 将 Mod 压缩包（`.zip` / `.rar` / `.7z`）、单个 `.ini` 文件或文件夹拖入主窗口，填写 Mod 信息后确定。
6. 在「选择」列表中双击 Mod 即可加载；选中 Mod 后拖入图片可设置预览图；合并 Mod 可右键「编辑 Mod 切换键」修改切换按键。
7. 点击「启动游戏」，由 XXMI Launcher 注入并启动游戏。

更详细的说明见程序内「关于」页面。

## 原版 d3dxSkinManage 用户使用指引

本程序与原版 d3dxSkinManage（v1.5.x）的数据目录与文件格式兼容，**无需导入或转换**，直接复制到原版根目录即可使用：

1. **备份**：先备份原版根目录下的 `home` 与 `resources` 文件夹（以防万一）。
2. **复制**：从 [Releases](https://github.com/hkway168/d3dxSkinManagePro/releases) 下载 `d3dxSkinManagePro-vX.X.X-win64.zip`，将压缩包内 `d3dxSkinManagePro` 文件夹中的**全部内容**（`d3dxSkinManagePro.exe` 与 `local` 文件夹）复制到原版根目录（即 `d3dxSkinManage.exe` 所在目录），提示同名文件时选择覆盖（仅为 `local/7zip` 与 `local/iconbitmap.ico`）。
3. **启动**：双击 `d3dxSkinManagePro.exe`，登录界面会列出原有的全部用户，登录后分类、对象、Mod、预览图、缩略图与已加载状态均与原版一致。
4. **对接 XXMI Launcher**：本程序不再使用原版的 3DMigoto 版本选择，登录后进入「环境设置」，按 [快速上手](#快速上手) 第 2、3 步选择 XXMI 目录与模组导入器，再在 XXMI Launcher 中安装 / 更新 3DMigoto（会部署到该用户原有的 `work` 目录，`work/Mods` 中已加载的 Mod 不受影响）。每个用户都需单独设置一次。

复制后的目录结构示意：

```
原版根目录\
├── d3dxSkinManage.exe       // 原版主程序 (保留, 可与新版并存)
├── d3dxSkinManagePro.exe    // 新版主程序 (新增)
├── home\                    // 原有用户数据 (直接沿用)
├── resources\               // 原有 Mod 与图片资源 (直接沿用)
├── local\                   // 7zip 与图标 (覆盖), configuration (沿用)
└── plugins\                 // 原版插件 (新版不再读取, 可保留)
```

注意事项：

- 两个程序共用同一份数据，可以并存，但**请勿同时运行**，以免索引与配置互相覆盖。
- 原版的 `plugins` 目录、`resources/3dmigoto`（3DMigoto 版本压缩包）、`resources/preview_screen` 等新版不再使用，保留或删除均可；确认不再使用原版后可自行删除以释放空间。
- 原版 `work` 目录中由原版解压的 3DMigoto 文件（`d3dx.ini`、`d3d11.dll` 等）会在 XXMI Launcher 安装 / 更新时被替换，若对 `d3dx.ini` 做过自定义修改，请提前备份。
- 新版会在 `local/configuration` 和用户 `configuration` 中追加少量新字段（如 XXMI 目录、导入器），并新增 `home/<用户名>/classification_order.json` 记录分类顺序，原版会忽略这些内容。
- 新版要求一个对象只属于一个分类，若原版中同一对象出现在多个分类里，首次登录时会只保留在排序靠前的分类中（会写回分类文件）。
- 新版特有的数据（如单个 `.ini` 形式导入的 Mod）原版无法识别，回到原版使用时这些 Mod 可能无法加载。

## Mod 修复

将修复脚本（`.py` 或 `.exe`）放入 `fixtool` 目录，然后：

- **修复单个 Mod**：Mod 右键「使用脚本修复Mod」，在该 Mod 的解压缓存目录中运行（需先加载过一次）；
- **修复所有 Mod**：分类 / 对象右键「使用脚本修复所有Mod」，在 `work/Mods` 中运行。

脚本只修改解压缓存，原始文件不受影响，删除缓存后重新加载即可还原。修复满意后，可通过 Mod 右键「应用到原始文件」重新打包替换原始文件（SHA 会改变，旧文件备份到 `resources/backup`）。

> 运行 `.py` 脚本需要 Python，找不到时可在 `local/configuration` 中设置 `fixtool_python` 为 `python.exe` 路径。

## 工作方式

将 Mod 压缩包以其 SHA1 值命名储存在 `./resources/mods` 中，并使用索引文件记录 Mod 文件的相关信息。

在加载 Mod 时将压缩包释放到对应用户 3DMigoto 工作目录的 Mods 文件夹（`home/<用户名>/work/Mods`），该工作目录同时作为 XXMI Launcher 的导入器目录。

单个 `.ini` 文件形式的 Mod 同样以 SHA1 命名直接储存，加载时无需解压，会被复制到 `home/<用户名>/work/Mods/<SHA1>/` 下。

[文件结构](doc/file-structure.md)

## 许可证

[GPL-3.0](LICENSE)
