```
\
├── home                        // 用户数据，每个用户独立
│   └── <用户名>
│       ├── classification          // 分类配置
│       ├── modsIndex               // Mod 索引
│       ├── work                    // 3DMigoto 工作目录 (XXMI Launcher 导入器目录)
│       │   └── Mods                    // 已加载的 Mod
│       ├── thumbnail               // 用户级缩略图 (可选, 与 resources/thumbnail 叠加, 同名优先; 文件名即名称)
│       ├── configuration           // 用户配置
│       ├── classification_order.json // 分类顺序
│       ├── choices_sort.json       // 选择列表排序设置、置顶 Mod 与最近使用记录
│       ├── modtags                 // 可选标签
│       ├── description.txt         // 用户描述
│       └── picture.png             // 用户头像
│
├── local                       // 程序资源与全局配置
│   ├── 7zip                        // 7z.exe / 7z.dll
│   ├── configuration               // 全局配置
│   └── iconbitmap.ico              // 程序图标
│
├── resources                   // 共享资源
│   ├── mods                        // Mod 原始文件 (SHA-1 命名)
│   ├── preview                     // 预览图
│   ├── thumbnail                   // 分类与对象缩略图 (含子目录, 文件名即名称, 不支持 _redirection.ini)
│   ├── backup                      // 「应用到原始文件」的旧文件备份
│   └── cache                       // 临时文件
│
├── fixtool                     // Mod 修复脚本
├── logs                        // 运行日志
└── d3dxSkinManagePro.exe       // 主程序
```
