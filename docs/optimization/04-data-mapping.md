# TH-Suite 数据映射策略设计

> **文档版本**: v1.0  
> **基于**: 02-database-optimization.md, 03-sdk-integration.md  
> **核心目标**: 定义 TH-Suite 到 Trans-Hub 的精确数据映射关系

## 🎯 映射策略概述

### 设计原则
1. **同步必要数据**: 仅同步翻译相关的业务数据
2. **保留本地数据**: 构建、路径、缓存等数据仅保存在本地
3. **版本化管理**: 支持同一项目的多版本并存
4. **UIDA 一致性**: 确保唯一标识符的稳定性

## 📊 最优化数据映射表

### TH-Suite → Trans-Hub 映射关系 (最优化设计)

| TH-Suite 实体 | Trans-Hub 实体 | 映射关系 | 说明 |
|---------------|----------------|----------|------|
| 所有整合包 | `th.projects` | N:1 | **单一项目**: "Minecraft" |
| `content_instances` | `th.content` | 1:1 | 每个翻译条目独立内容项 |
| 版本追踪信息 | `th.content.metadata` | 1:1 | 完整版本链路作为元数据 |

### 核心设计理念
- **单一项目原则**: Trans-Hub 中只有一个 "Minecraft" 项目
- **元数据驱动**: 所有版本、MOD、整合包信息都在 content.metadata 中
- **查询层级正确**: `词条 → MOD版本 → 整合包版本`

### 同步 vs 本地数据分类

#### ✅ 同步到 Trans-Hub 的数据
```python
SYNC_FIELDS = {
    "packs": [
        "name",           # 整合包名称
        "project_type",   # 项目类型
        "game_type",      # 游戏类型
        "description",    # 项目描述
        "author",         # 作者信息
    ],
    "pack_versions": [
        "version_tag",        # 版本标签
        "minecraft_version",  # MC版本
        "loader_type",       # 加载器类型
        "display_name",      # 显示名称
        "changelog",         # 变更日志
        "is_stable",         # 稳定性标记
        "is_default",        # 默认版本标记
    ],
    "mod_version_instances": [
        "mod_id",            # MOD标识符
        "mod_version",       # MOD版本
        "mod_name",          # MOD名称
        "description",       # 描述
        "authors",           # 作者列表
        "dependencies",      # 依赖关系
        "minecraft_versions", # 兼容版本
    ],
    "content_instances": [
        "content_key",       # 内容键
        "content_source",    # 内容来源
        "source_identifier", # 来源标识符
        "source_text",       # 源文本
        "language_code",     # 语言代码
        "content_type",      # 内容类型
        "category",          # 分类
        "comment",           # 注释
        "priority",          # 优先级
        "is_override",       # 覆盖标记
    ],
    "pack_content_relations": [
        "inclusion_reason",      # 包含原因
        "relative_path",         # 相对路径
        "override_reason",       # 覆盖原因
        "first_appeared_version", # 首次出现版本
        "last_modified_version",  # 最后修改版本
        "change_type",           # 变更类型
    ]
}
```

#### ❌ 仅保存在本地的数据
```python
LOCAL_ONLY_FIELDS = {
    "packs": [
        "path",              # 本地路径
        "sync_config",       # 同步配置
        "build_config",      # 构建配置
    ],
    "pack_versions": [
        "local_path",        # 版本本地路径
        "build_timestamp",   # 构建时间
    ],
    "mod_version_instances": [
        "jar_file_path",     # JAR文件路径
        "jar_file_size",     # 文件大小
        "jar_file_hash",     # 文件哈希
        "extraction_path",   # 解压路径
    ],
    "content_instances": [
        "file_path",         # 文件路径
        "file_format",       # 文件格式
        "line_number",       # 行号
        "raw_content",       # 原始内容
    ],
    "pack_mod_relations": [
        "detected_at",       # 检测时间
        "detection_method",  # 检测方式
    ],
    "pack_content_relations": [
        "detected_at",       # 检测时间
        "detection_method",  # 检测方式
    ]
}
```

## 🔄 投影适配器实现

### 最优化投影适配器 (单项目+元数据驱动)
```python
class OptimizedProjectionAdapter:
    """最优化投影适配器 - 单一项目多维度元数据"""
    
    MINECRAFT_PROJECT_ID = "minecraft"  # 固定项目ID
    
    def ensure_minecraft_project(self) -> dict:
        """确保 Minecraft 项目存在"""
        return {
            "project_id": self.MINECRAFT_PROJECT_ID,
            "display_name": "Minecraft",
            "metadata": {
                "game_type": "minecraft",
                "project_type": "game_localization",
                "description": "Minecraft 游戏本地化项目",
                "supported_loaders": ["forge", "fabric", "quilt", "neoforge"],
                "content_types": ["mod_jar", "pack_resource", "quest_pack", "config_file", "pack_docs"]
            }
        }
    
    def map_content_instance_to_transhub(
        self,
        content_instance: dict,
        pack_version: dict,
        relation_info: dict,
        mod_instance: dict = None
    ) -> dict:
        """映射内容实例到 Trans-Hub (单一 Minecraft 项目)"""
        
        # 生成多维度 UIDA 键
        uida_keys = self._generate_uida_keys(
            content_instance, pack_version, mod_instance
        )
        
        return {
            "project_id": self.MINECRAFT_PROJECT_ID,  # 固定项目ID
            "namespace": "minecraft",
            "keys": uida_keys,
            "source_lang": content_instance["language_code"],
            "source_payload": {
                "key": content_instance["content_key"],
                "value": self._stabilize_text(content_instance["source_text"]),
                "original_value": content_instance["source_text"],
                "comment": content_instance.get("comment")
            },
            "metadata": self._build_version_metadata(
                content_instance, pack_version, relation_info, mod_instance
            )
        }
    
    def _generate_uida_keys(
        self, 
        content_instance: dict, 
        pack_version: dict,
        mod_instance: dict = None
    ) -> List[str]:
        """生成多维度 UIDA 键 (支持正确的查询层级)"""
        
        # 基础键: 翻译键本身
        base_keys = [f"key:{content_instance['content_key']}"]
        
        # 根据内容来源添加层级键
        if content_instance["content_source"] == "mod_jar" and mod_instance:
            # MOD内容: key → mod_version → pack_version → mc_version
            base_keys.extend([
                f"mod:{mod_instance['mod_id']}:{mod_instance['mod_version']}",
                f"pack:{pack_version['pack_name']}:{pack_version['version_tag']}",
                f"mc:{pack_version['minecraft_version']}",
                f"loader:{pack_version['loader_type']}"
            ])
        elif content_instance["content_source"] == "pack_resource":
            # 整合包专属资源: key → pack_version → mc_version
            base_keys.extend([
                "source:pack_resource",
                f"pack:{pack_version['pack_name']}:{pack_version['version_tag']}",
                f"mc:{pack_version['minecraft_version']}",
                f"loader:{pack_version['loader_type']}"
            ])
        elif content_instance["content_source"] == "quest_pack":
            # 任务内容: quest → pack_version → mc_version
            base_keys[0] = f"quest:{content_instance['content_key']}"
            base_keys.extend([
                f"quest_type:{content_instance['content_type']}",
                f"pack:{pack_version['pack_name']}:{pack_version['version_tag']}",
                f"mc:{pack_version['minecraft_version']}"
            ])
        elif content_instance["content_source"] == "config_file":
            # 配置文件: config → pack_version → mc_version
            base_keys.extend([
                "source:config",
                f"pack:{pack_version['pack_name']}:{pack_version['version_tag']}",
                f"mc:{pack_version['minecraft_version']}"
            ])
        elif content_instance["content_source"] == "pack_docs":
            # 整合包文档: docs → pack_version → mc_version
            base_keys.extend([
                "source:pack_docs",
                f"pack:{pack_version['pack_name']}:{pack_version['version_tag']}",
                f"mc:{pack_version['minecraft_version']}"
            ])
        elif content_instance["content_source"] == "override":
            # 覆盖内容: override → pack_version → mc_version
            base_keys.extend([
                "source:override",
                f"pack:{pack_version['pack_name']}:{pack_version['version_tag']}",
                f"mc:{pack_version['minecraft_version']}",
                f"override_priority:{content_instance['priority']}"
            ])
        
        return base_keys
    
    def _build_version_metadata(
        self, 
        content_instance: dict,
        pack_version: dict, 
        relation_info: dict,
        mod_instance: dict = None
    ) -> dict:
        """构建完整的版本元数据 (单一项目多维度过滤用)"""
        
        metadata = {
            # 内容来源信息
            "content_source": content_instance["content_source"],
            "source_identifier": content_instance["source_identifier"],
            "content_type": content_instance["content_type"],
            "category": content_instance["category"],
            
            # 整合包信息
            "pack_name": pack_version["pack_name"],
            "pack_version": pack_version["version_tag"],
            "minecraft_version": pack_version["minecraft_version"],
            "loader_type": pack_version["loader_type"],
            
            # 版本追踪信息
            "first_appeared_version": relation_info.get("first_appeared_version"),
            "last_modified_version": relation_info.get("last_modified_version"),
            "change_type": relation_info.get("change_type"),
            
            # 覆盖信息
            "is_override": content_instance["is_override"],
            "override_reason": relation_info.get("override_reason"),
            "relative_path": relation_info.get("relative_path"),
            
            # 优先级
            "priority": content_instance["priority"]
        }
        
        # MOD 相关元数据
        if mod_instance:
            metadata.update({
                "mod_id": mod_instance["mod_id"],
                "mod_version": mod_instance["mod_version"],
                "mod_name": mod_instance["mod_name"],
                "mod_authors": mod_instance.get("authors"),
                "mod_dependencies": mod_instance.get("dependencies")
            })
        
        return metadata
    
    def _stabilize_text(self, text: str) -> str:
        """统一的文本稳定化处理"""
        if not text:
            return ""
        
        # 应用稳定化规则
        stabilized = text.strip()
        
        # 标准化空格
        import re
        stabilized = re.sub(r'\s+', ' ', stabilized)
        
        # 移除控制字符 (但保留换行符用于多行文本)
        stabilized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', stabilized)
        
        return stabilized
```

## 🔄 双向同步策略

### TH-Suite → Trans-Hub (上传)
```python
class SyncToTransHubService:
    """同步到 Trans-Hub 服务 (单一 Minecraft 项目)"""
    
    async def sync_pack_version(
        self, 
        pack_id: int, 
        version_id: int
    ) -> dict:
        """同步整合包版本到 Trans-Hub (统一 Minecraft 项目)"""
        
        # 1. 获取整合包和版本信息
        pack = await self.repository.get_pack(pack_id)
        version = await self.repository.get_pack_version(version_id)
        
        # 2. 确保统一 Minecraft 项目存在
        adapter = OptimizedProjectionAdapter()
        minecraft_project = adapter.ensure_minecraft_project()
        
        async with self.transhub_client:
            # 3. 创建或更新统一 Minecraft 项目
            await self.transhub_client.projects.create_or_update(minecraft_project)
        
            # 4. 同步翻译内容 (版本信息在元数据中)
            await self._sync_version_content(pack_id, version_id, adapter.MINECRAFT_PROJECT_ID)
        
        # 5. 更新本地同步状态
        await self.repository.update_sync_status(pack_id, version_id, {
            "last_sync_at": datetime.utcnow(),
            "transhub_project_id": adapter.MINECRAFT_PROJECT_ID,
            "sync_status": "completed"
        })
        
        return {
            "success": True,
            "transhub_project_id": adapter.MINECRAFT_PROJECT_ID,
            "synced_content_count": await self._count_synced_content(version_id)
        }
```

### Trans-Hub → TH-Suite (下载)
```python
class SyncFromTransHubService:
    """从 Trans-Hub 同步服务 (单一 Minecraft 项目)"""
    
    async def pull_translations(
        self, 
        pack_id: int, 
        version_id: int,
        target_language: str
    ) -> dict:
        """拉取翻译更新 (从统一 Minecraft 项目)"""
        
        # 1. 获取整合包版本信息用于过滤
        pack_version = await self.repository.get_pack_version(version_id)
        
        # 2. 从 Trans-Hub 统一项目导出翻译 (使用版本过滤)
        async with self.transhub_client:
            translations = await self.transhub_client.content.export_translations(
                project_id="minecraft",  # 固定统一项目ID
                target_language=target_language,
                status_filter=["published", "reviewed"],
                metadata_filters={
                    "pack_name": pack_version["pack_name"],
                    "pack_version": pack_version["version_tag"],
                    "minecraft_version": pack_version["minecraft_version"],
                    "loader_type": pack_version["loader_type"]
                }
            )
        
        # 3. 反向映射到本地数据结构
        local_updates = []
        for translation in translations:
            local_update = self.content_mapper.map_content_to_local(translation)
            local_updates.append(local_update)
        
        # 4. 更新本地翻译文件
        updated_files = await self._update_local_files(local_updates)
        
        return {
            "success": True,
            "updated_translations": len(local_updates),
            "updated_files": len(updated_files),
            "target_language": target_language
        }
```

## 📋 映射配置文件

### configs/mapping-rules.yaml
```yaml
# TH-Suite 数据映射规则配置
version: 1.0
app: "th-suite"

# 单一项目设计
minecraft_project:
  project_id: "minecraft"
  display_name: "Minecraft"
  namespace: "minecraft"

# UIDA 键生成规则 (支持正确查询层级)
uida_key_templates:
  - "key:{translation_key}"               # 基础翻译键
  - "mod:{mod_id}:{mod_version}"          # MOD版本层级
  - "pack:{pack_name}:{version_tag}"      # 整合包版本层级
  - "mc:{minecraft_version}"              # MC版本过滤
  - "loader:{loader_type}"                # 加载器过滤

# 字段映射规则 (单一项目设计)
field_mappings:
  packs:
    sync_fields: ["name", "project_type", "game_type", "description", "author"]
    local_fields: ["path", "sync_config", "build_config"]
  
  pack_versions:
    sync_fields: ["version_tag", "minecraft_version", "loader_type", "display_name", "changelog"]
    local_fields: ["local_path", "build_timestamp"]
    
  mod_version_instances:
    sync_fields: ["mod_id", "mod_version", "mod_name", "description", "authors", "dependencies"]
    local_fields: ["jar_file_path", "jar_file_size", "jar_file_hash", "extraction_path"]
    
  content_instances:
    sync_fields: ["content_key", "content_source", "source_text", "language_code", "content_type"]
    local_fields: ["file_path", "file_format", "line_number", "raw_content"]

# 文本稳定化规则
text_stabilizers:
  - "trim"               # 去除首尾空格
  - "normalize_space"    # 规范化空格
  - "remove_control"     # 移除控制字符

# 反向映射配置 (基于正确层级结构)
reverse_mapping:
  content_to_local:
    translation_key: "{keys[0]|strip_prefix:key:}"        # 从第一个键提取翻译键
    mod_info: "{keys[1]|strip_prefix:mod:}"               # MOD:版本信息
    pack_info: "{keys[2]|strip_prefix:pack:}"             # 整合包:版本信息
    minecraft_version: "{keys[3]|strip_prefix:mc:}"       # MC版本
    loader_type: "{keys[4]|strip_prefix:loader:}"         # 加载器类型
```

---

*下一步: 阅读实施路线图*