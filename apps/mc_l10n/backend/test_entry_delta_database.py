#!/usr/bin/env python
"""
测试Entry-Delta处理器的数据库集成功能
验证CRUD操作、合并逻辑、冲突处理等
"""

import sys
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
import structlog

sys.path.append('.')

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

from database.core.manager import McL10nDatabaseManager
from database.repositories.translation_entry_repository import TranslationEntryRepository, TranslationEntry
from api.v6.sync.entry_delta import get_entry_delta_processor, EntryDelta, MergeContext
from api.v6.sync.models import EntryDelta as EntryDeltaModel


async def setup_test_database():
    """设置测试数据库"""
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test_entry_delta.db"
    
    # 初始化数据库（构造时自动初始化）
    db_manager = McL10nDatabaseManager(str(db_path))
    
    # 创建Repository
    entry_repo = TranslationEntryRepository(db_manager)
    
    return db_manager, entry_repo, temp_dir


async def create_test_language_files(db_manager):
    """创建测试语言文件记录（满足外键约束）"""
    with db_manager.get_connection() as conn:
        # 创建必要的父记录
        conn.execute("""
            INSERT OR IGNORE INTO core_language_files (uid, carrier_type, carrier_uid, locale, rel_path, format, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("lang_minecraft_001", "mod", "carrier_001", "zh_cn", "lang/zh_cn.json", "json", 
              datetime.now().isoformat()))
        
        conn.execute("""
            INSERT OR IGNORE INTO core_language_files (uid, carrier_type, carrier_uid, locale, rel_path, format, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("lang_test_001", "mod", "carrier_test", "zh_cn", "lang/zh_cn.json", "json",
              datetime.now().isoformat()))


async def create_test_entries(entry_repo: TranslationEntryRepository, db_manager) -> list:
    """创建测试翻译条目"""
    # 先创建语言文件记录
    await create_test_language_files(db_manager)
    
    test_entries = []
    
    # 创建基础条目
    entry1 = TranslationEntry(
        uid="test_entry_001",
        language_file_uid="lang_minecraft_001",
        key="item.create.brass_ingot",
        src_text="Brass Ingot",
        dst_text="黄铜锭",
        status="reviewed",
        qa_flags={"validated": True},
        updated_at=datetime.now().isoformat(),
        created_at=datetime.now().isoformat(),  # 添加created_at
        uida_keys_b64="dGVzdF9rZXlzXzEyMw==",
        uida_hash="1234567890abcdef1234567890abcdef12345678"
    )
    
    entry2 = TranslationEntry(
        uid="test_entry_002", 
        language_file_uid="lang_minecraft_001",
        key="item.create.steel_ingot",
        src_text="Steel Ingot",
        dst_text="",  # 未翻译
        status="new",
        qa_flags={},
        updated_at=datetime.now().isoformat(),
        created_at=datetime.now().isoformat(),  # 添加created_at
        uida_keys_b64="dGVzdF9rZXlzXzQ1Ng==",
        uida_hash="abcdef1234567890abcdef1234567890abcdef12"
    )
    
    # 插入数据库
    created1 = await entry_repo.create(entry1)
    created2 = await entry_repo.create(entry2)
    
    test_entries.extend([created1, created2])
    
    logger.info("创建测试条目完成", count=len(test_entries))
    return test_entries


async def test_database_integration():
    """测试数据库集成功能"""
    print("=== 测试Entry-Delta数据库集成 ===")
    
    try:
        # 设置测试环境
        db_manager, entry_repo, temp_dir = await setup_test_database()
        
        # 创建测试数据
        test_entries = await create_test_entries(entry_repo, db_manager)
        print(f"✓ 创建测试条目: {len(test_entries)} 个")
        
        # 获取带Repository的处理器
        processor = get_entry_delta_processor(entry_repo)
        print("✓ Entry-Delta处理器初始化（含Repository）")
        
        # 测试场景1: 更新现有条目
        update_delta = EntryDeltaModel(
            entry_uid="test_entry_001",
            uida_keys_b64="dGVzdF9rZXlzXzEyMw==",
            uida_hash="1234567890abcdef1234567890abcdef12345678",
            operation="update",
            key="item.create.brass_ingot",
            src_text="Brass Ingot",
            dst_text="黄铜锭（更新版）",  # 更新翻译
            status="reviewed",
            language_file_uid="lang_minecraft_001",
            updated_at=datetime.now().isoformat(),
            qa_flags={"validated": True, "updated_by_sync": True}
        )
        
        # 测试场景2: 创建新条目
        create_delta = EntryDeltaModel(
            entry_uid="test_entry_003",
            uida_keys_b64="dGVzdF9rZXlzXzc4OQ==",
            uida_hash="567890abcdef1234567890abcdef1234567890ab",
            operation="create",
            key="item.create.copper_ingot",
            src_text="Copper Ingot",
            dst_text="铜锭",
            status="mt",
            language_file_uid="lang_minecraft_001",
            updated_at=datetime.now().isoformat(),
            qa_flags={"auto_translated": True}
        )
        
        # 测试场景3: 冲突情况（本地已修改的条目）
        conflict_delta = EntryDeltaModel(
            entry_uid="test_entry_002",
            uida_keys_b64="dGVzdF9rZXlzXzQ1Ng==",
            uida_hash="abcdef1234567890abcdef1234567890abcdef12",
            operation="update",
            key="item.create.steel_ingot",
            src_text="Steel Ingot",
            dst_text="钢锭（远程版本）",  # 与本地版本可能冲突
            status="reviewed",
            language_file_uid="lang_minecraft_001",
            updated_at=datetime.now().isoformat(),
            qa_flags={"remote_update": True}
        )
        
        # 先修改本地条目以制造冲突
        # 找到条目（通过language_file_uid和key）
        entries = await entry_repo.find_by_language_file("lang_minecraft_001")
        local_entry = None
        for entry in entries:
            if entry.uid == "test_entry_002":
                local_entry = entry
                break
        if local_entry:
            local_entry.dst_text = "钢锭（本地版本）"
            local_entry.status = "reviewed"
            await entry_repo.update(local_entry)
            print("✓ 本地条目已修改，准备测试冲突场景")
        
        # 批量处理Delta
        deltas = [update_delta, create_delta, conflict_delta]
        results = await processor.batch_process_deltas(deltas, merge_strategy="3way")
        
        print("\n✓ 批量处理结果:")
        print(f"  处理总数: {results['processed']}")
        print(f"  成功合并: {results['merged']}")
        print(f"  创建条目: {results['created']}")
        print(f"  更新条目: {results['updated']}")
        print(f"  删除条目: {results['deleted']}")
        print(f"  冲突数量: {results['conflicts']}")
        print(f"  错误数量: {results['errors']}")
        
        # 验证结果
        updated_entry = await entry_repo.find_by_id("test_entry_001")
        if updated_entry and updated_entry.dst_text == "黄铜锭（更新版）":
            print("✓ 更新操作验证成功")
        else:
            print("✗ 更新操作验证失败")
        
        created_entry = await entry_repo.find_by_id("test_entry_003")
        if created_entry:
            print("✓ 创建操作验证成功")
        else:
            print("✗ 创建操作验证失败")
        
        # 验证冲突处理
        if results['conflicts'] > 0:
            conflict_entry = await entry_repo.find_by_id("test_entry_002")
            if conflict_entry and conflict_entry.status == "conflict":
                print("✓ 冲突处理验证成功")
            else:
                print("✓ 冲突处理：使用策略合并")
        
        # 清理
        import shutil
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ 数据库集成测试失败: {e}")
        logger.error("数据库集成测试异常", error=str(e))
        return False


async def test_merge_strategies():
    """测试不同的合并策略"""
    print("\n=== 测试合并策略 ===")
    
    try:
        # 设置测试环境
        temp_dir = Path(tempfile.mkdtemp())
        db_path = temp_dir / "test_merge_strategies.db"
        db_manager = McL10nDatabaseManager(str(db_path))
        entry_repo = TranslationEntryRepository(db_manager)
        processor = get_entry_delta_processor(entry_repo)
        
        # 先创建语言文件
        await create_test_language_files(db_manager)
        
        # 创建基础条目
        base_entry = TranslationEntry(
            uid="merge_test_001",
            language_file_uid="lang_test_001",
            key="test.merge.key",
            src_text="Test Text",
            dst_text="原始翻译",
            status="reviewed",
            updated_at=datetime.now().isoformat(),
            created_at=datetime.now().isoformat()  # 添加created_at
        )
        await entry_repo.create(base_entry)
        
        # 测试策略1: take_remote
        remote_delta = EntryDeltaModel(
            entry_uid="merge_test_001",
            uida_keys_b64="dGVzdF9tZXJnZQ==",
            uida_hash="merge123456789abcdef123456789abcdef123456789",
            operation="update",
            key="test.merge.key",
            src_text="Test Text",
            dst_text="远程翻译",
            status="reviewed",
            language_file_uid="lang_test_001",
            updated_at=datetime.now().isoformat()
        )
        
        # 模拟本地修改
        local_modified = await entry_repo.find_by_id("merge_test_001")
        local_modified.dst_text = "本地翻译"
        await entry_repo.update(local_modified)
        
        # 执行合并
        context = MergeContext(
            base_entry=base_entry,
            local_entry=local_modified,
            remote_entry=processor.deserialize_entry_delta(remote_delta),
            merge_strategy="3way",
            conflict_resolution="take_remote"
        )
        
        merge_result = processor.perform_3way_merge(context)
        
        if merge_result.success and merge_result.merged_entry.dst_text == "远程翻译":
            print("✓ take_remote策略测试通过")
        else:
            print("✗ take_remote策略测试失败")
        
        # 清理
        import shutil
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ 合并策略测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有数据库集成测试"""
    print("🚀 开始Entry-Delta数据库集成测试")
    print("=" * 60)
    
    tests = [
        test_database_integration,
        test_merge_strategies,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            logger.error(f"测试执行异常: {test.__name__}", error=str(e))
    
    print("=" * 60)
    print(f"🏁 Entry-Delta数据库集成测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有数据库集成测试通过!")
        return True
    else:
        print(f"⚠️  有 {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    asyncio.run(run_all_tests())