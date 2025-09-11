# TH-Suite 优化实施路线图

> **文档版本**: v1.0  
> **总工期**: 5-7 个工作日  
> **风险等级**: 中等

## 🗓️ 实施计划

### 第一阶段: 基础准备 (1天)

#### 任务 1.1: 环境准备
```bash
# 依赖版本统一
cd /home/saken/project/TH-Suite
poetry update
poetry add trans-hub-sdk --path ../Trans-Hub/packages/sdk
poetry add trans-hub-core --path ../Trans-Hub/packages/core

# 版本对齐检查
poetry show | grep -E "(fastapi|pydantic|python)"
```

#### 任务 1.2: 数据备份
```bash
# 备份现有数据库
cp apps/mc_l10n/data/*.db backups/$(date +%Y%m%d)/
sqlite3 apps/mc_l10n/data/projects.db ".backup 'backups/pre_optimization.db'"

# 代码备份
git checkout -b optimization-backup
git add -A && git commit -m "备份: 优化前代码快照"
git checkout main
```

#### 验收标准
- [ ] SDK 依赖成功安装
- [ ] 版本兼容性检查通过
- [ ] 数据和代码完整备份

---

### 第二阶段: 数据库重构 (2天)

#### 任务 2.1: 新表结构创建
```sql
-- migrations/002_add_version_support.sql
CREATE TABLE IF NOT EXISTS project_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    version_tag TEXT NOT NULL,
    minecraft_version TEXT NOT NULL,
    loader_type TEXT NOT NULL,
    loader_version TEXT,
    is_default BOOLEAN DEFAULT 0,
    is_stable BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    UNIQUE(project_id, version_tag)
);

-- 添加版本关联字段
ALTER TABLE mods ADD COLUMN version_id INTEGER 
    REFERENCES project_versions(id) ON DELETE SET NULL;
ALTER TABLE language_files ADD COLUMN version_id INTEGER 
    REFERENCES project_versions(id) ON DELETE SET NULL;
```

#### 任务 2.2: 数据迁移脚本
```python
# scripts/migrate_to_versioned_schema.py
async def migrate_existing_data():
    """迁移现有数据到版本化结构"""
    
    # 1. 为每个项目创建默认版本
    projects = await db.fetch_all("SELECT * FROM projects")
    
    for project in projects:
        default_version = {
            "project_id": project["id"],
            "version_tag": "default",
            "minecraft_version": project.get("minecraft_versions", "1.19.2"),
            "loader_type": project.get("loader_type", "forge"),
            "is_default": True
        }
        
        version_id = await db.insert("project_versions", default_version)
        
        # 2. 更新 MOD 关联
        await db.execute(
            "UPDATE mods SET version_id = ? WHERE project_id = ?",
            [version_id, project["id"]]
        )
        
        # 3. 更新语言文件关联
        await db.execute(
            "UPDATE language_files SET version_id = ? WHERE project_id = ?",
            [version_id, project["id"]]
        )

    # 4. 清理冗余字段
    await db.execute("ALTER TABLE projects DROP COLUMN total_mods")
    await db.execute("ALTER TABLE projects DROP COLUMN total_language_files")
```

#### 验收标准
- [ ] 新表结构创建成功
- [ ] 现有数据完整迁移
- [ ] 关联关系正确建立
- [ ] 冗余字段成功清理

---

### 第三阶段: SDK 集成 (1.5天)

#### 任务 3.1: 客户端重构
```python
# 重构步骤
# 1. 备份现有客户端
mv apps/mc_l10n/src/adapters/core_client.py \
   apps/mc_l10n/src/adapters/core_client_legacy.py

# 2. 创建 SDK 集成版本
# 按照 03-sdk-integration.md 实现新客户端

# 3. 更新调用代码
grep -r "TransHubClient" apps/ --include="*.py" | \
    cut -d: -f1 | sort -u
# 逐个文件更新导入和调用
```

#### 任务 3.2: 配置管理统一
```python
# apps/mc_l10n/src/config.py
class THSuiteConfig(BaseSettings):
    # 与 Trans-Hub 保持一致的配置模式
    transhub_base_url: str = Field(env="TRANSHUB_BASE_URL")
    transhub_api_key: str = Field(env="TRANSHUB_API_KEY")
    
    # TH-Suite 特有配置
    mc_pack_directory: str = Field(env="THSUITE_MC_PACK_DIRECTORY")
    
    class Config:
        env_prefix = "THSUITE_"
```

#### 验收标准
- [ ] SDK 客户端集成成功
- [ ] 配置管理统一完成
- [ ] 基本功能测试通过

---

### 第四阶段: 数据映射实现 (1天)

#### 任务 4.1: 投影适配器增强
```python
# apps/mc_l10n/src/adapters/projection.py
class MinecraftProjectionAdapter:
    def __init__(self, sdk_client: TransHubClient):
        self.client = sdk_client
        self.mapping_config = load_mapping_config()
    
    async def sync_project_version(self, project_id: int, version_id: int):
        """同步项目版本到 Trans-Hub"""
        # 按照 04-data-mapping.md 实现
```

#### 任务 4.2: 映射配置创建
```yaml
# configs/mapping-rules.yaml
# 按照 04-data-mapping.md 创建完整配置
```

#### 验收标准
- [ ] 投影适配器增强完成
- [ ] 映射配置文件创建
- [ ] 数据映射逻辑验证

---

### 第五阶段: 测试和验证 (0.5天)

#### 任务 5.1: 集成测试
```python
# tests/integration/test_optimization.py
class TestOptimization:
    async def test_versioned_project_creation(self):
        """测试版本化项目创建"""
        
    async def test_sdk_integration(self):
        """测试 SDK 集成"""
        
    async def test_data_mapping(self):
        """测试数据映射"""
        
    async def test_sync_workflow(self):
        """测试完整同步工作流"""
```

#### 任务 5.2: 性能验证
```bash
# 性能基准测试
poetry run python scripts/benchmark_optimization.py
# 对比优化前后的性能指标
```

#### 验收标准
- [ ] 所有集成测试通过
- [ ] 性能指标达到预期
- [ ] 数据一致性验证通过

---

## 🚧 风险控制

### 高风险项
1. **数据迁移风险**: 可能导致数据丢失
   - **缓解**: 完整备份 + 分步迁移 + 验证脚本
   
2. **API 兼容性**: SDK 版本不匹配
   - **缓解**: 版本锁定 + 兼容性测试

3. **性能回退**: 新架构可能影响性能
   - **缓解**: 基准测试 + 性能监控

### 回滚计划
```bash
# 如果需要回滚
git checkout optimization-backup
cp backups/pre_optimization.db apps/mc_l10n/data/projects.db
poetry install  # 恢复原依赖
```

## 📊 成功指标

### 量化目标
- **代码减少**: 删除 15,000+ 行重复代码
- **测试覆盖率**: 从 6.4% 提升到 70%+
- **维护成本**: 降低 60%
- **集成效率**: 提升 50%

### 质量目标
- [ ] 所有单元测试通过
- [ ] 集成测试覆盖率 > 80%
- [ ] 代码质量检查通过
- [ ] 文档完整更新

## 📋 检查清单

### 每日检查
- [ ] 当日任务完成情况
- [ ] 代码提交和备份
- [ ] 测试执行结果
- [ ] 风险项状态更新

### 里程碑检查
- [ ] 第一阶段: 环境和备份就绪
- [ ] 第二阶段: 数据库重构完成
- [ ] 第三阶段: SDK 集成完成
- [ ] 第四阶段: 数据映射实现
- [ ] 第五阶段: 验证和交付

## 📞 支持资源

### 文档参考
- [Trans-Hub SDK 文档](../Trans-Hub/packages/sdk/README.md)
- [数据库迁移指南](./02-database-optimization.md)
- [映射配置规范](./04-data-mapping.md)

### 紧急联系
- **架构问题**: 参考 Trans-Hub 核心团队
- **数据问题**: 数据库备份和恢复流程
- **集成问题**: SDK 版本兼容性检查

---

*实施时请严格按照阶段顺序执行，确保每个阶段的验收标准都满足后再进入下一阶段*