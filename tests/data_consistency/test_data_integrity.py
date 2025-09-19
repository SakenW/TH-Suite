"""
数据一致性和完整性测试套件
验证数据同步、版本控制和冲突解决机制
"""
import pytest
import asyncio
import json
import hashlib
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import tempfile
from dataclasses import dataclass, asdict

from apps.mc_l10n.backend.infrastructure.services.simple_minecraft_scanner import SimpleMinecraftScanner


@dataclass
class TranslationEntry:
    """翻译条目数据类"""
    id: str
    key: str
    source_text: str
    target_text: str
    source_language: str
    target_language: str
    version: int
    last_modified: float
    checksum: str
    status: str = "pending"
    translator: Optional[str] = None
    reviewer: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def calculate_checksum(self) -> str:
        """计算数据校验和"""
        data_to_hash = f"{self.key}{self.source_text}{self.target_text}{self.version}"
        return hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()
    
    def update_checksum(self):
        """更新校验和"""
        self.checksum = self.calculate_checksum()
    
    def is_valid(self) -> bool:
        """验证数据完整性"""
        return self.checksum == self.calculate_checksum()


class DataIntegrityValidator:
    """数据完整性验证器"""
    
    def __init__(self):
        self.validation_errors = []
    
    def validate_translation_entry(self, entry: TranslationEntry) -> bool:
        """验证单个翻译条目"""
        errors = []
        
        # 检查必填字段
        if not entry.id:
            errors.append("缺少ID")
        if not entry.key:
            errors.append("缺少翻译键")
        if not entry.source_text:
            errors.append("缺少源文本")
        if not entry.source_language:
            errors.append("缺少源语言")
        if not entry.target_language:
            errors.append("缺少目标语言")
        
        # 检查版本号
        if entry.version < 1:
            errors.append("版本号必须大于0")
        
        # 检查时间戳
        if entry.last_modified <= 0:
            errors.append("无效的修改时间")
        
        # 检查校验和
        if not entry.is_valid():
            errors.append("校验和不匹配")
        
        # 检查状态值
        valid_statuses = ["pending", "in_progress", "completed", "review", "approved", "rejected"]
        if entry.status not in valid_statuses:
            errors.append(f"无效的状态: {entry.status}")
        
        if errors:
            self.validation_errors.extend([f"条目 {entry.id}: {error}" for error in errors])
            return False
        
        return True
    
    def validate_translation_consistency(self, entries: List[TranslationEntry]) -> bool:
        """验证翻译条目一致性"""
        errors = []
        
        # 检查重复ID
        ids = [entry.id for entry in entries]
        duplicate_ids = set([id for id in ids if ids.count(id) > 1])
        if duplicate_ids:
            errors.append(f"发现重复ID: {duplicate_ids}")
        
        # 检查重复键（同一语言对）
        language_keys = {}
        for entry in entries:
            lang_pair = f"{entry.source_language}-{entry.target_language}"
            if lang_pair not in language_keys:
                language_keys[lang_pair] = []
            language_keys[lang_pair].append(entry.key)
        
        for lang_pair, keys in language_keys.items():
            duplicate_keys = set([key for key in keys if keys.count(key) > 1])
            if duplicate_keys:
                errors.append(f"语言对 {lang_pair} 中发现重复键: {duplicate_keys}")
        
        if errors:
            self.validation_errors.extend(errors)
            return False
        
        return True
    
    def get_validation_report(self) -> Dict[str, Any]:
        """获取验证报告"""
        return {
            "total_errors": len(self.validation_errors),
            "errors": self.validation_errors,
            "is_valid": len(self.validation_errors) == 0
        }


class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self):
        self.conflict_resolution_strategies = {
            "accept_local": self._accept_local,
            "accept_remote": self._accept_remote,
            "merge_content": self._merge_content,
            "manual_review": self._manual_review
        }
    
    def detect_conflicts(self, local_entries: List[TranslationEntry], 
                        remote_entries: List[TranslationEntry]) -> List[Dict[str, Any]]:
        """检测冲突"""
        conflicts = []
        
        # 创建索引
        local_index = {entry.key: entry for entry in local_entries}
        remote_index = {entry.key: entry for entry in remote_entries}
        
        # 检查所有键
        all_keys = set(local_index.keys()) | set(remote_index.keys())
        
        for key in all_keys:
            local_entry = local_index.get(key)
            remote_entry = remote_index.get(key)
            
            if local_entry and remote_entry:
                # 检查版本冲突
                if local_entry.version != remote_entry.version:
                    conflicts.append({
                        "type": "version_conflict",
                        "key": key,
                        "local": local_entry.to_dict(),
                        "remote": remote_entry.to_dict(),
                        "description": f"版本冲突: 本地 {local_entry.version} vs 远程 {remote_entry.version}"
                    })
                
                # 检查内容冲突
                elif (local_entry.target_text != remote_entry.target_text and 
                      local_entry.last_modified != remote_entry.last_modified):
                    conflicts.append({
                        "type": "content_conflict",
                        "key": key,
                        "local": local_entry.to_dict(),
                        "remote": remote_entry.to_dict(),
                        "description": "内容和时间戳都不同"
                    })
            
            elif local_entry and not remote_entry:
                conflicts.append({
                    "type": "local_only",
                    "key": key,
                    "local": local_entry.to_dict(),
                    "remote": None,
                    "description": "仅存在于本地"
                })
            
            elif not local_entry and remote_entry:
                conflicts.append({
                    "type": "remote_only",
                    "key": key,
                    "local": None,
                    "remote": remote_entry.to_dict(),
                    "description": "仅存在于远程"
                })
        
        return conflicts
    
    def resolve_conflict(self, conflict: Dict[str, Any], strategy: str) -> Optional[TranslationEntry]:
        """解决单个冲突"""
        if strategy not in self.conflict_resolution_strategies:
            raise ValueError(f"未知的冲突解决策略: {strategy}")
        
        return self.conflict_resolution_strategies[strategy](conflict)
    
    def _accept_local(self, conflict: Dict[str, Any]) -> Optional[TranslationEntry]:
        """接受本地版本"""
        if conflict["local"]:
            return TranslationEntry(**conflict["local"])
        return None
    
    def _accept_remote(self, conflict: Dict[str, Any]) -> Optional[TranslationEntry]:
        """接受远程版本"""
        if conflict["remote"]:
            return TranslationEntry(**conflict["remote"])
        return None
    
    def _merge_content(self, conflict: Dict[str, Any]) -> Optional[TranslationEntry]:
        """合并内容"""
        if not conflict["local"] or not conflict["remote"]:
            return self._accept_remote(conflict) or self._accept_local(conflict)
        
        local = TranslationEntry(**conflict["local"])
        remote = TranslationEntry(**conflict["remote"])
        
        # 简单的合并策略：使用更新的版本
        if remote.last_modified > local.last_modified:
            merged = remote
        else:
            merged = local
        
        # 更新版本号和时间戳
        merged.version = max(local.version, remote.version) + 1
        merged.last_modified = time.time()
        merged.update_checksum()
        
        return merged
    
    def _manual_review(self, conflict: Dict[str, Any]) -> Optional[TranslationEntry]:
        """标记为需要手动审查"""
        if conflict["local"]:
            entry = TranslationEntry(**conflict["local"])
            entry.status = "manual_review_required"
            entry.last_modified = time.time()
            entry.update_checksum()
            return entry
        return None


class TestDataIntegrityValidation:
    """数据完整性验证测试"""
    
    def test_translation_entry_validation(self):
        """测试翻译条目验证"""
        validator = DataIntegrityValidator()
        
        # 创建有效的翻译条目
        valid_entry = TranslationEntry(
            id="entry_1",
            key="item.test_mod.test_item",
            source_text="Test Item",
            target_text="测试物品",
            source_language="en_us",
            target_language="zh_cn",
            version=1,
            last_modified=time.time(),
            checksum=""
        )
        valid_entry.update_checksum()
        
        # 验证有效条目
        assert validator.validate_translation_entry(valid_entry)
        
        # 创建无效的翻译条目
        invalid_entry = TranslationEntry(
            id="",  # 空ID
            key="",  # 空键
            source_text="Test",
            target_text="测试",
            source_language="en_us",
            target_language="zh_cn",
            version=0,  # 无效版本
            last_modified=-1,  # 无效时间
            checksum="invalid_checksum"  # 错误校验和
        )
        
        # 验证无效条目
        assert not validator.validate_translation_entry(invalid_entry)
        
        # 检查错误报告
        report = validator.get_validation_report()
        assert not report["is_valid"]
        assert report["total_errors"] > 0
    
    def test_translation_consistency_validation(self):
        """测试翻译一致性验证"""
        validator = DataIntegrityValidator()
        
        # 创建测试条目
        entries = [
            TranslationEntry(
                id="entry_1",
                key="item.test.item1",
                source_text="Item 1",
                target_text="物品 1",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=time.time(),
                checksum=""
            ),
            TranslationEntry(
                id="entry_2",
                key="item.test.item2",
                source_text="Item 2",
                target_text="物品 2",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=time.time(),
                checksum=""
            ),
            # 重复ID
            TranslationEntry(
                id="entry_1",  # 重复ID
                key="item.test.item3",
                source_text="Item 3",
                target_text="物品 3",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=time.time(),
                checksum=""
            ),
            # 重复键
            TranslationEntry(
                id="entry_4",
                key="item.test.item1",  # 重复键
                source_text="Item 1 Duplicate",
                target_text="物品 1 重复",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=time.time(),
                checksum=""
            )
        ]
        
        # 更新所有校验和
        for entry in entries:
            entry.update_checksum()
        
        # 验证一致性
        assert not validator.validate_translation_consistency(entries)
        
        # 检查错误
        report = validator.get_validation_report()
        assert not report["is_valid"]
        assert "重复ID" in str(report["errors"])
        assert "重复键" in str(report["errors"])
    
    def test_checksum_integrity(self):
        """测试校验和完整性"""
        entry = TranslationEntry(
            id="checksum_test",
            key="test.checksum",
            source_text="Original Text",
            target_text="原始文本",
            source_language="en_us",
            target_language="zh_cn",
            version=1,
            last_modified=time.time(),
            checksum=""
        )
        
        # 生成正确的校验和
        entry.update_checksum()
        original_checksum = entry.checksum
        
        # 验证正确的校验和
        assert entry.is_valid()
        
        # 修改内容但不更新校验和
        entry.target_text = "修改后的文本"
        
        # 验证校验和不匹配
        assert not entry.is_valid()
        
        # 更新校验和
        entry.update_checksum()
        
        # 验证新的校验和正确
        assert entry.is_valid()
        assert entry.checksum != original_checksum


class TestConflictResolution:
    """冲突解决测试"""
    
    def test_conflict_detection(self):
        """测试冲突检测"""
        resolver = ConflictResolver()
        
        # 创建本地条目
        local_entries = [
            TranslationEntry(
                id="local_1",
                key="item.test.item1",
                source_text="Item 1",
                target_text="物品 1",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=1000,
                checksum=""
            ),
            TranslationEntry(
                id="local_2",
                key="item.test.item2",
                source_text="Item 2",
                target_text="物品 2",
                source_language="en_us",
                target_language="zh_cn",
                version=2,
                last_modified=2000,
                checksum=""
            ),
            TranslationEntry(
                id="local_3",
                key="item.test.local_only",
                source_text="Local Only",
                target_text="仅本地",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=3000,
                checksum=""
            )
        ]
        
        # 创建远程条目
        remote_entries = [
            TranslationEntry(
                id="remote_1",
                key="item.test.item1",
                source_text="Item 1",
                target_text="物品 1（更新）",
                source_language="en_us",
                target_language="zh_cn",
                version=2,  # 版本冲突
                last_modified=1500,
                checksum=""
            ),
            TranslationEntry(
                id="remote_2",
                key="item.test.item2",
                source_text="Item 2",
                target_text="物品 2（不同）",
                source_language="en_us",
                target_language="zh_cn",
                version=2,
                last_modified=2500,  # 内容冲突
                checksum=""
            ),
            TranslationEntry(
                id="remote_3",
                key="item.test.remote_only",
                source_text="Remote Only",
                target_text="仅远程",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=4000,
                checksum=""
            )
        ]
        
        # 更新校验和
        for entry in local_entries + remote_entries:
            entry.update_checksum()
        
        # 检测冲突
        conflicts = resolver.detect_conflicts(local_entries, remote_entries)
        
        # 验证冲突类型
        conflict_types = [conflict["type"] for conflict in conflicts]
        assert "version_conflict" in conflict_types
        assert "content_conflict" in conflict_types
        assert "local_only" in conflict_types
        assert "remote_only" in conflict_types
        
        # 验证冲突数量
        assert len(conflicts) == 4
    
    def test_conflict_resolution_strategies(self):
        """测试冲突解决策略"""
        resolver = ConflictResolver()
        
        # 创建冲突场景
        local_entry = TranslationEntry(
            id="conflict_test",
            key="item.test.conflict",
            source_text="Conflict Test",
            target_text="冲突测试（本地）",
            source_language="en_us",
            target_language="zh_cn",
            version=1,
            last_modified=1000,
            checksum=""
        )
        local_entry.update_checksum()
        
        remote_entry = TranslationEntry(
            id="conflict_test",
            key="item.test.conflict",
            source_text="Conflict Test",
            target_text="冲突测试（远程）",
            source_language="en_us",
            target_language="zh_cn",
            version=2,
            last_modified=1500,
            checksum=""
        )
        remote_entry.update_checksum()
        
        conflict = {
            "type": "version_conflict",
            "key": "item.test.conflict",
            "local": local_entry.to_dict(),
            "remote": remote_entry.to_dict()
        }
        
        # 测试接受本地策略
        resolved_local = resolver.resolve_conflict(conflict, "accept_local")
        assert resolved_local.target_text == "冲突测试（本地）"
        assert resolved_local.version == 1
        
        # 测试接受远程策略
        resolved_remote = resolver.resolve_conflict(conflict, "accept_remote")
        assert resolved_remote.target_text == "冲突测试（远程）"
        assert resolved_remote.version == 2
        
        # 测试合并策略
        resolved_merged = resolver.resolve_conflict(conflict, "merge_content")
        assert resolved_merged.version == 3  # 版本应该递增
        assert resolved_merged.target_text == "冲突测试（远程）"  # 使用更新的版本
        
        # 测试手动审查策略
        resolved_manual = resolver.resolve_conflict(conflict, "manual_review")
        assert resolved_manual.status == "manual_review_required"
    
    def test_batch_conflict_resolution(self):
        """测试批量冲突解决"""
        resolver = ConflictResolver()
        
        # 创建多个冲突
        conflicts = []
        for i in range(5):
            local_entry = TranslationEntry(
                id=f"conflict_{i}",
                key=f"item.test.item{i}",
                source_text=f"Item {i}",
                target_text=f"物品 {i}（本地）",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=1000 + i,
                checksum=""
            )
            local_entry.update_checksum()
            
            remote_entry = TranslationEntry(
                id=f"conflict_{i}",
                key=f"item.test.item{i}",
                source_text=f"Item {i}",
                target_text=f"物品 {i}（远程）",
                source_language="en_us",
                target_language="zh_cn",
                version=2,
                last_modified=1500 + i,
                checksum=""
            )
            remote_entry.update_checksum()
            
            conflicts.append({
                "type": "version_conflict",
                "key": f"item.test.item{i}",
                "local": local_entry.to_dict(),
                "remote": remote_entry.to_dict()
            })
        
        # 批量解决冲突
        resolution_strategies = ["accept_local", "accept_remote", "merge_content"]
        resolved_entries = []
        
        for i, conflict in enumerate(conflicts):
            strategy = resolution_strategies[i % len(resolution_strategies)]
            resolved = resolver.resolve_conflict(conflict, strategy)
            resolved_entries.append(resolved)
        
        # 验证解决结果
        assert len(resolved_entries) == 5
        
        # 验证不同策略的结果
        assert resolved_entries[0].target_text == "物品 0（本地）"  # accept_local
        assert resolved_entries[1].target_text == "物品 1（远程）"  # accept_remote
        assert resolved_entries[2].version == 3  # merge_content
        assert resolved_entries[3].target_text == "物品 3（本地）"  # accept_local
        assert resolved_entries[4].target_text == "物品 4（远程）"  # accept_remote


class TestDataSynchronization:
    """数据同步测试"""
    
    async def test_incremental_sync(self):
        """测试增量同步"""
        # 模拟初始数据集
        initial_data = [
            TranslationEntry(
                id=f"entry_{i}",
                key=f"item.test.item{i}",
                source_text=f"Item {i}",
                target_text=f"物品 {i}",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=1000 + i,
                checksum=""
            )
            for i in range(10)
        ]
        
        for entry in initial_data:
            entry.update_checksum()
        
        # 模拟同步点
        last_sync_time = 1005
        
        # 创建增量更新
        incremental_updates = []
        for i in range(3, 8):  # 更新部分条目
            updated_entry = TranslationEntry(
                id=f"entry_{i}",
                key=f"item.test.item{i}",
                source_text=f"Item {i}",
                target_text=f"物品 {i}（已更新）",
                source_language="en_us",
                target_language="zh_cn",
                version=2,
                last_modified=2000 + i,  # 新的时间戳
                checksum=""
            )
            updated_entry.update_checksum()
            incremental_updates.append(updated_entry)
        
        # 添加新条目
        new_entry = TranslationEntry(
            id="entry_new",
            key="item.test.new_item",
            source_text="New Item",
            target_text="新物品",
            source_language="en_us",
            target_language="zh_cn",
            version=1,
            last_modified=2010,
            checksum=""
        )
        new_entry.update_checksum()
        incremental_updates.append(new_entry)
        
        # 模拟增量同步
        def get_incremental_updates(since: float) -> List[TranslationEntry]:
            return [entry for entry in incremental_updates if entry.last_modified > since]
        
        # 获取增量更新
        updates = get_incremental_updates(last_sync_time)
        
        # 验证增量同步结果
        assert len(updates) == 6  # 5个更新 + 1个新增
        
        # 验证更新的条目
        updated_keys = [entry.key for entry in updates if entry.key.startswith("item.test.item")]
        assert len(updated_keys) == 5
        
        # 验证新增的条目
        new_keys = [entry.key for entry in updates if entry.key == "item.test.new_item"]
        assert len(new_keys) == 1
    
    async def test_bidirectional_sync(self):
        """测试双向同步"""
        resolver = ConflictResolver()
        
        # 模拟本地更改
        local_changes = [
            TranslationEntry(
                id="change_1",
                key="item.test.local_change",
                source_text="Local Change",
                target_text="本地更改",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=1500,
                checksum=""
            )
        ]
        
        # 模拟远程更改
        remote_changes = [
            TranslationEntry(
                id="change_2",
                key="item.test.remote_change",
                source_text="Remote Change",
                target_text="远程更改",
                source_language="en_us",
                target_language="zh_cn",
                version=1,
                last_modified=1600,
                checksum=""
            ),
            # 与本地冲突的条目
            TranslationEntry(
                id="change_1",
                key="item.test.local_change",
                source_text="Local Change",
                target_text="本地更改（远程版本）",
                source_language="en_us",
                target_language="zh_cn",
                version=2,
                last_modified=1700,
                checksum=""
            )
        ]
        
        for entry in local_changes + remote_changes:
            entry.update_checksum()
        
        # 检测冲突
        conflicts = resolver.detect_conflicts(local_changes, remote_changes)
        
        # 双向同步结果
        sync_result = {
            "local_to_remote": [],  # 发送到远程的更改
            "remote_to_local": [],  # 从远程接收的更改
            "conflicts": conflicts,
            "resolved_conflicts": []
        }
        
        # 处理冲突
        for conflict in conflicts:
            if conflict["type"] == "remote_only":
                # 新的远程条目添加到本地
                sync_result["remote_to_local"].append(conflict["remote"])
            elif conflict["type"] == "local_only":
                # 新的本地条目发送到远程
                sync_result["local_to_remote"].append(conflict["local"])
            elif conflict["type"] == "version_conflict":
                # 解决版本冲突
                resolved = resolver.resolve_conflict(conflict, "accept_remote")
                sync_result["resolved_conflicts"].append(resolved.to_dict())
        
        # 验证双向同步结果
        assert len(sync_result["remote_to_local"]) == 1  # 一个远程新条目
        assert len(sync_result["resolved_conflicts"]) == 1  # 一个解决的冲突
        
        # 验证冲突解决
        resolved_conflict = sync_result["resolved_conflicts"][0]
        assert resolved_conflict["target_text"] == "本地更改（远程版本）"
        assert resolved_conflict["version"] == 2


class TestVersionControl:
    """版本控制测试"""
    
    def test_version_tracking(self):
        """测试版本跟踪"""
        entry = TranslationEntry(
            id="version_test",
            key="item.test.version",
            source_text="Version Test",
            target_text="版本测试",
            source_language="en_us",
            target_language="zh_cn",
            version=1,
            last_modified=time.time(),
            checksum=""
        )
        entry.update_checksum()
        
        # 版本历史
        version_history = [entry.to_dict()]
        
        # 模拟多次更新
        for i in range(2, 6):
            entry.target_text = f"版本测试 {i}"
            entry.version = i
            entry.last_modified = time.time()
            entry.update_checksum()
            
            version_history.append(entry.to_dict())
            
            # 模拟延迟
            time.sleep(0.001)
        
        # 验证版本历史
        assert len(version_history) == 5
        
        # 验证版本递增
        for i, version_data in enumerate(version_history):
            assert version_data["version"] == i + 1
        
        # 验证时间戳递增
        timestamps = [v["last_modified"] for v in version_history]
        assert timestamps == sorted(timestamps)
        
        # 验证内容变化
        texts = [v["target_text"] for v in version_history]
        assert texts[0] == "版本测试"
        assert texts[-1] == "版本测试 5"
    
    def test_rollback_functionality(self):
        """测试回滚功能"""
        # 创建版本历史
        versions = []
        for i in range(1, 4):
            entry = TranslationEntry(
                id="rollback_test",
                key="item.test.rollback",
                source_text="Rollback Test",
                target_text=f"回滚测试 {i}",
                source_language="en_us",
                target_language="zh_cn",
                version=i,
                last_modified=1000 + i * 100,
                checksum=""
            )
            entry.update_checksum()
            versions.append(entry)
        
        # 当前版本（最新）
        current_version = versions[-1]
        assert current_version.version == 3
        assert current_version.target_text == "回滚测试 3"
        
        # 回滚到版本2
        target_version = 2
        rollback_entry = None
        
        for version in versions:
            if version.version == target_version:
                rollback_entry = TranslationEntry(
                    id=version.id,
                    key=version.key,
                    source_text=version.source_text,
                    target_text=version.target_text,
                    source_language=version.source_language,
                    target_language=version.target_language,
                    version=current_version.version + 1,  # 新版本号
                    last_modified=time.time(),  # 新时间戳
                    checksum=""
                )
                rollback_entry.update_checksum()
                break
        
        # 验证回滚结果
        assert rollback_entry is not None
        assert rollback_entry.target_text == "回滚测试 2"  # 回滚到版本2的内容
        assert rollback_entry.version == 4  # 但版本号是新的
        assert rollback_entry.last_modified > current_version.last_modified


if __name__ == "__main__":
    # 运行数据一致性测试
    pytest.main([__file__, "-v"])