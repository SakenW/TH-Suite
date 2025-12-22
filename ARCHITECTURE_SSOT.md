# TransHub Suite 架构设计与开发指南 (SSOT)

本文档作为 TransHub Suite 开发的**唯一事实来源 (Single Source of Truth)**。所有开发活动、目录结构调整与技术选型均需以此为准。

---

## 1. 核心设计理念

1.  **以“项目 (Project)”为主导**：
    *   仓库组织以项目（如 `minecraft`, `factorio`）为顶层分类，而非功能层（UI/Web）。
    *   每个项目下包含多个**产品 (Product)**（如 `game-desktop`, `web-desktop`）。
2.  **产品独立打包**：
    *   每个产品（`products/*`）都是一个独立的构建目标。
    *   **Windows**: 输出独立的 `.exe`（或便携包）。
    *   **macOS**: 预留输出 `.app` / `.dmg`。
3.  **最小闭环优先 (MVP)**：
    *   首要目标：实现 `minecraft` 项目下的 `game-desktop` 产品。
    *   核心链路：**扫描 (Scan) → 上传/翻译 (Upload) → 导出/还原 (Restore)**。
4.  **数据安全与防污染**：
    *   **加密**: 必须使用 **SQLCipher** 对本地数据库进行加密。
    *   **防篡改**: 通过 `install_id` 绑定与完整性校验，防止用户随意替换或污染数据库。
5.  **单文件/便携式分发**：
    *   **Windows**: 纯便携模式。运行时在同级目录生成 `data/`, `config/`, `logs/`。
    *   **macOS**: 支持便携模式与标准路径（`~/Library/Application Support/`）两套策略。

---

## 2. 目录结构 (Monorepo)

采用 `pnpm workspace` + `turbo` 管理的多包架构。

```text
transhub-suite/
├── package.json
├── pnpm-workspace.yaml
├── turbo.json
├── README.md
│
├── tools/                          # 构建与辅助工具
│   ├── scripts/                    # 构建、发布、代码生成脚本
│   │   ├── gen-openapi-client.mjs
│   │   ├── dev-cert.mjs
│   │   └── release.mjs
│   └── templates/                  # 脚手架模板
│       └── product-tauri-react/    # 标准 Tauri+React 产品模板
│
├── shared/                         # 共享库（跨项目复用）
│   ├── api-client/                 # Trans-Hub API Client (OpenAPI 生成 + 封装)
│   ├── core/                       # 通用领域模型 (Job/Asset/Segment/ExportPlan)
│   ├── fs/                         # 文件系统抽象、跨平台路径、Watcher
│   ├── crypto/                     # 安全相关：SQLCipher 密钥管理、HMAC 校验
│   ├── presets/                    # 通用 Preset Schema (Zod 定义)
│   ├── ui/                         # 通用 UI 组件库 (Radix + shadcn/ui)
│   ├── telemetry/                  # 日志与埋点 (可选)
│   └── types/                      # 公共 TS 类型定义
│
└── packages/                       # 项目集合
    ├── minecraft/                  # [Project] Minecraft 产品线
    │   ├── project.json            # 项目元信息
    │   ├── presets/                # 项目级预设 (CurseForge, Modrinth 等)
    │   ├── adapters/               # 项目适配层 (核心业务逻辑)
    │   │   └── game/               # 游戏/整合包适配逻辑
    │   │       ├── scan/           # 扫描器
    │   │       ├── normalize/      # 数据标准化
    │   │       ├── restore/        # 还原逻辑
    │   │       └── paths/          # 路径策略 (Win/Mac 实现)
    │   │
    │   └── products/               # [Products] 独立发布单元
    │       ├── game-desktop/       # Minecraft 整合包翻译工具 (EXE)
    │       │   ├── product.json    # 产品配置 (BundleId 等)
    │       │   ├── src-tauri/      # Rust 后端
    │       │   └── ui/             # React 前端
    │       │
    │       └── web-desktop/        # Minecraft 网页翻译工具 (规划中)
    │           └── ...
    │
    └── [其他项目]/                  # 如 factorio, rimworld 等
        └── ...
```

---

## 3. 技术栈

### 3.1 核心栈
*   **Runtime**: Tauri (Rust)
*   **Frontend**: React + Vite + TypeScript
*   **UI Framework**: Tailwind CSS + Radix UI + shadcn/ui
*   **Package Manager**: pnpm + Turborepo

### 3.2 必需组件
1.  **TypeScript**: 全栈统一语言（Frontend + Shared）。
2.  **TanStack Query**: 管理异步状态（扫描/上传任务）、重试机制、缓存。
3.  **Zod**: 运行时 Schema 校验（Config, Preset, Job 数据）。
4.  **Zustand / Jotai**: 前端全局状态管理。
5.  **Rust Database**: `sqlx` 或 `rusqlite` + **SQLCipher**（加密）。
6.  **Keyring**: 系统级凭据管理（biolerplate/keyring 或 stronghold），用于存储数据库密钥。

---

## 4. 关键技术方案

### 4.1 数据库安全与防污染策略
目标：防止用户随意替换数据库文件，保证数据一致性。

1.  **初始化 (首次启动)**:
    *   生成 `install_id` (UUID) 写入 `config/product.toml`。
    *   生成 `db_key` (32 bytes 随机值)。
    *   将 `db_key` 存入操作系统凭据库 (Windows Credential Manager / macOS Keychain)。
    *   使用 `db_key` 创建加密的 SQLCipher 数据库 (`data/app.db`)。
    *   在数据库 `meta` 表中记录: `install_id`, `schema_version`。

2.  **运行时校验**:
    *   从 Keychain 读取 `db_key` 尝试解密数据库。
    *   **校验一致性**: 比对 `meta.install_id` 与 `config.install_id`。
        *   如果不匹配：拒绝启动或自动归档旧库并重建新库（防止“换库”操作）。
    *   **完整性检查**: 运行 `PRAGMA integrity_check` 确保文件未被篡改/损坏。

### 4.2 路径与分发策略
每个 `Adapter` 需实现路径策略接口。

*   **Windows (优先)**:
    *   **模式**: Portable (便携)。
    *   **行为**: 无论是 `.exe` 还是解压包，运行时在当前可执行文件同级目录下生成：
        *   `./data/` (数据库)
        *   `./config/` (配置文件)
        *   `./logs/` (日志)
*   **macOS (预留)**:
    *   **模式**: Hybrid (标准/便携)。
    *   **标准行为**: 写入 `~/Library/Application Support/<BundleId>/`。
    *   **便携行为**: 检测到特殊标记或位于非 `/Applications` 目录时，尝试在同级生成（需处理沙盒权限）。

---

## 5. 最小闭环 (MVP) - Minecraft Game Desktop

**目标**: 产出 `Minecraft Modpack Translator.exe`。

### 5.1 业务流程
1.  **选择目录**: 用户选择整合包根目录。
2.  **扫描 (Scan)**:
    *   `PackageAdapter` 根据 Preset (如 CurseForge) 扫描 `assets/**/lang/*.json`, `kubejs`, `ftbquests` 等文件。
3.  **标准化 (Normalize)**:
    *   解析文件，提取 Key-Value 对，生成统一的 `ScanJob`。
4.  **上传/翻译 (Upload)**:
    *   调用 Shared API Client 上传资源摘要/内容到 Trans-Hub。
    *   获取翻译结果。
5.  **导出 (Restore)**:
    *   将翻译内容还原为游戏可读格式（`.json`, `.snbt` 等）。
    *   写入原目录或指定输出目录。

### 5.2 开发路线图
1.  **搭建脚手架**: 初始化 Monorepo, Shared, Minecraft Package。
2.  **打通端到端**:
    *   实现 Tauri Shell。
    *   实现 Windows 便携路径逻辑。
    *   集成 SQLCipher 与 Keyring。
3.  **实现核心逻辑**: 仅支持 `assets` 目录下 JSON 文件的扫描与还原。
4.  **对接 API**: 完成登录、上传、下载链路。
5.  **打包交付**: 输出可运行的无关环境 EXE。

---
