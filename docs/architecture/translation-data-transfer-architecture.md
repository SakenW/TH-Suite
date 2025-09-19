# TH-Suite 翻译数据传输架构设计

## 设计概述

本文档描述了TH-Suite全新的数据优先传输架构，专注于传输翻译条目数据而非完整文件，实现轻量级、高效的多游戏翻译同步系统。

## 核心设计理念

### 数据优先 vs 文件优先

**传统方式**（文件优先）：
```
游戏文件 → 压缩包 → 上传 → 解压 → 解析 → 翻译数据
```

**新架构**（数据优先）：
```
游戏文件 → 提取器 → 翻译数据 → 同步器 → 远程翻译数据
```

### 关键优势

1. **传输量减少90%+**：只传输翻译文本，不传输二进制文件
2. **实时同步**：增量更新，支持多人协作
3. **格式无关**：统一数据模型，支持多游戏格式
4. **版本控制**：完整的翻译历史和回滚机制
5. **离线友好**：支持离线编辑和批量同步

## 架构组件设计

### 1. 统一翻译数据模型

#### 核心数据结构

```python
@dataclass
class TranslationEntry:
    """统一翻译条目模型"""
    
    # 标识信息
    entry_id: str                    # 全局唯一标识
    namespace: str                   # 命名空间 (minecraft, mod:techguns)
    key: str                        # 翻译键名
    
    # 内容信息
    source_text: str                # 源文本 (通常为英文)
    target_text: Optional[str]      # 目标翻译文本
    target_language: str            # 目标语言代码 (zh_cn, en_us)
    
    # 上下文信息
    game_type: GameType             # 游戏类型 (minecraft, rimworld, factorio)
    mod_info: Optional[ModInfo]     # MOD信息
    file_path: str                  # 原始文件路径
    category: Optional[str]         # 分类 (item, block, entity)
    
    # 元数据
    version: int                    # 版本号
    last_modified: datetime         # 最后修改时间
    checksum: str                   # 内容校验和
    status: TranslationStatus       # 翻译状态 (pending, translated, reviewed)
    
    # 协作信息
    translator: Optional[str]       # 翻译者
    reviewer: Optional[str]         # 审核者
    comments: List[Comment]         # 评论和讨论

@dataclass
class TranslationProject:
    """翻译项目模型"""
    
    project_id: str                 # 项目标识
    name: str                      # 项目名称
    game_type: GameType            # 游戏类型
    source_language: str           # 源语言
    target_languages: List[str]    # 目标语言列表
    
    # 项目配置
    root_path: str                 # 项目根路径
    includes: List[str]            # 包含的MOD/包列表
    excludes: List[str]            # 排除的模式
    
    # 状态统计
    total_entries: int             # 总条目数
    translated_entries: int        # 已翻译数
    reviewed_entries: int          # 已审核数
    
    # 元数据
    created_at: datetime
    updated_at: datetime
    contributors: List[Contributor]

@dataclass
class TranslationDelta:
    """翻译变更记录"""
    
    delta_id: str                  # 变更标识
    project_id: str               # 项目标识
    base_version: int              # 基础版本
    target_version: int            # 目标版本
    
    # 变更内容
    added: List[TranslationEntry]     # 新增条目
    modified: List[TranslationEntry]  # 修改条目
    deleted: List[str]               # 删除的条目ID
    moved: List[EntryMove]           # 移动的条目
    
    # 元数据
    timestamp: datetime
    author: str
    commit_message: str
```

#### 游戏特定扩展

```python
# Minecraft扩展
@dataclass
class MinecraftModInfo(ModInfo):
    mod_id: str                    # MOD标识
    loader_type: ModLoader         # 加载器类型 (forge, fabric, quilt)
    mc_version: str               # Minecraft版本
    mod_version: str              # MOD版本
    
# RimWorld扩展  
@dataclass
class RimWorldModInfo(ModInfo):
    package_id: str               # 包标识
    mod_name: str                # MOD名称
    supported_versions: List[str] # 支持的游戏版本
    
# Factorio扩展
@dataclass
class FactorioModInfo(ModInfo):
    mod_name: str                # MOD名称
    factorio_version: str        # Factorio版本
    dependencies: List[str]      # 依赖列表
```

### 2. 翻译数据提取器架构

#### 提取器接口设计

```python
class ITranslationExtractor(Protocol):
    """翻译数据提取器接口"""
    
    async def extract_project(self, project_path: str) -> TranslationProject:
        """提取项目信息"""
        ...
    
    async def extract_entries(
        self, 
        project: TranslationProject,
        incremental: bool = True
    ) -> List[TranslationEntry]:
        """提取翻译条目"""
        ...
    
    async def detect_changes(
        self, 
        project: TranslationProject,
        last_scan: Optional[datetime] = None
    ) -> TranslationDelta:
        """检测翻译变更"""
        ...

class BaseTranslationExtractor:
    """提取器基类"""
    
    def __init__(self, game_type: GameType):
        self.game_type = game_type
        self.checksum_cache: Dict[str, str] = {}
    
    def _calculate_checksum(self, content: str) -> str:
        """计算内容校验和"""
        return blake3(content.encode()).hexdigest()
    
    def _normalize_key(self, key: str, namespace: str = None) -> str:
        """标准化翻译键"""
        if namespace and not key.startswith(namespace):
            return f"{namespace}.{key}"
        return key
    
    def _detect_encoding(self, file_path: str) -> str:
        """检测文件编码"""
        import chardet
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
            return result['encoding']
```

#### Minecraft数据提取器

```python
class MinecraftTranslationExtractor(BaseTranslationExtractor):
    """Minecraft翻译数据提取器"""
    
    def __init__(self):
        super().__init__(GameType.MINECRAFT)
        self.mod_loaders = {
            'forge': ForgeModLoader(),
            'fabric': FabricModLoader(), 
            'quilt': QuiltModLoader(),
            'neoforge': NeoForgeModLoader()
        }
    
    async def extract_project(self, project_path: str) -> TranslationProject:
        """提取Minecraft项目信息"""
        
        # 扫描目录结构
        mods = await self._scan_mods(project_path)
        
        # 检测MOD加载器类型
        loader_type = await self._detect_loader_type(project_path)
        
        # 统计翻译条目
        total_entries = await self._count_translation_entries(mods)
        
        return TranslationProject(
            project_id=self._generate_project_id(project_path),
            name=Path(project_path).name,
            game_type=GameType.MINECRAFT,
            source_language="en_us",
            target_languages=["zh_cn"],
            root_path=project_path,
            total_entries=total_entries,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    async def extract_entries(
        self, 
        project: TranslationProject,
        incremental: bool = True
    ) -> List[TranslationEntry]:
        """提取Minecraft翻译条目"""
        
        entries = []
        
        # 处理每个MOD
        for mod_path in await self._get_mod_paths(project.root_path):
            mod_info = await self._extract_mod_info(mod_path)
            
            # 提取语言文件
            lang_files = await self._find_language_files(mod_path)
            
            for lang_file in lang_files:
                lang_entries = await self._extract_language_file(
                    lang_file, mod_info
                )
                entries.extend(lang_entries)
        
        return entries
    
    async def _extract_language_file(
        self, 
        lang_file: Path,
        mod_info: MinecraftModInfo
    ) -> List[TranslationEntry]:
        """提取单个语言文件的翻译条目"""
        
        entries = []
        
        # 解析语言文件格式
        if lang_file.suffix == '.json':
            data = await self._parse_json_lang_file(lang_file)
        elif lang_file.suffix == '.lang':
            data = await self._parse_properties_lang_file(lang_file)
        else:
            return entries
        
        # 提取语言代码
        language = self._extract_language_code(lang_file)
        
        # 转换为翻译条目
        for key, value in data.items():
            entry = TranslationEntry(
                entry_id=self._generate_entry_id(mod_info.mod_id, key, language),
                namespace=mod_info.mod_id,
                key=key,
                source_text=value if language == "en_us" else "",
                target_text=value if language != "en_us" else None,
                target_language=language,
                game_type=GameType.MINECRAFT,
                mod_info=mod_info,
                file_path=str(lang_file),
                category=self._categorize_key(key),
                version=1,
                last_modified=datetime.fromtimestamp(lang_file.stat().st_mtime),
                checksum=self._calculate_checksum(value),
                status=TranslationStatus.TRANSLATED if language != "en_us" else TranslationStatus.SOURCE
            )
            entries.append(entry)
        
        return entries
```

### 3. 翻译数据同步器架构

#### 同步器接口设计

```python
class ITranslationSynchronizer(Protocol):
    """翻译数据同步器接口"""
    
    async def push_delta(
        self, 
        project_id: str,
        delta: TranslationDelta
    ) -> SyncResult:
        """推送翻译变更"""
        ...
    
    async def pull_delta(
        self, 
        project_id: str,
        since_version: int
    ) -> TranslationDelta:
        """拉取翻译变更"""
        ...
    
    async def sync_project(
        self, 
        project: TranslationProject,
        strategy: SyncStrategy = SyncStrategy.INCREMENTAL
    ) -> SyncResult:
        """同步项目翻译数据"""
        ...
    
    async def resolve_conflicts(
        self, 
        conflicts: List[TranslationConflict]
    ) -> List[TranslationEntry]:
        """解决翻译冲突"""
        ...

class TranslationSynchronizer:
    """翻译数据同步器实现"""
    
    def __init__(
        self,
        local_repo: ITranslationRepository,
        remote_client: IRemoteTranslationClient,
        conflict_resolver: IConflictResolver
    ):
        self.local_repo = local_repo
        self.remote_client = remote_client
        self.conflict_resolver = conflict_resolver
    
    async def sync_project(
        self, 
        project: TranslationProject,
        strategy: SyncStrategy = SyncStrategy.INCREMENTAL
    ) -> SyncResult:
        """同步项目翻译数据"""
        
        result = SyncResult(project_id=project.project_id)
        
        try:
            # 1. 获取本地和远程版本信息
            local_version = await self.local_repo.get_project_version(project.project_id)
            remote_version = await self.remote_client.get_project_version(project.project_id)
            
            # 2. 推送本地变更
            if local_version > remote_version:
                local_delta = await self.local_repo.get_delta(
                    project.project_id, 
                    remote_version, 
                    local_version
                )
                push_result = await self.remote_client.push_delta(project.project_id, local_delta)
                result.pushed_entries = len(local_delta.added) + len(local_delta.modified)
            
            # 3. 拉取远程变更
            if remote_version > local_version:
                remote_delta = await self.remote_client.pull_delta(
                    project.project_id, 
                    local_version
                )
                
                # 检测冲突
                conflicts = await self._detect_conflicts(remote_delta, local_version)
                
                if conflicts:
                    # 解决冲突
                    resolved_entries = await self.conflict_resolver.resolve_conflicts(conflicts)
                    result.conflicts_resolved = len(conflicts)
                
                # 应用远程变更
                await self.local_repo.apply_delta(remote_delta)
                result.pulled_entries = len(remote_delta.added) + len(remote_delta.modified)
            
            result.success = True
            
        except Exception as e:
            result.success = False
            result.error = str(e)
        
        return result
    
    async def _detect_conflicts(
        self, 
        remote_delta: TranslationDelta, 
        local_version: int
    ) -> List[TranslationConflict]:
        """检测翻译冲突"""
        
        conflicts = []
        
        # 检查修改冲突
        for remote_entry in remote_delta.modified:
            local_entry = await self.local_repo.get_entry(remote_entry.entry_id)
            
            if local_entry and local_entry.version > local_version:
                # 本地也有修改，产生冲突
                conflict = TranslationConflict(
                    entry_id=remote_entry.entry_id,
                    local_entry=local_entry,
                    remote_entry=remote_entry,
                    conflict_type=ConflictType.MODIFY_MODIFY
                )
                conflicts.append(conflict)
        
        return conflicts
```

### 4. API接口设计

#### 翻译数据传输API

```python
# FastAPI路由定义
@router.post("/api/v1/translations/extract")
async def extract_translation_data(
    request: ExtractRequest,
    extractor_service: ITranslationExtractorService = Depends()
) -> ExtractResponse:
    """提取翻译数据"""
    
    project = await extractor_service.extract_project(request.project_path)
    entries = await extractor_service.extract_entries(project, request.incremental)
    
    return ExtractResponse(
        success=True,
        data={
            "project": project,
            "entries": entries,
            "total_count": len(entries)
        }
    )

@router.post("/api/v1/translations/sync")
async def sync_translation_data(
    request: SyncRequest,
    sync_service: ITranslationSyncService = Depends()
) -> SyncResponse:
    """同步翻译数据"""
    
    result = await sync_service.sync_project(
        request.project_id, 
        request.strategy
    )
    
    return SyncResponse(
        success=result.success,
        data={
            "pushed_entries": result.pushed_entries,
            "pulled_entries": result.pulled_entries,
            "conflicts_resolved": result.conflicts_resolved
        }
    )

@router.get("/api/v1/translations/diff")
async def get_translation_diff(
    project_id: str,
    from_version: int,
    to_version: int,
    diff_service: ITranslationDiffService = Depends()
) -> DiffResponse:
    """获取翻译差异"""
    
    delta = await diff_service.get_delta(project_id, from_version, to_version)
    
    return DiffResponse(
        success=True,
        data={
            "delta": delta,
            "summary": {
                "added": len(delta.added),
                "modified": len(delta.modified),
                "deleted": len(delta.deleted),
                "moved": len(delta.moved)
            }
        }
    )

@router.post("/api/v1/translations/apply")
async def apply_translation_data(
    request: ApplyRequest,
    apply_service: ITranslationApplyService = Depends()
) -> ApplyResponse:
    """应用翻译数据到游戏文件"""
    
    result = await apply_service.apply_translations(
        request.project_id,
        request.entries,
        request.target_path
    )
    
    return ApplyResponse(
        success=result.success,
        data={
            "applied_files": result.applied_files,
            "applied_entries": result.applied_entries
        }
    )

@router.get("/api/v1/translations/status/{project_id}")
async def get_translation_status(
    project_id: str,
    status_service: ITranslationStatusService = Depends()
) -> StatusResponse:
    """获取翻译状态"""
    
    status = await status_service.get_project_status(project_id)
    
    return StatusResponse(
        success=True,
        data=status
    )
```

#### WebSocket实时同步

```python
@router.websocket("/api/v1/translations/realtime/{project_id}")
async def translation_realtime_sync(
    websocket: WebSocket,
    project_id: str,
    sync_service: ITranslationSyncService = Depends()
):
    """翻译数据实时同步"""
    
    await websocket.accept()
    
    try:
        # 注册WebSocket连接
        await sync_service.register_websocket(project_id, websocket)
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "translation_update":
                # 处理翻译更新
                entry = TranslationEntry.from_dict(data["entry"])
                await sync_service.update_entry(entry)
                
                # 广播给其他连接
                await sync_service.broadcast_update(project_id, entry, exclude=websocket)
                
            elif message_type == "sync_request":
                # 处理同步请求
                result = await sync_service.sync_project(project_id)
                await websocket.send_json({
                    "type": "sync_result",
                    "data": result.to_dict()
                })
    
    except WebSocketDisconnect:
        # 注销WebSocket连接
        await sync_service.unregister_websocket(project_id, websocket)
```

### 5. 数据传输优化策略

#### 压缩优化

```python
class TranslationDataCompressor:
    """翻译数据压缩器"""
    
    def __init__(self):
        # 为翻译文本创建专用字典
        self.translation_dict = self._build_translation_dict()
        self.zstd_compressor = zstd.ZstdCompressor(
            level=zstd.MAX_COMPRESSION_LEVEL,
            dict_data=self.translation_dict
        )
    
    def _build_translation_dict(self) -> bytes:
        """构建翻译文本专用压缩字典"""
        
        # 常见的翻译模式
        common_patterns = [
            # Minecraft常见词汇
            "minecraft", "item", "block", "entity", "gui", "tooltip",
            "enchantment", "effect", "advancement", "biome",
            
            # 常见翻译结构
            "%s", "%d", "{}", "[]", "()", 
            "the", "and", "or", "to", "of", "in", "for", "with",
            
            # 中文常见字符
            "的", "是", "了", "在", "有", "和", "中", "一个", "这个", "那个"
        ]
        
        # 构建训练文本
        training_text = " ".join(common_patterns).encode('utf-8')
        
        # 使用zstd训练字典
        return zstd.train_dictionary(1024 * 16, [training_text])
    
    def compress_entries(self, entries: List[TranslationEntry]) -> bytes:
        """压缩翻译条目列表"""
        
        # 序列化为JSON
        data = [entry.to_dict() for entry in entries]
        json_data = json.dumps(data, ensure_ascii=False)
        
        # 压缩
        return self.zstd_compressor.compress(json_data.encode('utf-8'))
    
    def decompress_entries(self, compressed_data: bytes) -> List[TranslationEntry]:
        """解压缩翻译条目列表"""
        
        # 解压缩
        decompressor = zstd.ZstdDecompressor(dict_data=self.translation_dict)
        json_data = decompressor.decompress(compressed_data).decode('utf-8')
        
        # 反序列化
        data = json.loads(json_data)
        return [TranslationEntry.from_dict(item) for item in data]
```

#### 增量传输优化

```python
class IncrementalTransferManager:
    """增量传输管理器"""
    
    def __init__(self, local_cache: ITranslationCache):
        self.local_cache = local_cache
    
    async def prepare_incremental_sync(
        self, 
        project_id: str,
        target_entries: List[TranslationEntry]
    ) -> IncrementalSyncPlan:
        """准备增量同步方案"""
        
        # 获取本地缓存的条目指纹
        local_fingerprints = await self.local_cache.get_entry_fingerprints(project_id)
        
        # 计算需要传输的条目
        to_download = []
        to_upload = []
        
        # 创建远程条目指纹映射
        remote_fingerprints = {
            entry.entry_id: entry.checksum 
            for entry in target_entries
        }
        
        # 检查需要下载的条目
        for entry in target_entries:
            local_checksum = local_fingerprints.get(entry.entry_id)
            if local_checksum != entry.checksum:
                to_download.append(entry.entry_id)
        
        # 检查需要上传的条目  
        local_entries = await self.local_cache.get_entries(project_id)
        for entry in local_entries:
            remote_checksum = remote_fingerprints.get(entry.entry_id)
            if remote_checksum != entry.checksum:
                to_upload.append(entry)
        
        return IncrementalSyncPlan(
            to_download=to_download,
            to_upload=to_upload,
            total_entries=len(target_entries),
            transfer_ratio=len(to_download + to_upload) / len(target_entries)
        )
```

## 技术实现要点

### 1. 性能优化

- **批量操作**：使用批量插入/更新减少数据库开销
- **索引优化**：在entry_id、project_id、checksum等字段建立索引
- **连接池**：使用连接池管理数据库和网络连接
- **异步处理**：全程使用异步I/O提高并发性能

### 2. 数据一致性

- **事务管理**：关键操作使用数据库事务保证原子性
- **冲突检测**：基于版本号和时间戳检测并发修改冲突
- **校验和验证**：使用BLAKE3校验和确保数据完整性
- **幂等操作**：所有同步操作支持安全重试

### 3. 扩展性设计

- **插件架构**：支持新游戏类型的扩展插件
- **策略模式**：冲突解决、压缩算法等使用策略模式
- **事件驱动**：使用事件总线解耦组件依赖
- **配置化**：关键参数支持运行时配置

### 4. 监控和调试

- **结构化日志**：使用structlog记录详细的操作日志
- **性能指标**：监控传输速度、压缩比、冲突率等指标
- **错误追踪**：详细的错误信息和堆栈跟踪
- **调试接口**：提供调试和诊断的API接口

## 预期收益

1. **传输效率**：相比文件传输减少90%以上数据量
2. **实时协作**：支持多人实时编辑翻译项目
3. **版本控制**：完整的翻译历史和回滚机制
4. **离线友好**：支持离线编辑和智能合并
5. **多游戏支持**：统一的数据模型支持多种游戏类型

这个新架构将显著提升TH-Suite的翻译协作效率，为用户提供现代化的翻译工作流体验。