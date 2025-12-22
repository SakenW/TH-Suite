# TransHub Suite 国际化 (i18n) 结构

## 目录结构

```
TransHub Suite/
├── locales/                    # 全局通用翻译
│   ├── en/
│   │   └── common.json         # 英文通用翻译
│   └── zh-CN/
│       └── common.json         # 中文通用翻译
└── apps/
    ├── mc-l10n/
    │   └── frontend/
    │       └── src/
    │           └── locales/    # TH Suite MC L10n 专用翻译
    │               ├── en/
    │               │   └── mc-l10n.json
    │               └── zh-CN/
    │                   └── mc-l10n.json
    └── rw-studio/
        └── frontend/
            └── src/
                └── locales/    # RW Studio 专用翻译
                    ├── en/
                    │   └── rw-studio.json
                    └── zh-CN/
                        └── rw-studio.json
```

## 设计原则

1. **通用性优先**：将所有应用都可能用到的翻译放在 `locales/` 目录下
   - 基础 UI 操作（保存、取消、确认等）
   - 文件操作（上传、下载、拖拽等）
   - 工作流状态（扫描、提取、翻译等）
   - 设置相关（源语言、目标语言、自动化等）
   - 通用消息（错误、成功、网络等）

2. **应用专用**：只有特定应用才需要的翻译放在各自的 `locales/` 目录下
   - 应用特有的功能名称
   - 特定领域的术语
   - 应用独有的工作流程

3. **命名空间分离**：使用不同的命名空间避免冲突
4. **类型安全**：提供 TypeScript 类型定义确保翻译键的正确性
5. **功能复用**：程序功能相关的翻译优先提取到通用翻译中

### 1. 通用翻译 (Global Common)
位置：`/locales/`

包含所有应用共享的翻译内容：
- 基础 UI 操作（保存、取消、确认等）
- 通用状态（加载中、成功、失败等）
- 通用导航（首页、设置、帮助等）
- 通用交互（拖拽、上传、下载等）

### 2. 应用专用翻译 (App-Specific)
位置：`/apps/{app-name}/frontend/src/locales/`

包含特定应用的翻译内容：
- 应用特有的功能描述
- 专业术语和概念
- 应用特定的工作流程
- 应用独有的设置项

## 使用方式

### 在 React 组件中使用

```typescript
import { useCommonTranslation, useMcStudioTranslation } from '../hooks/useTranslation';

function MyComponent() {
  const { t: tCommon } = useCommonTranslation();
  const { t: tMc } = useMcStudioTranslation();

  return (
    <div>
      <button>{tCommon('actions.save')}</button>
      <h1>{tMc('mcStudio.title')}</h1>
    </div>
  );
}
```

### 命名空间

- `common`: 通用翻译
- `mcStudio`: TH Suite MC L10n 专用翻译
- `rwStudio`: RW Studio 专用翻译

## 开发工具

项目配置了 i18n-ally 插件，支持：
- 可视化翻译管理
- 翻译键的自动补全
- 缺失翻译的检测
- 多语言文件的同步编辑

## 添加新语言

1. 在 `/locales/` 下创建新的语言目录（如 `ja/`）
2. 在各应用的 `locales/` 目录下创建对应的语言目录
3. 复制现有的 JSON 文件并翻译内容
4. 更新 i18n 配置文件中的语言列表
