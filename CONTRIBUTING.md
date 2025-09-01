# 贡献指南

感谢你对 TransHub Suite 项目的关注！TransHub Suite (TransHub Suite) 是一个现代化的游戏本地化工具套件，我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复或新功能
- 🧪 编写测试
- 🎨 改进 UI/UX 设计
- 🌐 翻译引擎集成
- 📝 语言文件解析器

## 📋 开始之前

在开始贡献之前，请确保你已经：

1. 阅读了项目的 [README.md](README.md)
2. 了解了项目的架构和技术栈
3. 设置了本地开发环境

## 🚀 设置开发环境

### 环境要求

- Python 3.9+
- Node.js 18+
- Rust 1.70+
- Poetry
- pnpm
- Task（推荐）

### 安装步骤

1. **Fork 并克隆仓库**
   ```bash
   git clone https://github.com/your-username/TransHub Suite.git
   cd TransHub Suite
   ```

2. **安装依赖**
   ```bash
   task install
   ```

3. **配置环境**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入必要的配置
   ```

4. **运行测试**
   ```bash
   task test
   ```

5. **启动开发服务器**
   ```bash
   task dev
   ```

## 🐛 报告 Bug

在报告 Bug 之前，请先检查 [现有的 Issues](https://github.com/your-username/TransHub Suite/issues) 确保问题尚未被报告。

### Bug 报告模板

```markdown
**Bug 描述**
简洁明了地描述这个 Bug。

**复现步骤**
1. 进入 '...'
2. 点击 '....'
3. 滚动到 '....'
4. 看到错误

**期望行为**
描述你期望发生的行为。

**实际行为**
描述实际发生的行为。

**截图**
如果适用，添加截图来帮助解释你的问题。

**环境信息**
- 操作系统: [例如 Windows 11, macOS 13, Ubuntu 22.04]
- Python 版本: [例如 3.9.7]
- Node.js 版本: [例如 18.17.0]
- 应用版本: [例如 1.0.0]

**附加信息**
添加任何其他关于问题的信息。
```

## 💡 功能建议

我们欢迎新功能建议！请在提交建议前考虑以下几点：

- 功能是否符合本地化工具的项目目标
- 功能是否对翻译工作流程有帮助
- 功能的实现复杂度

### 功能建议模板

```markdown
**功能描述**
简洁明了地描述你想要的功能。

**问题背景**
描述这个功能要解决的问题。

**解决方案**
描述你希望的解决方案。

**替代方案**
描述你考虑过的其他替代解决方案。

**附加信息**
添加任何其他关于功能请求的信息或截图。
```

## 🔧 代码贡献

### 分支策略

- `main`: 主分支，包含稳定的生产代码
- `develop`: 开发分支，包含最新的开发代码
- `feature/*`: 功能分支，用于开发新功能
- `bugfix/*`: 修复分支，用于修复 Bug
- `hotfix/*`: 热修复分支，用于紧急修复

### 提交流程

1. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b bugfix/your-bugfix-name
   ```

2. **进行开发**
   - 遵循代码规范
   - 编写测试
   - 更新文档

3. **运行测试和检查**
   ```bash
   task test
   task lint
   task format
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 模板
   - 等待代码审查

### 提交信息规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**类型 (type):**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式化（不影响代码运行的变动）
- `refactor`: 重构（既不是新增功能，也不是修改 Bug 的代码变动）
- `perf`: 性能优化
- `test`: 增加测试
- `chore`: 构建过程或辅助工具的变动
- `ci`: CI 配置文件和脚本的变动

**示例:**
```
feat(mc-l10n): add mod auto-update feature
fix(rw-studio): resolve save file corruption issue
docs: update installation guide
test(core): add unit tests for parser module
```

## 📝 代码规范

### Python 代码规范

- 使用 [PEP 8](https://pep8.org/) 代码风格
- 使用 [Black](https://black.readthedocs.io/) 进行代码格式化
- 使用 [isort](https://isort.readthedocs.io/) 进行导入排序
- 使用 [Ruff](https://docs.astral.sh/ruff/) 进行代码检查
- 使用 [MyPy](https://mypy.readthedocs.io/) 进行类型检查

```bash
# 格式化代码
task format:python

# 检查代码
task lint:python
```

### TypeScript/JavaScript 代码规范

- 使用 [ESLint](https://eslint.org/) 进行代码检查
- 使用 [Prettier](https://prettier.io/) 进行代码格式化
- 使用 TypeScript 严格模式

```bash
# 格式化代码
task format:frontend

# 检查代码
task lint:frontend
```

### 命名规范

**Python:**
- 变量和函数: `snake_case`
- 类: `PascalCase`
- 常量: `UPPER_SNAKE_CASE`
- 私有成员: `_leading_underscore`

**TypeScript:**
- 变量和函数: `camelCase`
- 类和接口: `PascalCase`
- 常量: `UPPER_SNAKE_CASE`
- 类型: `PascalCase`

**文件命名:**
- Python 文件: `snake_case.py`
- TypeScript 文件: `camelCase.ts` 或 `PascalCase.tsx`
- 配置文件: `kebab-case.json`

## 🧪 测试指南

### 测试类型

1. **单元测试**: 测试单个函数或类
2. **集成测试**: 测试多个组件的交互
3. **端到端测试**: 测试完整的用户流程
4. **黄金测试**: 测试特定游戏场景

### 编写测试

**Python 测试 (pytest):**
```python
import pytest
from your_module import your_function

def test_your_function():
    # Arrange
    input_data = "test input"
    expected_output = "expected output"
    
    # Act
    result = your_function(input_data)
    
    # Assert
    assert result == expected_output

@pytest.mark.asyncio
async def test_async_function():
    result = await your_async_function()
    assert result is not None
```

**TypeScript 测试 (Vitest):**
```typescript
import { describe, it, expect } from 'vitest';
import { yourFunction } from './yourModule';

describe('yourFunction', () => {
  it('should return expected output', () => {
    // Arrange
    const input = 'test input';
    const expectedOutput = 'expected output';
    
    // Act
    const result = yourFunction(input);
    
    // Assert
    expect(result).toBe(expectedOutput);
  });
});
```

### 运行测试

```bash
# 运行所有测试
task test

# 运行特定测试
task test:python
task test:frontend
task test:mc
task test:rw

# 运行测试并生成覆盖率报告
poetry run pytest --cov=apps --cov-report=html
```

## 📚 文档贡献

### 文档类型

- **API 文档**: 自动生成，通过代码注释维护
- **用户文档**: 面向最终用户的使用指南
- **开发文档**: 面向开发者的技术文档
- **架构文档**: 系统设计和架构说明

### 文档规范

- 使用 Markdown 格式
- 包含代码示例
- 保持简洁明了
- 及时更新

## 🎨 UI/UX 贡献

### 设计原则

- **简洁性**: 界面简洁，功能明确
- **一致性**: 保持设计风格一致
- **可访问性**: 支持无障碍访问
- **响应式**: 适配不同屏幕尺寸

### 设计工具

- **Figma**: 界面设计和原型
- **Tailwind CSS**: CSS 框架
- **Heroicons**: 图标库

## 🔍 代码审查

### 审查清单

**功能性:**
- [ ] 代码实现了预期功能
- [ ] 边界情况得到处理
- [ ] 错误处理适当

**代码质量:**
- [ ] 代码清晰易读
- [ ] 遵循项目规范
- [ ] 没有重复代码
- [ ] 性能考虑适当

**测试:**
- [ ] 包含适当的测试
- [ ] 测试覆盖率足够
- [ ] 测试通过

**文档:**
- [ ] 代码有适当注释
- [ ] API 文档更新
- [ ] 用户文档更新

### 审查流程

1. **自动检查**: CI/CD 流水线自动运行测试和检查
2. **人工审查**: 至少一名维护者审查代码
3. **讨论**: 通过 PR 评论进行讨论
4. **修改**: 根据反馈修改代码
5. **合并**: 审查通过后合并到主分支

## 🏷️ 发布流程

### 版本号规范

我们使用 [语义化版本](https://semver.org/) (SemVer):

- `MAJOR.MINOR.PATCH`
- `MAJOR`: 不兼容的 API 修改
- `MINOR`: 向下兼容的功能性新增
- `PATCH`: 向下兼容的问题修正

### 发布步骤

1. **更新版本号**
2. **更新 CHANGELOG**
3. **创建 Release Tag**
4. **构建和测试**
5. **发布到各平台**

## 📞 获取帮助

如果你在贡献过程中遇到问题，可以通过以下方式获取帮助：

- **GitHub Issues**: 报告问题或提出疑问
- **GitHub Discussions**: 参与社区讨论
- **Discord**: 加入我们的 Discord 服务器（如果有）
- **Email**: 直接联系维护者

## 🙏 致谢

感谢所有为 TransHub Suite 项目做出贡献的开发者！你们的贡献让这个项目变得更好。

---

再次感谢你对 TransHub Suite 项目的关注和贡献！🎉
