# TH-Suite 测试指南

本文档提供TH-Suite项目的完整测试策略和实施指南。

## 目录

- [测试策略](#测试策略)
- [测试工具链](#测试工具链)
- [测试类型](#测试类型)
- [运行测试](#运行测试)
- [编写测试](#编写测试)
- [测试覆盖率](#测试覆盖率)
- [CI/CD集成](#cicd集成)
- [最佳实践](#最佳实践)

## 测试策略

### 测试金字塔

```
         /\
        /E2E\      <- 少量高价值测试
       /------\
      /集成测试 \   <- 适度覆盖
     /----------\
    /  单元测试   \ <- 大量快速测试
   /--------------\
```

### 覆盖率目标

- **整体覆盖率**: ≥ 70%
- **核心业务逻辑**: ≥ 90%
- **前端组件**: ≥ 75%
- **Rust代码**: ≥ 70%
- **Python后端**: ≥ 80%

## 测试工具链

### 前端测试

- **单元测试**: Vitest + Testing Library
- **E2E测试**: Playwright
- **组件测试**: @testing-library/react
- **Mock工具**: MSW (Mock Service Worker)
- **覆盖率**: c8/v8

### Rust测试

- **单元测试**: 内置 `cargo test`
- **集成测试**: `cargo test --test`
- **基准测试**: Criterion
- **覆盖率**: Tarpaulin
- **Mock工具**: Mockall

### 代码质量

- **ESLint**: 代码质量检查
- **Clippy**: Rust代码检查
- **Prettier**: 代码格式化
- **SonarQube**: 代码质量分析

## 测试类型

### 1. 单元测试

#### 前端组件测试

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MyComponent } from './MyComponent'

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent title="Test" />)
    expect(screen.getByText('Test')).toBeInTheDocument()
  })

  it('should handle click events', () => {
    const mockClick = vi.fn()
    render(<MyComponent onClick={mockClick} />)
    
    fireEvent.click(screen.getByRole('button'))
    expect(mockClick).toHaveBeenCalledOnce()
  })
})
```

#### Rust单元测试

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_function_behavior() {
        let result = my_function(42);
        assert_eq!(result, expected_value);
    }

    #[tokio::test]
    async fn test_async_function() {
        let result = async_function().await;
        assert!(result.is_ok());
    }
}
```

### 2. 集成测试

```typescript
describe('API Integration', () => {
  it('should handle complete workflow', async () => {
    // 设置测试数据
    const testProject = createTestProject()
    
    // 执行完整流程
    const response = await api.createProject(testProject)
    expect(response.success).toBe(true)
    
    const project = await api.getProject(response.data.id)
    expect(project.name).toBe(testProject.name)
  })
})
```

### 3. E2E测试

```typescript
test('complete user workflow', async ({ page }) => {
  // 用户登录
  await page.goto('/login')
  await page.fill('[name="username"]', 'testuser')
  await page.fill('[name="password"]', 'password')
  await page.click('button[type="submit"]')

  // 创建项目
  await page.goto('/projects')
  await page.click('text="新建项目"')
  await page.fill('[name="projectName"]', 'Test Project')
  await page.click('button[type="submit"]')

  // 验证项目创建成功
  await expect(page.locator('text="Test Project"')).toBeVisible()
})
```

## 运行测试

### 前端测试

```bash
# 单元测试
npm run test

# 监听模式
npm run test:watch

# 覆盖率报告
npm run test:coverage

# E2E测试
npm run test:e2e

# 测试UI界面
npm run test:ui
```

### Rust测试

```bash
# 单元测试
cargo test

# 集成测试
cargo test --test integration_test

# 基准测试
cargo bench

# 覆盖率报告
cargo tarpaulin --out Html
```

### 完整测试套件

```bash
# 运行所有测试
npm run test:all

# CI环境测试
npm run test:ci
```

## 编写测试

### 测试命名规范

- **描述性命名**: 测试名应清楚描述测试内容
- **Given-When-Then**: 使用此模式组织测试
- **中文测试名**: 允许使用中文描述测试场景

```typescript
describe('项目管理功能', () => {
  it('当用户点击创建按钮时，应该显示创建项目对话框', () => {
    // Given: 用户在项目页面
    // When: 点击创建按钮
    // Then: 显示对话框
  })
})
```

### 测试数据管理

```typescript
// 测试工厂函数
export const createTestProject = (overrides = {}) => ({
  id: '1',
  name: 'Test Project',
  type: 'mod',
  path: '/test/path',
  ...overrides,
})

// 测试夹具
export const testFixtures = {
  validProject: createTestProject(),
  invalidProject: createTestProject({ name: '' }),
  largeProject: createTestProject({ 
    files: Array.from({ length: 1000 }, (_, i) => `file${i}.json`)
  }),
}
```

### Mock策略

```typescript
// API Mock
vi.mock('@/services/api', () => ({
  ProjectService: {
    getProjects: vi.fn(() => Promise.resolve([])),
    createProject: vi.fn((project) => 
      Promise.resolve({ id: '1', ...project })
    ),
  },
}))

// Tauri Mock
vi.mock('@tauri-apps/api/tauri', () => ({
  invoke: vi.fn((command, args) => {
    switch (command) {
      case 'get_projects':
        return Promise.resolve([])
      default:
        return Promise.resolve(null)
    }
  }),
}))
```

## 测试覆盖率

### 配置覆盖率阈值

```javascript
// vitest.config.ts
export default defineConfig({
  test: {
    coverage: {
      thresholds: {
        global: {
          branches: 75,
          functions: 80,
          lines: 80,
          statements: 80,
        },
        'src/services/': {
          branches: 85,
          functions: 90,
          lines: 90,
          statements: 90,
        },
      },
    },
  },
})
```

### 覆盖率报告

- **HTML报告**: `coverage/index.html`
- **LCOV报告**: `coverage/lcov.info`
- **JSON报告**: `coverage/coverage.json`
- **文本报告**: 控制台输出

## CI/CD集成

### GitHub Actions配置

测试在以下情况下自动运行：

- **Pull Request**: 所有测试套件
- **Push到main**: 完整测试+部署
- **定时任务**: 每日完整测试

### 质量门禁

- **测试通过率**: 100%
- **覆盖率**: 满足阈值要求
- **性能测试**: 不超过基准线
- **安全扫描**: 无高危漏洞

## 最佳实践

### 1. 测试隔离

```typescript
describe('UserService', () => {
  beforeEach(() => {
    // 每个测试前重置状态
    vi.clearAllMocks()
    resetTestDatabase()
  })

  afterEach(() => {
    // 清理测试数据
    cleanupTestData()
  })
})
```

### 2. 异步测试

```typescript
it('should handle async operations', async () => {
  const promise = asyncFunction()
  
  // 等待Promise解决
  await expect(promise).resolves.toBe(expectedValue)
  
  // 或者捕获错误
  await expect(promise).rejects.toThrow('Error message')
})
```

### 3. 参数化测试

```typescript
describe.each([
  { input: 'valid@email.com', expected: true },
  { input: 'invalid-email', expected: false },
  { input: '', expected: false },
])('email validation with $input', ({ input, expected }) => {
  it(`should return ${expected}`, () => {
    expect(validateEmail(input)).toBe(expected)
  })
})
```

### 4. 测试组织

```typescript
describe('ProjectService', () => {
  describe('创建项目', () => {
    it('should create valid project', () => {})
    it('should reject invalid data', () => {})
  })

  describe('查询项目', () => {
    it('should return existing projects', () => {})
    it('should handle empty results', () => {})
  })
})
```

### 5. 性能测试

```typescript
it('should perform within time limit', async () => {
  const startTime = performance.now()
  
  await heavyOperation()
  
  const duration = performance.now() - startTime
  expect(duration).toBeLessThan(1000) // 1秒内完成
})
```

## 调试测试

### Vitest调试

```bash
# 调试特定测试
npm run test -- --reporter=verbose MyComponent.test.tsx

# 仅运行失败的测试
npm run test -- --run --reporter=verbose --bail=1
```

### Playwright调试

```bash
# 头部模式运行
npm run test:e2e -- --headed

# 调试模式
npm run test:e2e -- --debug

# 生成测试代码
npx playwright codegen localhost:3000
```

## 测试维护

### 定期任务

1. **更新依赖**: 保持测试工具最新
2. **清理过时测试**: 删除不再相关的测试
3. **重构测试**: 保持测试代码质量
4. **性能优化**: 提高测试执行速度

### 监控指标

- **测试执行时间**: < 5分钟
- **测试稳定性**: 通过率 > 95%
- **维护成本**: 测试代码与生产代码比例 < 1:2

## 故障排除

### 常见问题

1. **测试超时**: 增加超时时间或优化测试
2. **Mock失效**: 检查Mock配置和路径
3. **异步问题**: 正确使用await和Promise
4. **内存泄漏**: 清理测试数据和事件监听器

### 支持资源

- [Vitest文档](https://vitest.dev/)
- [Playwright文档](https://playwright.dev/)
- [Testing Library文档](https://testing-library.com/)
- [项目内部测试示例](../examples/testing/)

---

## 贡献指南

编写测试时请遵循以下原则：

1. **测试优先**: 先写测试，再写实现
2. **简单明确**: 每个测试只验证一个行为
3. **独立性**: 测试之间不应有依赖关系
4. **可维护性**: 测试代码也需要重构和优化
5. **文档化**: 复杂测试需要注释说明

通过遵循这些实践，我们可以确保TH-Suite的高质量和可靠性。