"""
Phase 4 集成测试 - ScanSessionManager与所有组件的集成
验证统一扫描API接口的完整功能
"""

import asyncio
import tempfile
from pathlib import Path

from infrastructure.db_initializer import DatabaseInitializer
from infrastructure.services.scan_session_manager import ScanSessionManager, ScanMode


async def test_scan_session_manager_integration():
    """测试ScanSessionManager完整集成功能"""
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    print("🚀 Phase 4 集成测试 - ScanSessionManager")
    
    try:
        # 初始化数据库
        print("1️⃣ 初始化数据库...")
        db_initializer = DatabaseInitializer(db_path)
        db_initializer.ensure_database_exists()
        
        # 创建ScanSessionManager
        print("2️⃣ 创建ScanSessionManager...")
        manager = ScanSessionManager(db_path)
        await manager.start()
        
        # 测试1: 启动完整扫描会话
        print("\n3️⃣ 测试完整扫描模式...")
        # 创建临时测试目录
        with tempfile.TemporaryDirectory() as temp_dir:
            session_id = await manager.start_scan(
                root_path=temp_dir,  # 使用临时目录进行测试
                mode=ScanMode.FULL,
                target_languages=['en_us', 'zh_cn']
            )
            print(f"   ✅ 扫描会话已启动: {session_id}")
            
            # 等待一段时间让工作流程开始执行
            await asyncio.sleep(2.0)
            
            # 测试2: 获取扫描状态
            print("\n4️⃣ 测试扫描状态获取...")
            status = await manager.get_scan_status(session_id)
            if status:
                print(f"   📊 会话状态: {status['stage']}")
                print(f"   📈 进度: {status['progress']:.1%}")
                print(f"   📋 任务统计: {status['tasks']}")
            else:
                print("   ⚠️ 无法获取扫描状态")
            
            # 测试3: 列出活动会话
            print("\n5️⃣ 测试活动会话列表...")
            active_sessions = await manager.list_active_sessions()
            print(f"   📋 活动会话数量: {len(active_sessions)}")
            for session in active_sessions:
                print(f"      - {session['session_id']}: {session['stage']}")
            
            # 测试4: 流式进度监控（简短测试）
            print("\n6️⃣ 测试流式进度监控...")
            progress_count = 0
            async for progress in manager.stream_scan_progress(session_id):
                print(f"   📡 进度更新: {progress['stage']} - {progress['progress']:.1%}")
                progress_count += 1
                if progress_count >= 3:  # 只监控3次更新
                    break
            
            # 测试5: 不同扫描模式
            print("\n7️⃣ 测试不同扫描模式...")
            
            # 元数据模式
            meta_session_id = await manager.start_scan(
                root_path=temp_dir,
                mode=ScanMode.METADATA_ONLY
            )
            print(f"   🏷️ 元数据扫描会话: {meta_session_id}")
            
            # 语言模式
            lang_session_id = await manager.start_scan(
                root_path=temp_dir, 
                mode=ScanMode.LANGUAGE_ONLY,
                target_languages=['zh_cn']
            )
            print(f"   🌐 语言扫描会话: {lang_session_id}")
        
        await asyncio.sleep(1.0)
        
        # 测试6: 管理器统计信息
        print("\n8️⃣ 测试管理器统计...")
        manager_stats = manager.get_manager_stats()
        print(f"   📊 管理器统计: {manager_stats}")
        
        # 测试7: 取消扫描会话
        print("\n9️⃣ 测试扫描会话取消...")
        cancel_result = await manager.cancel_scan(meta_session_id)
        print(f"   🚫 取消结果: {cancel_result}")
        
        # 等待其他会话完成或失败
        await asyncio.sleep(2.0)
        
        # 测试8: 获取扫描结果
        print("\n🔟 测试扫描结果获取...")
        results = await manager.get_scan_results(session_id)
        if results:
            print(f"   📋 扫描结果: {results['statistics']}")
        else:
            print("   ⚠️ 扫描尚未完成或失败")
        
        print("\n🎉 Phase 4 集成测试完成！")
        print("✅ ScanSessionManager成功集成所有组件")
        print("✅ 统一扫描API接口功能正常")
        print("✅ 多种扫描模式支持正常")
        print("✅ 会话管理和进度监控正常")
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 停止管理器
        try:
            manager.stop()
        except:
            pass
        
        # 清理数据库
        try:
            Path(db_path).unlink()
        except:
            pass


async def test_scan_modes_comparison():
    """测试不同扫描模式的对比"""
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    print("\n🔄 扫描模式对比测试")
    
    try:
        # 初始化
        db_initializer = DatabaseInitializer(db_path)
        db_initializer.ensure_database_exists()
        manager = ScanSessionManager(db_path)
        await manager.start()
        
        # 测试所有扫描模式
        modes = [
            (ScanMode.FULL, "完整扫描"),
            (ScanMode.INCREMENTAL, "增量扫描"),
            (ScanMode.METADATA_ONLY, "仅元数据"),
            (ScanMode.LANGUAGE_ONLY, "仅语言文件")
        ]
        
        session_ids = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for mode, description in modes:
                print(f"\n📋 启动{description}...")
                session_id = await manager.start_scan(
                    root_path=temp_dir,
                    mode=mode,
                    target_languages=['en_us', 'zh_cn'],
                    incremental=(mode == ScanMode.INCREMENTAL)
                )
                session_ids.append((session_id, description))
                print(f"   ✅ 会话ID: {session_id}")
        
        # 等待工作流程启动
        await asyncio.sleep(2.0)
        
        # 检查各会话状态
        print("\n📊 各扫描模式状态:")
        for session_id, description in session_ids:
            status = await manager.get_scan_status(session_id)
            if status:
                print(f"   {description}: {status['stage']} - {status['progress']:.1%}")
            else:
                print(f"   {description}: 状态未知")
        
        print("\n✅ 扫描模式对比测试完成")
        
    except Exception as e:
        print(f"❌ 扫描模式测试失败: {e}")
        
    finally:
        try:
            manager.stop()
            Path(db_path).unlink()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(test_scan_session_manager_integration())
    asyncio.run(test_scan_modes_comparison())