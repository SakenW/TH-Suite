# TH-Suite SDK 集成改进计划

> **文档版本**: v1.0  
> **基于**: 01-integration-analysis.md  
> **核心目标**: 替换自定义 HTTP 客户端为 Trans-Hub 官方 SDK

## 🔍 当前问题

### 重复实现的客户端
1. **core_client.py**: 自实现的 HTTP 客户端 (450+ 行)
2. **localization-kit/transhub_client.py**: 另一个 HTTP 客户端实现
3. **总代码重复**: 约 15,000+ 行

### 维护负担
- API 接口不一致
- 错误处理逻辑重复
- 认证机制各自实现
- 版本兼容性问题

## 🎯 改进方案

### 第一步: 添加 SDK 依赖

```toml
# pyproject.toml 更新
[tool.poetry.dependencies]
python = "^3.10"  # 与 Trans-Hub 保持一致
trans-hub-sdk = {path = "../Trans-Hub/packages/sdk", develop = true}
trans-hub-core = {path = "../Trans-Hub/packages/core", develop = true}

# 移除重复依赖
# aiohttp = "^3.12.15"  # 删除
# httpx = "^0.28.1"     # 保留用于其他用途
```

### 第二步: 重构客户端适配器

```python
# apps/mc_l10n/src/adapters/core_client.py (重构版)
from trans_hub_sdk import TransHubClient
from trans_hub_sdk.models import ClientConfig, ContentItem
from typing import List, Dict, Any

class MinecraftTransHubAdapter:
    """使用官方 SDK 的 Minecraft 适配器"""
    
    def __init__(self, base_url: str, api_key: str):
        self.client = TransHubClient(
            config=ClientConfig(
                base_url=base_url,
                api_key=api_key,
                user_agent="TH-Suite-MC-L10N/2.0"
            )
        )
    
    async def create_project(self, project_data: Dict[str, Any]) -> str:
        """创建项目 - 使用 SDK 标准方法"""
        async with self.client:
            project = await self.client.projects.create(project_data)
            return project.project_id
    
    async def ingest_content_batch(
        self, 
        project_id: str, 
        content_items: List[ContentItem]
    ) -> Dict[str, Any]:
        """批量摄入内容 - 使用 SDK 标准方法"""
        async with self.client:
            result = await self.client.content.ingest_batch(
                project_id=project_id,
                items=content_items
            )
            return {
                "success": result.success,
                "processed_items": result.processed_count,
                "failed_items": result.failed_count,
                "errors": result.errors
            }
    
    async def export_translations(
        self, 
        project_id: str, 
        target_language: str,
        **filters
    ) -> List[Dict[str, Any]]:
        """导出翻译 - 使用 SDK 流式接口"""
        translations = []
        async with self.client:
            async for item in self.client.content.export_stream(
                project_id=project_id,
                target_language=target_language,
                **filters
            ):
                translations.append(item)
        return translations
```

### 第三步: 配置管理统一

```python
# apps/mc_l10n/src/config.py (新增)
from pydantic import BaseSettings, Field

class THSuiteConfig(BaseSettings):
    """TH-Suite 配置 - 与 Trans-Hub 保持一致"""
    
    # Trans-Hub 连接配置
    transhub_base_url: str = Field(
        default="http://localhost:8000",
        env="TRANSHUB_BASE_URL"
    )
    transhub_api_key: str = Field(
        env="TRANSHUB_API_KEY"
    )
    
    # 应用特定配置
    mc_pack_directory: str = Field(
        default="./minecraft_packs",
        env="THSUITE_MC_PACK_DIRECTORY"  # 自有前缀
    )
    
    class Config:
        env_file = ".env"
        env_prefix = "THSUITE_"  # 避免与 Trans-Hub 冲突
```

## 🔄 投影适配器增强

### 与 SDK 集成的投影适配器

```python
# apps/mc_l10n/src/adapters/projection.py (增强版)
from trans_hub_sdk.models import ContentItem
from trans_hub_core.types import UidaHash

class MinecraftProjectionAdapter:
    """Minecraft 投影适配器 - SDK 集成版"""
    
    def __init__(self, sdk_client: TransHubClient):
        self.client = sdk_client
        self.spec = self._load_projection_spec()
    
    async def minecraft_to_core(
        self, 
        minecraft_data: MinecraftLanguageData
    ) -> List[ContentItem]:
        """转换为 SDK 标准内容项"""
        content_items = []
        
        for lang_file in minecraft_data.language_files:
            for key, value in lang_file.translations.items():
                # 使用 SDK 的内容项模型
                item = ContentItem(
                    project_id=self._generate_project_id(minecraft_data),
                    namespace="minecraft",
                    keys=self._generate_uida_keys(minecraft_data, lang_file, key),
                    source_language=lang_file.language_code,
                    source_text=self._stabilize_text(value),
                    metadata={
                        "mod_id": lang_file.mod_id,
                        "file_path": lang_file.file_path,
                        "loader_type": minecraft_data.mod_loader
                    }
                )
                content_items.append(item)
        
        return content_items
    
    async def sync_to_transhub(
        self, 
        project_id: str, 
        minecraft_data: MinecraftLanguageData
    ) -> Dict[str, Any]:
        """同步到 Trans-Hub"""
        content_items = await self.minecraft_to_core(minecraft_data)
        
        # 使用适配器的客户端实例
        result = await self.client.content.ingest_batch(
            project_id=project_id,
            items=content_items
        )
        
        return {
            "synced_items": result.processed_count,
            "failed_items": result.failed_count,
            "errors": result.errors
        }
```

## 📋 迁移步骤

### 阶段 1: 依赖更新 (1天)
```bash
# 1. 更新依赖
cd /home/saken/project/TH-Suite
poetry add trans-hub-sdk --path ../Trans-Hub/packages/sdk
poetry add trans-hub-core --path ../Trans-Hub/packages/core

# 2. 移除重复依赖
poetry remove aiohttp  # 如果仅用于 Trans-Hub 通信

# 3. 验证安装
poetry run python -c "from trans_hub_sdk import TransHubClient; print('SDK 导入成功')"
```

### 阶段 2: 客户端重构 (2天)
```bash
# 1. 备份现有实现
mv apps/mc_l10n/src/adapters/core_client.py apps/mc_l10n/src/adapters/core_client_old.py

# 2. 创建新实现
# 按照上述示例重写 core_client.py

# 3. 更新导入引用
grep -r "from.*core_client" apps/ --include="*.py"
# 逐一更新调用代码
```

### 阶段 3: 测试验证 (1天)
```python
# tests/adapters/test_sdk_integration.py
import pytest
from apps.mc_l10n.src.adapters.core_client import MinecraftTransHubAdapter

class TestSDKIntegration:
    @pytest.fixture
    def adapter(self):
        return MinecraftTransHubAdapter(
            base_url="http://localhost:8000",
            api_key="test_key"
        )
    
    async def test_project_creation(self, adapter):
        """测试项目创建"""
        project_data = {
            "name": "Test Modpack",
            "type": "modpack",
            "game_type": "minecraft"
        }
        
        project_id = await adapter.create_project(project_data)
        assert project_id.startswith("mc:")
    
    async def test_content_ingestion(self, adapter):
        """测试内容摄入"""
        # 使用 SDK 的内容项模型
        content_items = [
            ContentItem(
                project_id="mc:test:1.19.2",
                namespace="minecraft",
                keys=["mod:testmod", "key:item.test"],
                source_language="en_us",
                source_text="Test Item"
            )
        ]
        
        result = await adapter.ingest_content_batch("mc:test:1.19.2", content_items)
        assert result["success"] is True
```

## ⚠️ 注意事项

### 1. 向后兼容性
- 保留旧客户端实现作为备份
- 分步骤迁移，降低风险
- 确保关键功能不中断

### 2. 错误处理
- SDK 异常与自定义异常的转换
- 网络错误的统一处理
- 重试机制的配置

### 3. 性能考虑
- SDK 连接池配置
- 批量操作的优化
- 内存使用的监控

---

*下一步: 阅读数据映射策略设计*