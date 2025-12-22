# TH-Suite 修复需求文档

> **文档版本**: v1.0  
> **创建时间**: 2025-09-11  
> **基于审查**: V6数据库设计深度分析  
> **优先级分类**: P0(阻断) > P1(严重) > P2(重要) > P3(优化)

---

## 🎯 项目愿景理解

基于审查分析，TH-Suite的核心功能应该是：

### 🎮 Minecraft本地化工作流
```
扫描MOD/组合包 → 提取翻译键值 → 上传到服务器 → 
翻译处理 → 下载补丁 → 安全回写 → 验收与回滚
```

### 🔑 关键技术特性
- **内容寻址**: 基于BLAKE3的去重存储
- **统一标识**: UIDA架构支持跨版本一致性
- **智能同步**: Bloom过滤器优化的增量传输
- **3-way合并**: 支持冲突检测和解决
- **安全回写**: Overlay优先，支持JAR修改和回滚

---

## 🚨 P0级修复需求（阻断问题）

### 1. 数据一致性系统重构 ⚡

**问题**: UIDA哈希与CID映射机制存在根本性缺陷

**现状问题**:
```python
# 当前错误实现 - sync_service.py:72-75
if cid.startswith("blake3:"):
    uida_hash = cid[7:]  # 危险：直接截取
    entries = await self.translation_repo.find_by_uida_hash(uida_hash)
```

**修复方案**:
```python
class UidaCidMappingService:
    """UIDA-CID映射服务"""
    
    def __init__(self, uida_service, content_addressing):
        self.uida_service = uida_service
        self.content_addressing = content_addressing
        self.mapping_cache = LRUCache(maxsize=10000)
    
    async def generate_consistent_mapping(
        self, 
        translation_entry: TranslationEntry,
        mod_id: str,
        locale: str
    ) -> Tuple[ContentId, UidaComponents]:
        """生成一致的UIDA-CID映射"""
        
        # 1. 生成标准化的条目数据
        normalized_data = self._normalize_entry_data(translation_entry)
        
        # 2. 计算内容CID
        cid = self.content_addressing.compute_cid(normalized_data)
        
        # 3. 生成UIDA标识符
        uida = self.uida_service.generate_translation_entry_uida(
            mod_id=mod_id,
            translation_key=translation_entry.key,
            locale=locale
        )
        
        # 4. 验证映射一致性
        self._validate_mapping_consistency(cid, uida, normalized_data)
        
        # 5. 缓存映射关系
        self._cache_mapping(cid, uida)
        
        return cid, uida
    
    def _normalize_entry_data(self, entry: TranslationEntry) -> Dict[str, Any]:
        """标准化条目数据以确保一致的CID计算"""
        return {
            "key": entry.key,
            "src_text": entry.src_text,
            "dst_text": entry.dst_text or "",
            "status": entry.status,
            # 排除时间戳等易变字段
            "metadata": {
                "language_file_uid": entry.language_file_uid,
                "qa_flags": entry.qa_flags or {}
            }
        }
    
    async def verify_mapping_integrity(
        self, 
        cid: ContentId, 
        uida_hash: str,
        content_data: bytes
    ) -> bool:
        """验证CID-UIDA映射的完整性"""
        
        # 1. 验证CID
        expected_cid = self.content_addressing.compute_cid(content_data)
        if expected_cid != cid:
            logger.error("CID验证失败", 
                        expected=str(expected_cid), 
                        actual=str(cid))
            return False
        
        # 2. 查找映射关系
        cached_mapping = self._get_cached_mapping(cid)
        if cached_mapping and cached_mapping.uida_hash != uida_hash:
            logger.error("UIDA映射不一致", 
                        cached=cached_mapping.uida_hash,
                        provided=uida_hash)
            return False
        
        return True
```

**数据库Schema修改**:
```sql
-- 新增映射关系表
CREATE TABLE cid_uida_mappings (
    id INTEGER PRIMARY KEY,
    cid_algorithm TEXT NOT NULL,
    cid_hash TEXT NOT NULL,
    uida_hash TEXT NOT NULL,
    content_size INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified TIMESTAMP,
    verification_count INTEGER DEFAULT 0,
    
    UNIQUE(cid_algorithm, cid_hash, uida_hash),
    INDEX idx_cid_lookup (cid_algorithm, cid_hash),
    INDEX idx_uida_lookup (uida_hash)
);
```

### 2. 会话持久化系统 💾

**问题**: 同步会话和分片数据完全存储在内存中

**修复方案**:
```python
class PersistentSyncSessionManager:
    """持久化同步会话管理器"""
    
    def __init__(self, db_manager, storage_backend="sqlite"):
        self.db_manager = db_manager
        self.storage_backend = storage_backend
        self.session_cache = LRUCache(maxsize=100)
    
    async def create_session(
        self, 
        client_id: str, 
        session_id: str,
        ttl_hours: int = 1
    ) -> PersistentSyncSession:
        """创建持久化会话"""
        
        session = PersistentSyncSession(
            session_id=session_id,
            client_id=client_id,
            status="active",
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
            metadata={}
        )
        
        # 存储到数据库
        await self._store_session(session)
        
        # 创建分片存储目录
        await self._create_chunk_storage(session_id)
        
        return session
    
    async def store_chunk(
        self, 
        session_id: str, 
        cid: str, 
        chunk_index: int,
        chunk_data: bytes
    ) -> bool:
        """持久化存储分片数据"""
        
        # 验证会话
        session = await self.get_session(session_id)
        if not session or session.status != "active":
            return False
        
        # 计算分片存储路径
        chunk_path = self._get_chunk_path(session_id, cid, chunk_index)
        
        try:
            # 原子写入
            temp_path = f"{chunk_path}.tmp"
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(chunk_data)
            
            # 原子移动
            os.rename(temp_path, chunk_path)
            
            # 更新会话统计
            await self._update_session_progress(session_id, cid, chunk_index)
            
            return True
            
        except Exception as e:
            logger.error("分片存储失败", 
                        session_id=session_id,
                        cid=cid, 
                        chunk_index=chunk_index,
                        error=str(e))
            return False
    
    async def reconstruct_content(
        self, 
        session_id: str, 
        cid: str, 
        total_chunks: int
    ) -> Optional[bytes]:
        """重建完整内容并验证"""
        
        chunks = []
        
        for i in range(total_chunks):
            chunk_path = self._get_chunk_path(session_id, cid, i)
            
            if not os.path.exists(chunk_path):
                logger.error("分片缺失", 
                           session_id=session_id,
                           cid=cid, 
                           chunk_index=i)
                return None
            
            try:
                async with aiofiles.open(chunk_path, 'rb') as f:
                    chunk_data = await f.read()
                chunks.append(chunk_data)
            except Exception as e:
                logger.error("分片读取失败", 
                           session_id=session_id,
                           cid=cid,
                           chunk_index=i, 
                           error=str(e))
                return None
        
        # 重建完整内容
        full_content = b''.join(chunks)
        
        # CID完整性验证
        expected_cid = compute_cid(full_content, HashAlgorithm.BLAKE3)
        if str(expected_cid) != cid:
            logger.error("内容完整性验证失败",
                       session_id=session_id,
                       expected_cid=str(expected_cid),
                       actual_cid=cid)
            return None
        
        return full_content
```

**数据库Schema**:
```sql
-- 持久化会话表
CREATE TABLE sync_sessions (
    session_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'expired', 'error')),
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_cids INTEGER DEFAULT 0,
    completed_cids INTEGER DEFAULT 0,
    chunk_size_bytes INTEGER NOT NULL,
    metadata JSON,
    
    INDEX idx_client_sessions (client_id, created_at),
    INDEX idx_active_sessions (status, expires_at)
);

-- 分片进度追踪表
CREATE TABLE session_chunk_progress (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    cid TEXT NOT NULL,
    total_chunks INTEGER NOT NULL,
    received_chunks INTEGER DEFAULT 0,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES sync_sessions(session_id),
    UNIQUE (session_id, cid)
);
```

### 3. 端到端数据验证系统 🔒

**问题**: 分片重组后缺乏完整性验证

**修复方案**:
```python
class ContentIntegrityValidator:
    """内容完整性验证器"""
    
    def __init__(self):
        self.validation_cache = LRUCache(maxsize=1000)
    
    async def validate_upload_pipeline(
        self,
        chunks: List[bytes],
        expected_cid: str,
        expected_uida_hash: str,
        metadata: Dict[str, Any]
    ) -> ValidationResult:
        """端到端上传流水线验证"""
        
        result = ValidationResult()
        
        try:
            # 1. 分片完整性检查
            chunk_validation = await self._validate_chunks(chunks)
            result.add_check("chunk_integrity", chunk_validation)
            
            # 2. 内容重建验证
            full_content = b''.join(chunks)
            content_validation = await self._validate_content_cid(
                full_content, expected_cid
            )
            result.add_check("content_cid", content_validation)
            
            # 3. UIDA一致性验证
            uida_validation = await self._validate_uida_consistency(
                full_content, expected_uida_hash, metadata
            )
            result.add_check("uida_consistency", uida_validation)
            
            # 4. Entry-Delta格式验证
            delta_validation = await self._validate_entry_delta_format(
                full_content
            )
            result.add_check("delta_format", delta_validation)
            
            # 5. 业务规则验证
            business_validation = await self._validate_business_rules(
                full_content, metadata
            )
            result.add_check("business_rules", business_validation)
            
        except Exception as e:
            result.add_error(f"验证过程异常: {str(e)}")
        
        return result
    
    async def _validate_chunks(self, chunks: List[bytes]) -> CheckResult:
        """验证分片完整性"""
        
        if not chunks:
            return CheckResult(False, "分片列表为空")
        
        # 检查每个分片的BLAKE3哈希
        for i, chunk in enumerate(chunks):
            if not chunk:
                return CheckResult(False, f"分片{i}为空")
            
            # 计算分片哈希并验证
            chunk_hash = blake3.blake3(chunk).hexdigest()
            # 这里需要与上传时提供的分片哈希进行比对
            
        return CheckResult(True, f"所有{len(chunks)}个分片验证通过")
    
    async def _validate_entry_delta_format(self, content: bytes) -> CheckResult:
        """验证Entry-Delta格式"""
        
        try:
            from api.v6.sync.entry_delta import get_entry_delta_processor
            processor = get_entry_delta_processor()
            
            deltas = processor.parse_delta_payload(content)
            
            if not deltas:
                return CheckResult(False, "Entry-Delta列表为空")
            
            # 验证每个delta的必需字段
            for i, delta in enumerate(deltas):
                if not delta.entry_uid:
                    return CheckResult(False, f"Delta{i}缺少entry_uid")
                if not delta.uida_hash:
                    return CheckResult(False, f"Delta{i}缺少uida_hash")
                if not delta.key:
                    return CheckResult(False, f"Delta{i}缺少translation key")
            
            return CheckResult(True, f"Entry-Delta格式验证通过，包含{len(deltas)}个条目")
            
        except Exception as e:
            return CheckResult(False, f"Entry-Delta解析失败: {str(e)}")

@dataclass
class ValidationResult:
    """验证结果"""
    checks: Dict[str, CheckResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_check(self, name: str, result: CheckResult):
        self.checks[name] = result
        if not result.passed:
            self.errors.append(f"{name}: {result.message}")
    
    def add_error(self, error: str):
        self.errors.append(error)
    
    def is_valid(self) -> bool:
        return len(self.errors) == 0 and all(
            check.passed for check in self.checks.values()
        )
```

---

## 🟡 P1级修复需求（严重问题）

### 4. 智能3-way合并系统

**问题**: 缺少base版本信息，冲突解决不完善

**修复方案**:
```python
class Enhanced3WayMerger:
    """增强的3-way合并器"""
    
    async def perform_intelligent_merge(
        self,
        merge_context: Enhanced3WayContext
    ) -> Enhanced3WayResult:
        """执行智能3-way合并"""
        
        # 1. 构建完整的版本历史
        version_history = await self._build_version_history(merge_context)
        
        # 2. 识别真正的base版本
        true_base = await self._identify_true_base(version_history)
        
        # 3. 执行语义级别的差异分析
        semantic_diff = await self._analyze_semantic_differences(
            true_base, merge_context.local_entry, merge_context.remote_entry
        )
        
        # 4. 应用智能合并策略
        merge_result = await self._apply_intelligent_strategies(
            semantic_diff, merge_context.merge_options
        )
        
        return merge_result
    
    async def _analyze_semantic_differences(
        self,
        base: TranslationEntry,
        local: TranslationEntry,
        remote: TranslationEntry
    ) -> SemanticDiff:
        """分析语义级差异"""
        
        diff = SemanticDiff()
        
        # 文本语义变化分析
        if base and local:
            local_changes = self._analyze_text_changes(base.dst_text, local.dst_text)
            diff.local_changes = local_changes
        
        if base and remote:
            remote_changes = self._analyze_text_changes(base.dst_text, remote.dst_text)
            diff.remote_changes = remote_changes
        
        # 冲突类型分类
        diff.conflict_type = self._classify_conflict(diff.local_changes, diff.remote_changes)
        
        # 生成合并建议
        diff.merge_suggestions = self._generate_merge_suggestions(diff)
        
        return diff
    
    def _classify_conflict(
        self, 
        local_changes: TextChanges, 
        remote_changes: TextChanges
    ) -> ConflictType:
        """分类冲突类型"""
        
        if local_changes.is_formatting_only and remote_changes.is_formatting_only:
            return ConflictType.FORMATTING_CONFLICT
        elif local_changes.is_terminology_change or remote_changes.is_terminology_change:
            return ConflictType.TERMINOLOGY_CONFLICT
        elif local_changes.has_placeholder_changes or remote_changes.has_placeholder_changes:
            return ConflictType.PLACEHOLDER_CONFLICT
        else:
            return ConflictType.CONTENT_CONFLICT
```

### 5. Bloom过滤器优化系统

**修复方案**:
```python
class AdaptiveBloomFilter:
    """自适应Bloom过滤器"""
    
    def __init__(self, target_fpr: float = 0.001):
        self.target_fpr = target_fpr
        self.optimization_enabled = True
    
    async def optimize_for_dataset(
        self, 
        expected_items: int,
        available_memory: int
    ) -> BloomConfig:
        """根据数据集优化Bloom过滤器配置"""
        
        # 计算最优参数
        optimal_bits = self._calculate_optimal_bits(expected_items, self.target_fpr)
        optimal_hashes = self._calculate_optimal_hashes(optimal_bits, expected_items)
        
        # 内存约束检查
        required_memory = optimal_bits // 8
        if required_memory > available_memory:
            # 内存受限时降级处理
            optimal_bits = available_memory * 8
            optimal_hashes = self._calculate_optimal_hashes(optimal_bits, expected_items)
            actual_fpr = self._calculate_actual_fpr(optimal_bits, optimal_hashes, expected_items)
            logger.warning("内存限制导致FPR上升", 
                         target_fpr=self.target_fpr,
                         actual_fpr=actual_fpr)
        
        return BloomConfig(
            bits=optimal_bits,
            hashes=optimal_hashes,
            expected_items=expected_items,
            target_fpr=self.target_fpr
        )
    
    async def handle_false_positives(
        self,
        client_bloom: BloomFilter,
        server_cids: List[str],
        client_actual_cids: Set[str]
    ) -> FalsePositiveReport:
        """处理假阳性情况"""
        
        false_positives = []
        
        for cid in server_cids:
            if client_bloom.might_contain(cid):
                # Bloom说客户端有，验证客户端是否真的有
                if cid not in client_actual_cids:
                    false_positives.append(cid)
        
        # 生成假阳性报告
        report = FalsePositiveReport(
            total_server_cids=len(server_cids),
            bloom_positive_count=len([cid for cid in server_cids if client_bloom.might_contain(cid)]),
            false_positive_count=len(false_positives),
            actual_fpr=len(false_positives) / len(server_cids) if server_cids else 0,
            false_positive_cids=false_positives[:10]  # 只记录前10个用于调试
        )
        
        return report
```

### 6. 数据库并发优化

**修复方案**:
```python
class OptimizedDatabaseManager:
    """优化的数据库管理器"""
    
    def __init__(self, db_path: str, connection_pool_size: int = 10):
        self.db_path = db_path
        self.connection_pool = None
        self.write_queue = asyncio.Queue(maxsize=1000)
        self.batch_processor = None
    
    async def initialize(self):
        """初始化数据库管理器"""
        
        # 创建连接池
        self.connection_pool = await self._create_connection_pool()
        
        # 启动批量写入处理器
        self.batch_processor = asyncio.create_task(self._process_write_batches())
        
        # 优化SQLite配置
        await self._optimize_sqlite_settings()
    
    async def _optimize_sqlite_settings(self):
        """优化SQLite设置"""
        
        async with self.get_write_connection() as conn:
            # 优化设置
            await conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            await conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全
            await conn.execute("PRAGMA cache_size=10000")   # 增加缓存
            await conn.execute("PRAGMA temp_store=MEMORY")   # 临时表存储在内存
            await conn.execute("PRAGMA mmap_size=268435456") # 256MB内存映射
            await conn.commit()
    
    async def batch_insert_entries(
        self, 
        entries: List[TranslationEntry]
    ) -> int:
        """批量插入翻译条目"""
        
        if not entries:
            return 0
        
        # 使用事务批量插入
        async with self.get_write_connection() as conn:
            try:
                await conn.execute("BEGIN TRANSACTION")
                
                insert_sql = """
                INSERT OR REPLACE INTO core_translation_entries 
                (uid, language_file_uid, key, src_text, dst_text, status, 
                 qa_flags, updated_at, uida_keys_b64, uida_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                batch_data = [
                    (
                        entry.uid, entry.language_file_uid, entry.key,
                        entry.src_text, entry.dst_text, entry.status,
                        json.dumps(entry.qa_flags or {}), entry.updated_at,
                        entry.uida_keys_b64, entry.uida_hash, entry.created_at
                    )
                    for entry in entries
                ]
                
                await conn.executemany(insert_sql, batch_data)
                await conn.execute("COMMIT")
                
                return len(entries)
                
            except Exception as e:
                await conn.execute("ROLLBACK")
                logger.error("批量插入失败", error=str(e))
                raise
```

---

## 🟠 P2级修复需求（重要优化）

### 7. 性能监控系统

**建议实现**:
```python
class PerformanceMonitor:
    """性能监控系统"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.alerts = []
    
    async def monitor_sync_performance(
        self,
        session_id: str,
        operation: str,
        duration: float,
        data_size: int
    ):
        """监控同步性能"""
        
        metric = PerformanceMetric(
            session_id=session_id,
            operation=operation,
            duration=duration,
            data_size=data_size,
            timestamp=time.time(),
            throughput=data_size / duration if duration > 0 else 0
        )
        
        self.metrics[operation].append(metric)
        
        # 性能告警检查
        await self._check_performance_alerts(operation, metric)
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "operations": {},
            "summary": {},
            "alerts": self.alerts[-10:]  # 最近10个告警
        }
        
        for operation, metrics in self.metrics.items():
            if metrics:
                durations = [m.duration for m in metrics]
                throughputs = [m.throughput for m in metrics if m.throughput > 0]
                
                report["operations"][operation] = {
                    "count": len(metrics),
                    "avg_duration": statistics.mean(durations),
                    "p95_duration": statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else durations[0],
                    "avg_throughput": statistics.mean(throughputs) if throughputs else 0,
                    "total_data_size": sum(m.data_size for m in metrics)
                }
        
        return report
```

### 8. 容错与恢复系统

**建议实现**:
```python
class FaultToleranceManager:
    """容错与恢复管理器"""
    
    async def recover_interrupted_session(
        self,
        session_id: str
    ) -> RecoveryResult:
        """恢复中断的同步会话"""
        
        try:
            # 1. 查找会话状态
            session = await self._find_interrupted_session(session_id)
            if not session:
                return RecoveryResult(False, "会话不存在")
            
            # 2. 检查已存储的分片
            stored_chunks = await self._scan_stored_chunks(session_id)
            
            # 3. 验证已存储分片的完整性
            validated_chunks = await self._validate_stored_chunks(stored_chunks)
            
            # 4. 重建可恢复的内容
            recoverable_cids = await self._identify_recoverable_cids(validated_chunks)
            
            # 5. 更新会话恢复状态
            recovery_session = await self._create_recovery_session(
                session, recoverable_cids
            )
            
            return RecoveryResult(
                True, 
                f"恢复{len(recoverable_cids)}个CID，需要重传其余内容",
                recovery_session
            )
            
        except Exception as e:
            logger.error("会话恢复失败", session_id=session_id, error=str(e))
            return RecoveryResult(False, f"恢复失败: {str(e)}")
```

---

## 🔧 实施建议

### 立即行动计划（1-2周）

1. **停用当前V6生产环境**
2. **实施P0级修复**：
   - UIDA-CID映射系统重构
   - 会话持久化实现
   - 端到端验证系统

### 短期计划（2-4周）

1. **P1级问题修复**：
   - 智能3-way合并
   - Bloom过滤器优化
   - 数据库并发优化

### 中期计划（1-2月）

1. **P2级优化实施**：
   - 性能监控系统
   - 容错恢复机制
   - 全面测试覆盖

### 质量保证

1. **测试策略**：
   - 单元测试覆盖率 ≥ 90%
   - 集成测试覆盖关键数据流
   - 压力测试验证并发性能
   - 灾难恢复测试

2. **监控指标**：
   - 数据一致性检查
   - 同步成功率
   - 平均响应时间
   - 错误率和恢复时间

**结论**: TH-Suite具有很强的技术潜力，但当前V6实现存在严重的数据安全问题。按照此修复计划实施后，将成为一个可靠的Minecraft本地化工具平台。