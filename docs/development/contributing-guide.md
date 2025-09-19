# TH-Suite v2.0 开发者贡献指南

## 欢迎加入 TH-Suite 开发

感谢您对 TH-Suite 项目的关注！本指南将帮助您了解如何为项目做出贡献，无论是代码、文档、测试还是反馈建议。

## 项目概览

### 技术栈
- **后端**: Python 3.12+, FastAPI, SQLAlchemy, SQLCipher
- **前端**: React 18, TypeScript, Ant Design, Tauri
- **工具链**: Poetry, pnpm, Task, Ruff, Mypy
- **测试**: pytest, Jest, Playwright
- **CI/CD**: GitHub Actions

### 架构原则
- **Clean Architecture**: 六边形架构，领域驱动设计
- **Core-First**: 与 Trans-Hub Core 深度集成
- **Type Safety**: 全面的类型注解和检查
- **Test-Driven**: 高测试覆盖率和质量保证

## 开发环境搭建

### 环境要求
```bash
# 检查版本要求
python --version   # >= 3.12
node --version     # >= 18
pnpm --version     # >= 8
```

### 克隆和设置
```bash
# 克隆仓库
git clone https://github.com/trans-hub/th-suite.git
cd th-suite

# 安装依赖
task install

# 或手动安装
poetry install
cd apps/mc_l10n/frontend && pnpm install
```

### 开发工具配置

#### VS Code 推荐配置
创建 `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "typescript.preferences.importModuleSpecifier": "relative",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true,
    "source.fixAll.eslint": true
  }
}
```

推荐扩展:
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next"
  ]
}
```

#### PyCharm 配置
1. 导入项目，选择 Poetry 作为解释器
2. 启用 Ruff 和 Mypy 检查
3. 配置代码格式化为 Black
4. 设置导入排序为 isort

### 运行和测试
```bash
# 运行开发服务器
task dev:mc

# 运行测试
task test

# 代码质量检查
task lint
```

## 代码规范

### Python 编码规范

#### 基本原则
- 遵循 PEP 8 和 PEP 484 (类型注解)
- 使用 Python 3.12+ 新特性
- 所有公共函数必须有类型注解和文档字符串
- 优先使用 async/await 而非同步代码

#### 代码风格示例
```python
"""
模块文档字符串
简要描述模块功能和用途
"""
from typing import Dict, List, Optional, Protocol
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class TranslationEntry:
    """翻译条目数据模型
    
    Attributes:
        key: 翻译键，如 'item.mod_name.item_name'
        source_text: 源文本
        target_text: 目标翻译文本
        language: 目标语言代码
    """
    key: str
    source_text: str
    target_text: str
    language: str
    
    def validate(self) -> bool:
        """验证翻译条目的有效性
        
        Returns:
            bool: 条目是否有效
            
        Raises:
            ValueError: 当必填字段为空时
        """
        if not self.key or not self.source_text:
            raise ValueError("翻译键和源文本不能为空")
        return True


class TranslationRepository(Protocol):
    """翻译仓储接口定义"""
    
    async def save(self, entry: TranslationEntry) -> str:
        """保存翻译条目"""
        ...
    
    async def find_by_key(self, key: str) -> Optional[TranslationEntry]:
        """根据键查找翻译条目"""
        ...


class TranslationService:
    """翻译服务实现"""
    
    def __init__(self, repository: TranslationRepository) -> None:
        self._repository = repository
        self._logger = structlog.get_logger()
    
    async def create_translation(
        self, 
        key: str, 
        source_text: str, 
        target_text: str,
        language: str
    ) -> str:
        """创建新的翻译条目
        
        Args:
            key: 翻译键
            source_text: 源文本
            target_text: 翻译文本
            language: 目标语言
            
        Returns:
            str: 创建的条目ID
            
        Raises:
            ValueError: 当输入参数无效时
            TranslationExistsError: 当翻译条目已存在时
        """
        entry = TranslationEntry(
            key=key,
            source_text=source_text,
            target_text=target_text,
            language=language
        )
        
        # 验证条目
        entry.validate()
        
        # 检查是否已存在
        existing = await self._repository.find_by_key(key)
        if existing:
            raise TranslationExistsError(f"翻译条目已存在: {key}")
        
        # 保存条目
        entry_id = await self._repository.save(entry)
        
        self._logger.info(
            "翻译条目创建成功",
            entry_id=entry_id,
            key=key,
            language=language
        )
        
        return entry_id
```

#### 异常处理
```python
class TH_SuiteError(Exception):
    """TH-Suite 基础异常类"""
    pass


class TranslationError(TH_SuiteError):
    """翻译相关异常"""
    pass


class ScanError(TH_SuiteError):
    """扫描相关异常"""
    pass


# 使用示例
async def scan_project(project_path: Path) -> ScanResult:
    """扫描项目文件"""
    try:
        if not project_path.exists():
            raise ScanError(f"项目路径不存在: {project_path}")
        
        # 扫描逻辑
        return ScanResult(files=found_files)
        
    except PermissionError as e:
        logger.error("扫描权限不足", path=project_path, error=str(e))
        raise ScanError(f"无权限访问: {project_path}") from e
    except Exception as e:
        logger.exception("扫描过程发生未知错误", path=project_path)
        raise ScanError(f"扫描失败: {e}") from e
```

### TypeScript/React 编码规范

#### 基本原则
- 严格的 TypeScript 配置，禁用 `any` 类型
- 使用函数组件和 Hooks
- 优先使用组合而非继承
- 所有组件必须有 PropTypes 或 TypeScript 接口

#### 组件编写示例
```typescript
// 类型定义
interface ProjectCardProps {
  project: Project;
  onEdit: (project: Project) => void;
  onDelete: (projectId: string) => void;
  className?: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'completed';
  createdAt: Date;
  updatedAt: Date;
}

// 组件实现
export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onEdit,
  onDelete,
  className
}) => {
  const [isLoading, setIsLoading] = useState(false);
  
  const handleEdit = useCallback(() => {
    onEdit(project);
  }, [project, onEdit]);
  
  const handleDelete = useCallback(async () => {
    try {
      setIsLoading(true);
      await onDelete(project.id);
    } catch (error) {
      console.error('删除项目失败:', error);
      // 错误处理
    } finally {
      setIsLoading(false);
    }
  }, [project.id, onDelete]);
  
  return (
    <Card 
      className={cn('project-card', className)}
      actions={[
        <Button key="edit" onClick={handleEdit}>
          编辑
        </Button>,
        <Button 
          key="delete" 
          danger 
          loading={isLoading}
          onClick={handleDelete}
        >
          删除
        </Button>
      ]}
    >
      <Card.Meta
        title={project.name}
        description={project.description}
      />
      <div className="project-meta">
        <Tag color={getStatusColor(project.status)}>
          {getStatusText(project.status)}
        </Tag>
        <span className="project-date">
          {formatDate(project.updatedAt)}
        </span>
      </div>
    </Card>
  );
};

// 工具函数
const getStatusColor = (status: Project['status']): string => {
  const colorMap = {
    active: 'green',
    inactive: 'orange',
    completed: 'blue'
  } as const;
  
  return colorMap[status];
};

const getStatusText = (status: Project['status']): string => {
  const textMap = {
    active: '活跃',
    inactive: '暂停',
    completed: '完成'
  } as const;
  
  return textMap[status];
};
```

#### API 服务示例
```typescript
// API 类型定义
interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
}

interface CreateProjectRequest {
  name: string;
  description: string;
  projectType: 'mod' | 'resourcepack';
  sourceLanguage: string;
  targetLanguages: string[];
}

// API 服务类
export class ProjectApiService {
  private readonly baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
  
  async createProject(
    request: CreateProjectRequest
  ): Promise<Project> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result: ApiResponse<Project> = await response.json();
      
      if (!result.success) {
        throw new Error(result.message);
      }
      
      return result.data;
    } catch (error) {
      console.error('创建项目失败:', error);
      throw new Error('创建项目失败，请稍后重试');
    }
  }
  
  async getProjects(): Promise<Project[]> {
    // 实现获取项目列表
  }
  
  async updateProject(
    id: string, 
    updates: Partial<Project>
  ): Promise<Project> {
    // 实现更新项目
  }
  
  async deleteProject(id: string): Promise<void> {
    // 实现删除项目
  }
}
```

### 文档字符串规范

#### Python 文档字符串
使用 Google 风格的文档字符串:
```python
def scan_minecraft_project(
    project_path: Path,
    include_mods: bool = True,
    recursive: bool = True
) -> ScanResult:
    """扫描 Minecraft 项目中的可翻译内容
    
    Args:
        project_path: 项目根目录路径
        include_mods: 是否包含 MOD 文件扫描
        recursive: 是否递归扫描子目录
        
    Returns:
        ScanResult: 扫描结果，包含找到的文件和翻译条目
        
    Raises:
        ScanError: 当扫描过程出错时
        ValueError: 当参数无效时
        
    Example:
        >>> result = scan_minecraft_project(Path("/game/mods"))
        >>> print(f"找到 {len(result.entries)} 个翻译条目")
    """
```

#### TypeScript 文档注释
使用 JSDoc 风格:
```typescript
/**
 * 项目扫描服务
 * 负责扫描 Minecraft 项目中的可翻译内容
 */
export class ProjectScanService {
  /**
   * 开始扫描项目
   * @param projectPath - 项目路径
   * @param options - 扫描选项
   * @returns Promise 包含扫描结果
   * @throws {ScanError} 当扫描失败时
   * 
   * @example
   * ```typescript
   * const service = new ProjectScanService();
   * const result = await service.scanProject('/path/to/project', {
   *   includeMods: true,
   *   recursive: true
   * });
   * ```
   */
  async scanProject(
    projectPath: string,
    options: ScanOptions
  ): Promise<ScanResult> {
    // 实现
  }
}
```

## 测试规范

### 测试策略

#### 测试金字塔
```
    /\
   /E2E\     ← 端到端测试（少量，高价值）
  /------\
 /  集成  \   ← 集成测试（适量）
/--------\
/  单元   \  ← 单元测试（大量，快速）
/---------\
```

#### 测试覆盖率要求
- **单元测试**: 覆盖率 ≥ 80%
- **集成测试**: 覆盖主要业务流程
- **端到端测试**: 覆盖关键用户路径
- **核心功能**: 覆盖率 ≥ 90%

### Python 测试示例

#### 单元测试
```python
import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from apps.mc_l10n.backend.domain.models.translation_entry import TranslationEntry
from apps.mc_l10n.backend.application.services.translation_service import TranslationService


class TestTranslationService:
    """翻译服务测试"""
    
    @pytest.fixture
    def mock_repository(self):
        """模拟仓储"""
        return Mock()
    
    @pytest.fixture
    def translation_service(self, mock_repository):
        """翻译服务实例"""
        return TranslationService(mock_repository)
    
    async def test_create_translation_success(self, translation_service, mock_repository):
        """测试创建翻译成功"""
        # Arrange
        mock_repository.find_by_key.return_value = None
        mock_repository.save.return_value = "entry_123"
        
        # Act
        result = await translation_service.create_translation(
            key="item.test.sword",
            source_text="Sword",
            target_text="剑",
            language="zh_cn"
        )
        
        # Assert
        assert result == "entry_123"
        mock_repository.find_by_key.assert_called_once_with("item.test.sword")
        mock_repository.save.assert_called_once()
    
    async def test_create_translation_duplicate_key(self, translation_service, mock_repository):
        """测试创建重复键的翻译"""
        # Arrange
        existing_entry = TranslationEntry(
            key="item.test.sword",
            source_text="Sword",
            target_text="剑",
            language="zh_cn"
        )
        mock_repository.find_by_key.return_value = existing_entry
        
        # Act & Assert
        with pytest.raises(TranslationExistsError, match="翻译条目已存在"):
            await translation_service.create_translation(
                key="item.test.sword",
                source_text="Sword",
                target_text="剑",
                language="zh_cn"
            )
    
    @pytest.mark.parametrize("key,source_text,expected_error", [
        ("", "Sword", "翻译键和源文本不能为空"),
        ("item.test.sword", "", "翻译键和源文本不能为空"),
        (None, "Sword", "翻译键和源文本不能为空"),
    ])
    async def test_create_translation_invalid_input(
        self, 
        translation_service, 
        key, 
        source_text, 
        expected_error
    ):
        """测试无效输入参数"""
        with pytest.raises(ValueError, match=expected_error):
            await translation_service.create_translation(
                key=key,
                source_text=source_text,
                target_text="剑",
                language="zh_cn"
            )


class TestTranslationEntry:
    """翻译条目模型测试"""
    
    def test_valid_entry_creation(self):
        """测试有效条目创建"""
        entry = TranslationEntry(
            key="item.test.sword",
            source_text="Sword",
            target_text="剑",
            language="zh_cn"
        )
        
        assert entry.validate() is True
        assert entry.key == "item.test.sword"
        assert entry.source_text == "Sword"
        assert entry.target_text == "剑"
        assert entry.language == "zh_cn"
    
    def test_entry_validation_empty_key(self):
        """测试空键验证"""
        entry = TranslationEntry(
            key="",
            source_text="Sword",
            target_text="剑",
            language="zh_cn"
        )
        
        with pytest.raises(ValueError, match="翻译键和源文本不能为空"):
            entry.validate()
```

#### 集成测试
```python
import pytest
import asyncio
from pathlib import Path
import tempfile
import json

from apps.mc_l10n.backend.main import create_app
from apps.mc_l10n.backend.core.di_container import DIContainer


class TestProjectScanIntegration:
    """项目扫描集成测试"""
    
    @pytest.fixture
    async def test_project(self):
        """创建测试项目"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            
            # 创建模拟 MOD 结构
            assets_dir = project_path / "assets" / "test_mod" / "lang"
            assets_dir.mkdir(parents=True)
            
            # 创建英文语言文件
            en_file = assets_dir / "en_us.json"
            en_data = {
                "item.test_mod.sword": "Test Sword",
                "block.test_mod.ore": "Test Ore"
            }
            en_file.write_text(json.dumps(en_data, indent=2))
            
            # 创建中文语言文件
            zh_file = assets_dir / "zh_cn.json"
            zh_data = {
                "item.test_mod.sword": "测试剑"
                # 故意缺少一个翻译条目
            }
            zh_file.write_text(json.dumps(zh_data, indent=2))
            
            yield project_path
    
    async def test_complete_scan_workflow(self, test_project):
        """测试完整扫描工作流"""
        # 创建应用实例
        app = create_app()
        container = DIContainer()
        
        # 创建项目
        project_service = container.get_project_service()
        project = await project_service.create_project(
            name="测试项目",
            project_path=str(test_project),
            project_type="mod",
            source_language="en_us",
            target_languages=["zh_cn"]
        )
        
        # 执行扫描
        scan_service = container.get_scan_service()
        scan_result = await scan_service.scan_project(project.id)
        
        # 验证扫描结果
        assert scan_result.total_files > 0
        assert scan_result.total_entries == 2  # 两个英文条目
        assert len(scan_result.missing_translations) == 1  # 一个缺失中文翻译
        
        # 验证具体条目
        entries = scan_result.entries
        sword_entry = next(e for e in entries if e.key == "item.test_mod.sword")
        assert sword_entry.source_text == "Test Sword"
        assert sword_entry.target_text == "测试剑"
        
        ore_entry = next(e for e in entries if e.key == "block.test_mod.ore")
        assert ore_entry.source_text == "Test Ore"
        assert ore_entry.target_text == ""  # 缺失翻译
```

### TypeScript 测试示例

#### 组件测试
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { ProjectCard } from '../ProjectCard';

const mockProject: Project = {
  id: 'project-1',
  name: '测试项目',
  description: '这是一个测试项目',
  status: 'active',
  createdAt: new Date('2024-01-01'),
  updatedAt: new Date('2024-01-15')
};

describe('ProjectCard', () => {
  it('应该正确渲染项目信息', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    
    render(
      <ProjectCard 
        project={mockProject}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );
    
    expect(screen.getByText('测试项目')).toBeInTheDocument();
    expect(screen.getByText('这是一个测试项目')).toBeInTheDocument();
    expect(screen.getByText('活跃')).toBeInTheDocument();
  });
  
  it('应该在点击编辑按钮时调用 onEdit', () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    
    render(
      <ProjectCard 
        project={mockProject}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );
    
    fireEvent.click(screen.getByText('编辑'));
    
    expect(onEdit).toHaveBeenCalledWith(mockProject);
  });
  
  it('应该在点击删除按钮时调用 onDelete', async () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn().mockResolvedValue(undefined);
    
    render(
      <ProjectCard 
        project={mockProject}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );
    
    fireEvent.click(screen.getByText('删除'));
    
    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith('project-1');
    });
  });
  
  it('应该在删除失败时显示错误状态', async () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn().mockRejectedValue(new Error('删除失败'));
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    render(
      <ProjectCard 
        project={mockProject}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );
    
    fireEvent.click(screen.getByText('删除'));
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('删除项目失败:', expect.any(Error));
    });
    
    consoleSpy.mockRestore();
  });
});
```

#### API 服务测试
```typescript
import { vi } from 'vitest';
import { ProjectApiService } from '../ProjectApiService';

// 模拟 fetch
global.fetch = vi.fn();

describe('ProjectApiService', () => {
  let apiService: ProjectApiService;
  
  beforeEach(() => {
    apiService = new ProjectApiService('http://localhost:8000');
    vi.clearAllMocks();
  });
  
  it('应该成功创建项目', async () => {
    const mockResponse = {
      data: { id: 'project-1', name: '新项目' },
      message: '创建成功',
      success: true
    };
    
    (fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    } as Response);
    
    const request: CreateProjectRequest = {
      name: '新项目',
      description: '项目描述',
      projectType: 'mod',
      sourceLanguage: 'en_us',
      targetLanguages: ['zh_cn']
    };
    
    const result = await apiService.createProject(request);
    
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/projects',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      })
    );
    
    expect(result).toEqual(mockResponse.data);
  });
  
  it('应该在 HTTP 错误时抛出异常', async () => {
    (fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request'
    } as Response);
    
    const request: CreateProjectRequest = {
      name: '',
      description: '',
      projectType: 'mod',
      sourceLanguage: 'en_us',
      targetLanguages: ['zh_cn']
    };
    
    await expect(apiService.createProject(request))
      .rejects.toThrow('HTTP 400: Bad Request');
  });
  
  it('应该在 API 返回错误时抛出异常', async () => {
    const mockResponse = {
      data: null,
      message: '参数验证失败',
      success: false
    };
    
    (fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    } as Response);
    
    const request: CreateProjectRequest = {
      name: '',
      description: '',
      projectType: 'mod',
      sourceLanguage: 'en_us',
      targetLanguages: ['zh_cn']
    };
    
    await expect(apiService.createProject(request))
      .rejects.toThrow('参数验证失败');
  });
});
```

## 贡献流程

### 1. 问题报告

#### Bug 报告
使用 GitHub Issues 报告 Bug，请包含：
```markdown
## Bug 描述
简要描述遇到的问题

## 重现步骤
1. 打开应用
2. 点击 "创建项目"
3. 输入项目信息
4. 点击 "保存"

## 期望行为
应该成功创建项目并跳转到项目页面

## 实际行为
出现错误提示 "项目创建失败"

## 环境信息
- 操作系统: Windows 11
- TH-Suite 版本: v2.0.1
- Python 版本: 3.12.0
- Node.js 版本: 18.17.0

## 日志信息
```
2024-01-15 10:30:15 ERROR: Database connection failed
```

## 附加信息
- 重启应用后问题依然存在
- 在其他电脑上无法重现
```

#### 功能请求
```markdown
## 功能描述
希望添加批量导入翻译文件的功能

## 使用场景
当有大量现有翻译文件需要导入到新项目时

## 建议实现
1. 在项目页面添加 "批量导入" 按钮
2. 支持拖拽多个文件到导入区域
3. 自动检测文件格式和语言
4. 提供导入预览和确认界面

## 优先级
中等 - 能显著提高工作效率

## 参考
参考 Trans-Hub 网页版的导入功能
```

### 2. 代码贡献

#### Fork 和分支
```bash
# 1. Fork 项目到您的账户
# 2. 克隆 Fork 的仓库
git clone https://github.com/your-username/th-suite.git
cd th-suite

# 3. 添加上游仓库
git remote add upstream https://github.com/trans-hub/th-suite.git

# 4. 创建功能分支
git checkout -b feature/batch-import-translations

# 5. 进行开发
# ...

# 6. 提交更改
git add .
git commit -m "feat: 添加批量导入翻译功能

- 支持拖拽多文件导入
- 自动检测文件格式
- 提供导入预览界面
- 添加导入进度显示

Closes #123"

# 7. 推送分支
git push origin feature/batch-import-translations

# 8. 创建 Pull Request
```

#### 提交消息规范
使用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 格式:

```
<类型>[可选 范围]: <描述>

[可选 正文]

[可选 脚注]
```

**类型说明**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建工具、依赖更新等

**示例**:
```
feat(scan): 添加增量扫描功能

增量扫描只处理自上次扫描后变更的文件，大幅提高扫描速度。

- 基于文件修改时间和 MD5 哈希检测变更
- 支持手动触发完整扫描
- 添加扫描缓存管理
- 更新扫描进度显示

Closes #234
```

#### Pull Request 要求

**PR 标题**: 使用 Conventional Commits 格式
**PR 描述**: 使用模板
```markdown
## 变更描述
<!-- 简要描述本次 PR 的主要变更 -->

## 变更类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 重构
- [ ] 文档更新
- [ ] 性能优化
- [ ] 其他 (请说明):

## 测试
- [ ] 添加了新的测试用例
- [ ] 现有测试全部通过
- [ ] 手动测试通过

## 清单
- [ ] 代码遵循项目编码规范
- [ ] 自测通过，无明显问题
- [ ] 更新了相关文档
- [ ] 添加了必要的测试
- [ ] 提交信息遵循规范

## 关联 Issue
<!-- 如果有关联的 Issue，请在此列出 -->
Closes #issue_number

## 截图或演示
<!-- 如果有 UI 变更，请提供截图或录屏 -->

## 其他说明
<!-- 任何需要审查者注意的事项 -->
```

### 3. 代码审查

#### 审查清单

**功能审查**:
- [ ] 功能是否按需求正确实现
- [ ] 是否处理了异常情况
- [ ] 用户体验是否友好
- [ ] 性能是否可接受

**代码质量**:
- [ ] 代码风格是否一致
- [ ] 变量和函数命名是否清晰
- [ ] 是否有充分的注释和文档
- [ ] 是否遵循设计模式和架构原则

**测试质量**:
- [ ] 测试覆盖率是否足够
- [ ] 测试用例是否全面
- [ ] 测试是否可靠和可重复
- [ ] 是否包含边界条件测试

**安全性**:
- [ ] 是否存在安全漏洞
- [ ] 输入验证是否充分
- [ ] 是否正确处理敏感信息
- [ ] 权限控制是否合理

#### 审查意见类型

**必须修改 (Must Fix)**:
```
🚨 这里存在潜在的安全问题，用户输入没有进行适当的验证
建议使用 Pydantic 模型进行输入验证
```

**建议修改 (Suggestion)**:
```
💡 建议将这个函数拆分为更小的函数，提高可读性
可以考虑提取出数据验证逻辑
```

**问题询问 (Question)**:
```
❓ 这里为什么选择使用同步函数而不是异步函数？
是否有特殊的性能考虑？
```

**赞扬 (Praise)**:
```
👍 这个错误处理逻辑写得很好，考虑了各种边界情况
```

### 4. 发布流程

#### 版本号规范
使用 [语义化版本](https://semver.org/lang/zh-CN/):
- **MAJOR**: 不兼容的 API 修改
- **MINOR**: 向下兼容的功能性新增
- **PATCH**: 向下兼容的问题修正

#### 发布清单
- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] 变更日志已编写
- [ ] 版本号已更新
- [ ] 标签已创建
- [ ] 发布说明已准备

## 开发工具和资源

### 推荐工具

#### 代码编辑器
- **VS Code**: 推荐配置和扩展已提供
- **PyCharm**: 专业 Python 开发环境
- **WebStorm**: 专业前端开发环境

#### 调试工具
- **Python**: pdb, PyCharm 调试器
- **TypeScript**: VS Code 内置调试器
- **API**: Postman, Insomnia
- **数据库**: DB Browser for SQLite

#### 性能分析
- **Python**: cProfile, py-spy
- **前端**: Chrome DevTools, Lighthouse
- **内存**: memory_profiler, heapy

### 学习资源

#### 技术文档
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [React 官方文档](https://react.dev/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Ant Design 文档](https://ant.design/)

#### 架构设计
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)

#### Python 最佳实践
- [The Hitchhiker's Guide to Python](https://docs.python-guide.org/)
- [Real Python](https://realpython.com/)
- [Python Type Checking](https://mypy.readthedocs.io/)

#### TypeScript/React 最佳实践
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Testing Library](https://testing-library.com/docs/react-testing-library/intro/)

## 社区和沟通

### 沟通渠道
- **GitHub Issues**: Bug 报告和功能请求
- **GitHub Discussions**: 一般讨论和问题
- **Discord**: 实时交流和协作
- **邮件**: 重要通知和公告

### 社区准则

#### 行为准则
1. **尊重他人**: 保持友善和专业的沟通
2. **包容性**: 欢迎所有背景的贡献者
3. **建设性**: 提供有用的反馈和建议
4. **耐心**: 理解新贡献者需要时间学习

#### 沟通原则
- 使用清晰、简洁的语言
- 提供具体、可操作的建议
- 承认他人的贡献和努力
- 在不确定时寻求澄清

### 贡献者认可

#### 致谢方式
- **代码贡献**: 在 AUTHORS 文件中列出
- **文档贡献**: 在文档页面中致谢
- **问题报告**: 在发布说明中感谢
- **社区支持**: 在项目页面中展示

#### 贡献者权益
- 参与项目决策讨论
- 优先获得新功能体验
- 受邀参加技术分享会议
- 推荐信和职业发展支持

## 常见问题

### 开发相关

**Q: 如何解决依赖冲突？**
A: 
1. 首先尝试 `poetry update`
2. 检查 `pyproject.toml` 中的版本约束
3. 使用 `poetry show --tree` 查看依赖树
4. 必要时调整版本约束或使用 override

**Q: 测试运行失败怎么办？**
A:
1. 检查环境变量是否正确设置
2. 确认测试数据库是否可访问
3. 运行 `task test --verbose` 查看详细错误
4. 检查是否有端口冲突

**Q: 如何调试异步代码？**
A:
1. 使用 `pytest-asyncio` 进行异步测试
2. 在异步函数中使用 `import pdb; pdb.set_trace()`
3. 考虑使用 `asyncio.create_task()` 进行并发调试
4. 检查事件循环是否正确关闭

### 贡献相关

**Q: 我是新手，可以贡献什么？**
A:
1. 从标记为 "good first issue" 的问题开始
2. 改进文档和注释
3. 编写测试用例
4. 报告 Bug 和提供反馈
5. 翻译和本地化工作

**Q: 如何确保我的 PR 被接受？**
A:
1. 先创建 Issue 讨论功能需求
2. 遵循编码规范和测试要求
3. 保持 PR 范围小而专注
4. 及时响应审查意见
5. 确保所有检查通过

**Q: 代码审查通常需要多长时间？**
A:
1. 小的 Bug 修复：1-2 天
2. 功能性变更：3-7 天
3. 重大重构：1-2 周
4. 紧急修复：几小时内

## 结语

感谢您对 TH-Suite 项目的关注和贡献！无论是代码、文档、测试还是反馈，每一份贡献都对项目的发展非常重要。

通过遵循本指南，您将能够：
- 高效地设置开发环境
- 编写高质量的代码
- 进行充分的测试
- 与社区有效协作

如果您有任何问题或建议，请随时通过 Issues、Discussions 或其他渠道与我们联系。

再次感谢您的贡献，让我们一起把 TH-Suite 打造成最好的游戏本地化工具！