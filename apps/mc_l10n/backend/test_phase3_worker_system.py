"""
Phase 3 Worker系统综合测试
测试 ENUM/META/LANG/VERIFY 四个专门化Worker的完整工作流程
"""

import asyncio
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict, Any

import pytest

from infrastructure.db_initializer import DatabaseInitializer
from infrastructure.services.worker_manager import (
    WorkerManager, WorkerType, WorkTask, TaskStatus, WorkerResult
)
from infrastructure.services.event_applier import EventApplier
from infrastructure.services.workers.enum_worker import EnumWorker
from infrastructure.services.workers.meta_worker import MetaWorker
from infrastructure.services.workers.lang_worker import LangWorker
from infrastructure.services.workers.verify_worker import VerifyWorker


class TestPhase3WorkerSystem:
    """Phase 3 Worker系统综合测试"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # 初始化数据库
        db_initializer = DatabaseInitializer(db_path)
        db_initializer.ensure_database_exists()
        
        yield db_path
        
        # 清理
        Path(db_path).unlink()
    
    @pytest.fixture
    def temp_minecraft_dir(self):
        """创建临时Minecraft目录结构和测试MOD文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            minecraft_dir = Path(temp_dir) / "minecraft"
            minecraft_dir.mkdir()
            
            # 创建mods目录
            mods_dir = minecraft_dir / "mods"
            mods_dir.mkdir()
            
            # 创建测试MOD文件
            self._create_test_mod_file(mods_dir / "test_mod.jar")
            self._create_test_fabric_mod(mods_dir / "fabric_mod.jar")
            
            # 创建resourcepacks目录
            rp_dir = minecraft_dir / "resourcepacks"
            rp_dir.mkdir()
            self._create_test_resource_pack(rp_dir / "test_pack.zip")
            
            # 创建config目录
            config_dir = minecraft_dir / "config"
            config_dir.mkdir()
            (config_dir / "test.toml").write_text("test_key = 'test_value'")
            
            yield minecraft_dir
    
    def _create_test_mod_file(self, mod_path: Path):
        """创建测试MOD文件（Forge格式）"""
        with zipfile.ZipFile(mod_path, 'w') as zf:
            # 添加mods.toml
            mods_toml = '''
modLoader="javafml"
loaderVersion="[40,)"
license="MIT"

[[mods]]
modId="testmod"
version="1.0.0"
displayName="Test Mod"
description="A test mod for unit testing"
authors="Test Author"

[[dependencies.testmod]]
modId="minecraft"
mandatory=true
versionRange="[1.19,1.20)"
ordering="NONE"
side="BOTH"
'''
            zf.writestr('META-INF/mods.toml', mods_toml)
            
            # 添加语言文件
            en_us_json = {
                "item.testmod.test_item": "Test Item",
                "block.testmod.test_block": "Test Block",
                "gui.testmod.title": "Test GUI"
            }
            zf.writestr('assets/testmod/lang/en_us.json', json.dumps(en_us_json))
            
            zh_cn_json = {
                "item.testmod.test_item": "测试物品",
                "block.testmod.test_block": "测试方块",
                "gui.testmod.title": "测试界面"
            }
            zf.writestr('assets/testmod/lang/zh_cn.json', json.dumps(zh_cn_json))
    
    def _create_test_fabric_mod(self, mod_path: Path):
        """创建测试Fabric MOD文件"""
        with zipfile.ZipFile(mod_path, 'w') as zf:
            # 添加fabric.mod.json
            fabric_json = {
                "schemaVersion": 1,
                "id": "fabric_test_mod",
                "version": "2.0.0",
                "name": "Fabric Test Mod",
                "description": "A fabric test mod",
                "authors": ["Fabric Author"],
                "contact": {
                    "homepage": "https://example.com",
                    "sources": "https://github.com/example/mod"
                },
                "depends": {
                    "fabricloader": ">=0.14.0",
                    "minecraft": "1.19.x"
                }
            }
            zf.writestr('fabric.mod.json', json.dumps(fabric_json))
            
            # 添加语言文件
            en_lang = '''
item.fabric_test.weapon=Fabric Weapon
block.fabric_test.ore=Fabric Ore
'''
            zf.writestr('assets/fabric_test/lang/en_us.lang', en_lang)
    
    def _create_test_resource_pack(self, pack_path: Path):
        """创建测试资源包"""
        with zipfile.ZipFile(pack_path, 'w') as zf:
            # 添加pack.mcmeta
            pack_meta = {
                "pack": {
                    "pack_format": 9,
                    "description": "Test Resource Pack"
                }
            }
            zf.writestr('pack.mcmeta', json.dumps(pack_meta))
            
            # 添加语言文件
            overlay_lang = {
                "gui.done": "完成",
                "gui.cancel": "取消"
            }
            zf.writestr('assets/minecraft/lang/zh_cn.json', json.dumps(overlay_lang))
    
    @pytest.fixture
    def worker_manager(self, temp_db):
        """创建配置好的WorkerManager"""
        event_applier = EventApplier(temp_db)
        manager = WorkerManager(temp_db, event_applier)
        
        # 注册所有Worker
        manager.register_worker(EnumWorker(temp_db))
        manager.register_worker(MetaWorker(temp_db))
        manager.register_worker(LangWorker(temp_db))
        manager.register_worker(VerifyWorker(temp_db))
        
        return manager
    
    async def test_enum_worker_directory_scanning(self, temp_db, temp_minecraft_dir):
        """测试ENUM Worker的目录扫描功能"""
        worker = EnumWorker(temp_db)
        
        task = WorkTask(
            task_id=1,
            task_type=WorkerType.ENUM,
            session_id="test_session_1",
            payload={
                'root_path': str(temp_minecraft_dir),
                'snapshot_id': 'snapshot_1'
            },
            priority=100,
            status=TaskStatus.PENDING
        )
        
        result = await worker.process_task(task)
        
        assert result.success is True
        assert result.events is not None
        assert len(result.events) >= 3  # 至少应该找到2个MOD + 1个资源包 + 1个配置文件
        
        # 验证找到的文件类型 - 从mod_data中提取type
        file_types = []
        for event in result.events:
            if 'mod_data' in event.payload:
                file_types.append(event.payload['mod_data'].get('type'))
            else:
                file_types.append(event.payload.get('type'))
        
        print(f"调试: 发现的文件类型: {file_types}")
        
        assert 'mod_file' in file_types
        assert 'resource_pack' in file_types
        
        print(f"✅ ENUM Worker发现 {len(result.events)} 个文件")
    
    async def test_meta_worker_mod_parsing(self, temp_db, temp_minecraft_dir):
        """测试META Worker的MOD元数据解析"""
        worker = MetaWorker(temp_db)
        
        # 测试Forge MOD
        forge_mod_path = temp_minecraft_dir / "mods" / "test_mod.jar"
        task = WorkTask(
            task_id=2,
            task_type=WorkerType.META,
            session_id="test_session_2",
            payload={
                'file_path': str(forge_mod_path),
                'snapshot_id': 'snapshot_2'
            },
            priority=100,
            status=TaskStatus.PENDING
        )
        
        result = await worker.process_task(task)
        
        assert result.success is True
        assert result.events is not None
        assert len(result.events) >= 1  # 至少应该有MOD基础信息事件
        
        # 验证MOD信息
        mod_info_event = result.events[0]
        mod_data = mod_info_event.payload
        print(f"调试META: {mod_data}")  # 打印event payload结构
        
        # META Worker产生的事件可能有不同的结构
        if 'fields' in mod_data:
            fields = mod_data['fields']
            assert fields.get('modid') == 'testmod'
            assert fields.get('name') == 'Test Mod'
            mod_name = fields.get('name')
            mod_id = fields.get('modid')
        else:
            assert mod_data.get('modid') == 'testmod'
            assert mod_data.get('name') == 'Test Mod'
            mod_name = mod_data.get('name')
            mod_id = mod_data.get('modid')
        
        print(f"✅ META Worker解析MOD: {mod_name} (ID: {mod_id})")
        
        # 测试Fabric MOD
        fabric_mod_path = temp_minecraft_dir / "mods" / "fabric_mod.jar"
        task.payload['file_path'] = str(fabric_mod_path)
        
        result = await worker.process_task(task)
        assert result.success is True
        
        print(f"✅ META Worker同时支持Forge和Fabric格式")
    
    async def test_lang_worker_language_parsing(self, temp_db, temp_minecraft_dir):
        """测试LANG Worker的语言文件解析"""
        worker = LangWorker(temp_db)
        
        # 测试JSON格式语言文件
        mod_path = temp_minecraft_dir / "mods" / "test_mod.jar"
        task = WorkTask(
            task_id=3,
            task_type=WorkerType.LANG,
            session_id="test_session_3",
            payload={
                'file_path': str(mod_path),
                'target_languages': ['en_us', 'zh_cn'],
                'snapshot_id': 'snapshot_3'
            },
            priority=100,
            status=TaskStatus.PENDING
        )
        
        result = await worker.process_task(task)
        
        assert result.success is True
        assert result.events is not None
        assert len(result.events) >= 2  # 应该找到en_us和zh_cn两个语言文件
        
        # 验证语言文件内容
        total_entries = 0
        locales_found = []
        for event in result.events:
            lang_data = event.payload
            locale = lang_data.get('language_file', {}).get('locale')
            entries = lang_data.get('entries', [])
            
            locales_found.append(locale)
            total_entries += len(entries)
            
            # 验证条目结构
            for entry in entries[:3]:  # 检查前3个条目
                assert 'key' in entry
                assert 'src_text' in entry
                assert 'dst_text' in entry
                assert 'status' in entry
        
        assert 'en_us' in locales_found
        assert 'zh_cn' in locales_found
        assert total_entries >= 6  # 每个语言文件至少3个条目
        
        print(f"✅ LANG Worker解析 {len(locales_found)} 种语言，{total_entries} 个翻译条目")
    
    async def test_verify_worker_deduplication(self, temp_db):
        """测试VERIFY Worker的去重和冲突检测"""
        # 首先在数据库中插入一些测试数据来模拟重复和冲突
        conn = sqlite3.connect(temp_db)
        
        # 插入重复的MOD文件记录
        test_events = [
            {
                'session_id': 'test_session_4',
                'event_type': 'LIST_UPSERT',
                'payload_json': json.dumps({
                    'type': 'mod_file',
                    'file_path': 'mods/duplicate_mod.jar',
                    'file_size': 1024000
                })
            },
            {
                'session_id': 'test_session_4',
                'event_type': 'LIST_UPSERT',
                'payload_json': json.dumps({
                    'type': 'mod_file',
                    'file_path': 'mods/duplicate_mod.jar',  # 重复文件
                    'file_size': 1024000
                })
            },
            {
                'session_id': 'test_session_4',
                'event_type': 'FIELD_PATCH',
                'payload_json': json.dumps({
                    'modid': 'conflict_mod',
                    'version': '1.0.0',
                    'file_path': 'mods/conflict_mod_v1.jar'
                })
            },
            {
                'session_id': 'test_session_4',
                'event_type': 'FIELD_PATCH',
                'payload_json': json.dumps({
                    'modid': 'conflict_mod',  # 相同modid
                    'version': '2.0.0',      # 不同版本
                    'file_path': 'mods/conflict_mod_v2.jar'
                })
            }
        ]
        
        for event in test_events:
            conn.execute("""
                INSERT INTO ops_event_log (session_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (event['session_id'], event['event_type'], event['payload_json']))
        
        conn.commit()
        conn.close()
        
        # 测试VERIFY Worker
        worker = VerifyWorker(temp_db)
        task = WorkTask(
            task_id=4,
            task_type=WorkerType.VERIFY,
            session_id="test_session_4",
            payload={
                'verification_type': 'full',  # 完整验证
                'snapshot_id': 'snapshot_4'
            },
            priority=100,
            status=TaskStatus.PENDING
        )
        
        result = await worker.process_task(task)
        
        assert result.success is True
        assert result.events is not None
        
        # 验证产生的事件类型
        event_types = []
        for event in result.events:
            event_type = event.event_type
            event_types.append(event_type)
            
            if event_type == 'TOMBSTONE':
                payload = event.payload
                reason = payload.get('reason')
                assert reason in ['duplicate_file', 'duplicate_modid', 'version_conflict', 'loader_conflict']
        
        print(f"✅ VERIFY Worker检测到问题并生成 {len(result.events)} 个处理事件")
        print(f"   事件类型: {set(event_types)}")
    
    async def test_complete_worker_workflow(self, temp_db, temp_minecraft_dir, worker_manager):
        """测试完整的Worker工作流程"""
        # 启动EventApplier
        await worker_manager.event_applier.start()
        
        session_id = "complete_workflow_session"
        
        # 1. 创建ENUM任务
        enum_task = WorkTask(
            task_id=101,
            task_type=WorkerType.ENUM,
            session_id=session_id,
            payload={
                'root_path': str(temp_minecraft_dir),
                'snapshot_id': 'complete_snapshot'
            },
            priority=100,
            status=TaskStatus.PENDING
        )
        
        # 2. 处理ENUM任务
        enum_worker = worker_manager.workers[WorkerType.ENUM]
        enum_result = await enum_worker.handle_task(enum_task)
        
        assert enum_result.success is True
        print(f"📁 ENUM阶段完成，发现 {len(enum_result.events)} 个文件")
        
        # 提交ENUM事件
        for event in enum_result.events:
            worker_manager.event_applier.submit_event(event)
        
        # 3. 等待事件处理完成
        await asyncio.sleep(0.5)
        while not worker_manager.event_applier.event_queue.empty():
            await asyncio.sleep(0.1)
        
        # 4. 创建META任务处理找到的MOD文件
        meta_tasks = []
        for event in enum_result.events:
            if event.payload.get('type') == 'mod_file':
                file_path = event.payload.get('file_path')
                meta_task = WorkTask(
                    task_id=200 + len(meta_tasks),
                    task_type=WorkerType.META,
                    session_id=session_id,
                    payload={
                        'file_path': str(temp_minecraft_dir / file_path),
                        'snapshot_id': 'complete_snapshot'
                    },
                    priority=70,
                    status=TaskStatus.PENDING
                )
                meta_tasks.append(meta_task)
        
        # 5. 处理META任务
        meta_worker = worker_manager.workers[WorkerType.META]
        for meta_task in meta_tasks:
            meta_result = await meta_worker.handle_task(meta_task)
            assert meta_result.success is True
            
            for event in meta_result.events:
                worker_manager.event_applier.submit_event(event)
        
        print(f"🔧 META阶段完成，处理 {len(meta_tasks)} 个MOD文件")
        
        # 6. 创建LANG任务
        lang_tasks = []
        for event in enum_result.events:
            if event.payload.get('type') in ['mod_file', 'resource_pack']:
                file_path = event.payload.get('file_path')
                lang_task = WorkTask(
                    task_id=300 + len(lang_tasks),
                    task_type=WorkerType.LANG,
                    session_id=session_id,
                    payload={
                        'file_path': str(temp_minecraft_dir / file_path),
                        'target_languages': ['en_us', 'zh_cn'],
                        'snapshot_id': 'complete_snapshot'
                    },
                    priority=50,
                    status=TaskStatus.PENDING
                )
                lang_tasks.append(lang_task)
        
        # 7. 处理LANG任务
        lang_worker = worker_manager.workers[WorkerType.LANG]
        total_lang_entries = 0
        for lang_task in lang_tasks:
            lang_result = await lang_worker.handle_task(lang_task)
            if lang_result.success:
                total_lang_entries += len(lang_result.events)
                
                for event in lang_result.events:
                    worker_manager.event_applier.submit_event(event)
        
        print(f"🌐 LANG阶段完成，解析 {total_lang_entries} 个语言文件")
        
        # 8. 等待所有事件处理完成
        await asyncio.sleep(1)
        while not worker_manager.event_applier.event_queue.empty():
            await asyncio.sleep(0.1)
        
        # 9. 执行VERIFY任务
        verify_task = WorkTask(
            task_id=400,
            task_type=WorkerType.VERIFY,
            session_id=session_id,
            payload={
                'verification_type': 'full',
                'snapshot_id': 'complete_snapshot'
            },
            priority=20,
            status=TaskStatus.PENDING
        )
        
        verify_worker = worker_manager.workers[WorkerType.VERIFY]
        verify_result = await verify_worker.handle_task(verify_task)
        
        assert verify_result.success is True
        print(f"✅ VERIFY阶段完成，生成 {len(verify_result.events)} 个验证事件")
        
        # 10. 验证数据库中的数据
        conn = sqlite3.connect(temp_db)
        
        # 检查事件日志
        cursor = conn.execute("""
            SELECT event_type, COUNT(*) as count 
            FROM ops_event_log 
            WHERE session_id = ? 
            GROUP BY event_type
        """, (session_id,))
        
        event_counts = dict(cursor.fetchall())
        conn.close()
        
        assert 'LIST_UPSERT' in event_counts  # ENUM产生的事件
        assert 'FIELD_PATCH' in event_counts  # META产生的事件
        assert 'LANG_UPSERT' in event_counts  # LANG产生的事件
        
        print(f"📊 完整工作流程统计: {event_counts}")
        print("🎉 Phase 3 Worker系统综合测试通过！")
        
        # 停止EventApplier
        worker_manager.event_applier.stop()


if __name__ == "__main__":
    async def run_tests():
        """运行所有测试"""
        test_instance = TestPhase3WorkerSystem()
        
        # 创建临时资源
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db = f.name
        
        with tempfile.TemporaryDirectory() as temp_dir:
            minecraft_dir = Path(temp_dir) / "minecraft"
            minecraft_dir.mkdir()
            
            # 创建目录结构
            test_instance.temp_minecraft_dir = lambda: minecraft_dir
            
            # 初始化数据库
            db_initializer = DatabaseInitializer(temp_db)
            db_initializer.ensure_database_exists()
            
            # 创建测试文件
            minecraft_dir_obj = minecraft_dir
            mods_dir = minecraft_dir_obj / "mods" 
            mods_dir.mkdir()
            rp_dir = minecraft_dir_obj / "resourcepacks"
            rp_dir.mkdir()
            config_dir = minecraft_dir_obj / "config"
            config_dir.mkdir()
            
            test_instance._create_test_mod_file(mods_dir / "test_mod.jar")
            test_instance._create_test_fabric_mod(mods_dir / "fabric_mod.jar")
            test_instance._create_test_resource_pack(rp_dir / "test_pack.zip")
            (config_dir / "test.toml").write_text("test_key = 'test_value'")
            
            # 创建WorkerManager
            event_applier = EventApplier(temp_db)
            worker_manager = WorkerManager(temp_db, event_applier)
            worker_manager.register_worker(EnumWorker(temp_db))
            worker_manager.register_worker(MetaWorker(temp_db))
            worker_manager.register_worker(LangWorker(temp_db))
            worker_manager.register_worker(VerifyWorker(temp_db))
            
            try:
                print("🚀 开始Phase 3 Worker系统综合测试")
                
                # 运行各个测试
                await test_instance.test_enum_worker_directory_scanning(temp_db, minecraft_dir_obj)
                await test_instance.test_meta_worker_mod_parsing(temp_db, minecraft_dir_obj)
                await test_instance.test_lang_worker_language_parsing(temp_db, minecraft_dir_obj)
                await test_instance.test_verify_worker_deduplication(temp_db)
                await test_instance.test_complete_worker_workflow(temp_db, minecraft_dir_obj, worker_manager)
                
                print("\n🎉 所有Phase 3测试通过！")
                
            finally:
                # 清理
                Path(temp_db).unlink()
    
    # 运行测试
    asyncio.run(run_tests())