# TH-Suite 版本管理系统

## 概述

TH-Suite 版本管理系统是一个完整的数据版本控制解决方案，专为翻译数据管理而设计。它提供了类似Git的版本控制功能，包括版本控制、分支管理、回滚操作、标签管理和性能优化。

## 核心特性

### 🗂️ 版本仓库管理
- **自动仓库创建**: 为项目、MOD、语言文件等实体自动创建版本仓库
- **多实体支持**: 支持项目(Project)、整合包(Pack)、MOD、语言文件(Language File)、翻译条目(Translation Entries)
- **仓库统计**: 提供分支数量、提交数量、标签数量等统计信息

### 🌿 分支管理
- **分支创建**: 支持功能分支、热修复分支、发布分支等
- **分支保护**: 支持保护分支，防止误操作
- **分支列表**: 显示所有分支及其状态信息
- **HEAD引用**: 自动管理分支HEAD指针

### 📝 提交管理
- **版本提交**: 创建包含完整内容的版本提交
- **提交历史**: 按时间顺序显示提交历史
- **作者信息**: 记录提交者姓名和邮箱
- **提交消息**: 支持标题和详细描述
- **元数据**: 支持自定义元数据存储

### 🔄 版本差异
- **智能差异计算**: 基于JSON Patch标准的差异算法
- **三种差异类型**: 
  - 正向差异(Forward): A → B
  - 反向差异(Reverse): B → A  
  - 三路差异(Three-way): 用于合并场景
- **差异应用**: 将差异应用到基础数据
- **差异优化**: 减少操作数量，提高性能

### ⏪ 版本回滚
- **多种回滚策略**:
  - **Revert**: 创建回滚提交(推荐)
  - **Reset Soft**: 软重置，保留工作区
  - **Reset Hard**: 硬重置，完全回滚
- **路径验证**: 验证回滚路径的有效性
- **安全检查**: 防止无效或危险的回滚操作

### 🔀 分支合并
- **多种合并策略**:
  - **Fast Forward**: 快进合并
  - **Three-way**: 三路合并(默认)
  - **Ours**: 使用目标分支版本
  - **Theirs**: 使用源分支版本
- **冲突检测**: 自动检测合并冲突
- **冲突解决**: 支持手动和自动冲突解决

### 🏷️ 标签管理
- **版本标签**: 为重要版本创建标签
- **标签类型**: 支持release、milestone、hotfix、feature等类型
- **标签描述**: 支持详细描述和元数据
- **标签列表**: 显示所有标签及关联提交信息

### 🔄 同步集成
- **版本感知同步**: 与Trans-Hub同步时保持版本信息
- **冲突处理**: 智能处理同步冲突
- **同步策略**: 支持多种版本同步策略
- **远程版本**: 管理远程版本信息

### ⚡ 性能优化
- **数据压缩**: 支持GZIP、ZSTD、LZMA压缩算法
- **多层缓存**: 内存缓存 + 磁盘缓存
- **增量存储**: 基于差异的增量存储
- **去重存储**: 内容寻址存储(CAS)避免重复

## API接口

### 仓库管理
```http
POST   /api/v1/versions/repositories          # 创建版本仓库
GET    /api/v1/versions/repositories/{uid}    # 获取仓库信息
GET    /api/v1/versions/repositories/{uid}/stats # 获取仓库统计
```

### 分支管理
```http
POST   /api/v1/versions/repositories/{uid}/branches    # 创建分支
GET    /api/v1/versions/repositories/{uid}/branches    # 列出分支
```

### 提交管理
```http
POST   /api/v1/versions/repositories/{uid}/commits     # 创建提交
GET    /api/v1/versions/repositories/{uid}/commits     # 获取提交历史
```

### 版本操作
```http
POST   /api/v1/versions/repositories/{uid}/rollback    # 版本回滚
POST   /api/v1/versions/repositories/{uid}/merge       # 分支合并
POST   /api/v1/versions/repositories/{uid}/diff        # 版本比较
```

### 标签管理
```http
POST   /api/v1/versions/repositories/{uid}/tags        # 创建标签
GET    /api/v1/versions/repositories/{uid}/tags        # 列出标签
```

### 系统监控
```http
GET    /api/v1/versions/health                         # 健康检查
```

## 使用示例

### 1. 创建项目版本仓库

```bash
curl -X POST http://localhost:18000/api/v1/versions/repositories \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "project",
    "entity_uid": "my-minecraft-project",
    "default_branch": "main"
  }'
```

### 2. 创建功能分支

```bash
curl -X POST http://localhost:18000/api/v1/versions/repositories/{repository_uid}/branches \
  -H "Content-Type: application/json" \
  -d '{
    "name": "feature/new-translations",
    "description": "添加新的翻译内容",
    "is_protected": false
  }'
```

### 3. 创建版本提交

```bash
curl -X POST http://localhost:18000/api/v1/versions/repositories/{repository_uid}/commits \
  -H "Content-Type: application/json" \
  -d '{
    "branch_name": "main",
    "author_name": "翻译员",
    "message": "添加基础方块翻译",
    "content_data": {
      "translation_entries": [
        {
          "key": "item.minecraft.stone",
          "src_text": "Stone",
          "dst_text": "石头",
          "status": "reviewed"
        }
      ]
    },
    "author_email": "translator@example.com"
  }'
```

### 4. 版本回滚

```bash
curl -X POST http://localhost:18000/api/v1/versions/repositories/{repository_uid}/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "target_commit_uid": "commit-uid-to-rollback-to",
    "strategy": "revert",
    "author_name": "系统管理员",
    "message": "回滚到稳定版本"
  }'
```

### 5. 创建版本标签

```bash
curl -X POST http://localhost:18000/api/v1/versions/repositories/{repository_uid}/tags \
  -H "Content-Type: application/json" \
  -d '{
    "tag_name": "v1.0.0",
    "commit_uid": "commit-uid",
    "tag_type": "release",
    "description": "第一个稳定版本",
    "metadata": {
      "version": "1.0.0",
      "stable": true
    }
  }'
```

### 6. 版本比较

```bash
curl -X POST http://localhost:18000/api/v1/versions/repositories/{repository_uid}/diff \
  -H "Content-Type: application/json" \
  -d '{
    "from_commit_uid": "old-commit-uid",
    "to_commit_uid": "new-commit-uid",
    "diff_type": "forward"
  }'
```

## 数据库架构

### 核心表结构

#### 版本仓库表 (version_repositories)
- 管理实体的版本仓库
- 关联实体类型和UID
- 默认分支配置

#### 版本分支表 (version_branches)  
- 分支信息和层级关系
- 分支保护设置
- 创建时间和更新时间

#### 版本提交表 (version_commits)
- 提交信息和作者
- 父子关系和分支关联
- 提交哈希和元数据

#### 版本快照表 (version_snapshots)
- 版本内容存储
- 压缩和去重
- 内容寻址(CAS)

#### 版本差异表 (version_diffs)
- 版本间差异
- 增量存储
- 差异格式和操作

#### 版本标签表 (version_tags)
- 版本标签信息
- 标签类型和描述
- 关联提交

#### 扩展表
- 版本合并表 (version_merges)
- 版本冲突表 (version_conflicts)  
- 版本操作日志表 (version_operations_log)
- 版本同步状态表 (version_sync_status)

### 数据库迁移

运行以下迁移文件来创建版本管理表：

```bash
# 1. 创建版本管理核心表
sqlite3 data/mc_l10n.db < migrations/010_create_version_management_tables.sql

# 2. 扩展现有表支持版本管理
sqlite3 data/mc_l10n.db < migrations/011_extend_core_tables_for_versioning.sql
```

## 配置选项

### 版本管理服务配置
```python
{
    "auto_versioning": True,           # 自动版本管理
    "default_branch": "main",          # 默认分支名
    "max_commits_per_branch": 10000,   # 每分支最大提交数
    "snapshot_compression": "zstd",    # 快照压缩算法
    "diff_format": "json_patch",       # 差异格式
    "cache_snapshots": True,           # 缓存快照
    "cache_diffs": True,               # 缓存差异
    "retention_days": 365              # 数据保留天数
}
```

### 性能优化配置
```python
{
    "default_compression": "gzip",     # 默认压缩算法
    "compression_threshold": 1024,     # 压缩阈值(字节)
    "cache_strategy": "hybrid",        # 缓存策略
    "cache_ttl": 3600,                # 缓存生存时间
    "storage_mode": "incremental_delta", # 存储模式
    "parallel_operations": True,       # 并行操作
    "memory_limit": 536870912         # 内存限制(512MB)
}
```

### 同步集成配置
```python
{
    "version_sync_enabled": True,      # 启用版本同步
    "conflict_resolution_strategy": "manual", # 冲突解决策略
    "sync_batch_size": 1000,          # 同步批处理大小
    "enable_compression": True,        # 启用同步压缩
    "sync_timeout": 300               # 同步超时时间
}
```

## 性能指标

### 目标性能
- **版本创建**: < 5秒 (10,000条目)
- **版本回滚**: < 10秒 (任意规模)  
- **差异计算**: < 2秒 (版本对比)
- **压缩率**: 60-80% (取决于数据类型)
- **缓存命中率**: > 80%

### 性能监控
```bash
# 获取性能统计
curl http://localhost:18000/api/v1/versions/repositories/{uid}/stats

# 系统健康检查
curl http://localhost:18000/api/v1/versions/health
```

## 最佳实践

### 1. 版本管理工作流
1. **创建项目仓库**: 为每个翻译项目创建版本仓库
2. **功能分支开发**: 为新功能创建专门分支
3. **定期提交**: 阶段性完成时创建提交
4. **版本标签**: 为稳定版本创建标签
5. **分支合并**: 功能完成后合并到主分支

### 2. 提交信息规范
- **标题**: 简明扼要描述变更(50字符内)
- **描述**: 详细说明变更原因和影响
- **类型**: 使用统一的提交类型前缀
  - `feat:` 新功能
  - `fix:` 修复问题
  - `docs:` 文档更新
  - `refactor:` 代码重构
  - `test:` 测试相关

### 3. 分支命名规范
- `feature/功能名称` - 功能开发分支
- `hotfix/修复名称` - 热修复分支
- `release/版本号` - 发布准备分支
- `bugfix/问题名称` - 问题修复分支

### 4. 标签命名规范
- `v1.0.0` - 正式版本
- `v1.0.0-rc1` - 发布候选版本
- `v1.0.0-beta1` - 测试版本
- `v1.0.0-alpha1` - 内部版本

### 5. 性能优化建议
- **启用压缩**: 对大数据集启用压缩
- **合理缓存**: 配置适当的缓存策略
- **定期清理**: 清理过期的版本数据
- **批量操作**: 使用批量API减少请求次数

## 故障排除

### 常见问题

#### 1. 版本管理表不存在
**错误**: `版本管理表不存在，请运行数据库迁移`

**解决方案**:
```bash
# 运行数据库迁移
sqlite3 data/mc_l10n.db < migrations/010_create_version_management_tables.sql
sqlite3 data/mc_l10n.db < migrations/011_extend_core_tables_for_versioning.sql
```

#### 2. 分支创建失败
**错误**: `分支 main 已存在`

**解决方案**: 检查分支是否已存在，使用不同的分支名称

#### 3. 提交创建失败
**错误**: `分支 feature/test 不存在`

**解决方案**: 先创建分支，再创建提交

#### 4. 回滚失败
**错误**: `无效的回滚路径`

**解决方案**: 确保目标提交在当前提交的历史路径中

#### 5. 性能问题
**症状**: API响应缓慢

**解决方案**:
- 检查缓存配置
- 启用数据压缩
- 优化数据库查询
- 增加内存限制

### 调试工具

#### 1. 健康检查
```bash
curl http://localhost:18000/api/v1/versions/health
```

#### 2. 系统状态
```bash
curl http://localhost:18000/api/v1/versions/repositories/{uid}/stats
```

#### 3. 日志查看
```bash
# 查看应用日志
tail -f logs/mc_l10n.log

# 查看错误日志
grep ERROR logs/mc_l10n.log
```

## 测试

### 运行测试
```bash
# 运行版本管理系统测试
cd apps/mc_l10n/backend
python test_version_management_system.py
```

### 测试覆盖
- ✅ 版本仓库管理
- ✅ 分支管理
- ✅ 提交管理
- ✅ 差异计算
- ✅ 版本回滚
- ✅ 分支合并
- ✅ 标签管理
- ✅ 性能优化
- ✅ 同步集成
- ✅ 综合工作流

## 路线图

### 已完成 ✅
- [x] 核心版本管理功能
- [x] 分支和标签管理
- [x] 差异计算引擎
- [x] 版本回滚和合并
- [x] 性能优化
- [x] 同步协议集成
- [x] REST API接口
- [x] 数据库架构
- [x] 综合测试

### 计划中 🚧
- [ ] Web界面集成
- [ ] 可视化提交图
- [ ] 高级冲突解决
- [ ] 分布式版本管理
- [ ] 版本分析报告
- [ ] 自动化测试集成

### 考虑中 💭
- [ ] Git兼容接口
- [ ] 版本间文件比较
- [ ] 高级压缩算法
- [ ] 机器学习优化
- [ ] 云端版本备份

---

## 许可证

本版本管理系统是TH-Suite项目的一部分，采用相同的开源许可证。

## 贡献

欢迎贡献代码和建议！请参考项目的贡献指南。

## 支持

如有问题或建议，请在GitHub上创建Issue或联系开发团队。