#!/usr/bin/env python3
"""
测试分层异步增量扫描架构
验证快照构建、差异对比和工作队列功能
"""

import tempfile
import sqlite3
import json
import shutil
from pathlib import Path
from infrastructure.db_initializer import DatabaseInitializer
from infrastructure.services.snapshot_builder import SnapshotBuilder
from infrastructure.services.diff_engine import DiffEngine

def create_test_modpack(temp_dir: Path) -> Path:
    """创建测试用的模组包结构"""
    modpack_dir = temp_dir / "test_modpack"
    modpack_dir.mkdir()
    
    # 创建mods目录和一些测试文件
    mods_dir = modpack_dir / "mods"
    mods_dir.mkdir()
    
    # 模拟mod文件
    (mods_dir / "example-mod-1.0.jar").write_text("fake jar content 1")
    (mods_dir / "another-mod-2.1.jar").write_text("fake jar content 2")
    
    # 创建资源包目录
    resourcepacks_dir = modpack_dir / "resourcepacks"
    resourcepacks_dir.mkdir()
    
    (resourcepacks_dir / "test-resource-pack.zip").write_text("fake resource pack")
    
    # 创建配置文件
    config_dir = modpack_dir / "config"
    config_dir.mkdir()
    
    (config_dir / "example-mod.toml").write_text("""
[general]
enabled = true
""")
    
    # 创建语言文件
    lang_dir = modpack_dir / "assets" / "examplemod" / "lang"
    lang_dir.mkdir(parents=True)
    
    (lang_dir / "en_us.json").write_text(json.dumps({
        "item.examplemod.test_item": "Test Item",
        "block.examplemod.test_block": "Test Block"
    }))
    
    return modpack_dir

def test_snapshot_builder(db_path: str, modpack_dir: Path):
    """测试快照构建功能"""
    print("🔍 测试快照构建功能...")
    
    builder = SnapshotBuilder(db_path)
    
    # 构建第一个快照
    snapshot_id, file_count = builder.build_snapshot(
        root_path=str(modpack_dir),
        session_id="test_session_1",
        pack_uid="test_pack_uid"
    )
    
    print(f"✅ 快照构建成功: {snapshot_id}, 文件数量: {file_count}")
    
    # 验证快照数据
    snapshot_data = builder.get_snapshot(snapshot_id)
    assert snapshot_data is not None, "快照数据不能为空"
    assert len(snapshot_data['files']) == file_count, "文件数量不匹配"
    
    print(f"📋 快照包含文件: {list(snapshot_data['files'].keys())}")
    
    return snapshot_id

def test_diff_engine(db_path: str, modpack_dir: Path, base_snapshot_id: str):
    """测试差异对比功能"""
    print("🔍 测试差异对比功能...")
    
    # 修改一些文件以创建差异
    (modpack_dir / "mods" / "new-mod-1.0.jar").write_text("new mod content")
    (modpack_dir / "mods" / "example-mod-1.0.jar").write_text("modified jar content 1")
    (modpack_dir / "mods" / "another-mod-2.1.jar").unlink()  # 删除文件
    
    # 构建新快照
    builder = SnapshotBuilder(db_path)
    new_snapshot_id, file_count = builder.build_snapshot(
        root_path=str(modpack_dir),
        session_id="test_session_2",
        pack_uid="test_pack_uid"
    )
    
    print(f"✅ 新快照构建成功: {new_snapshot_id}, 文件数量: {file_count}")
    
    # 对比快照
    diff_engine = DiffEngine(db_path)
    delta_id, changes = diff_engine.compare_snapshots(
        current_snapshot_id=new_snapshot_id,
        base_snapshot_id=base_snapshot_id,
        session_id="test_diff_session"
    )
    
    print(f"✅ 差异对比完成: {delta_id}")
    
    # 验证变化
    print("📋 检测到的变化:")
    for change_type, change_list in changes.items():
        if change_list:
            print(f"  {change_type}: {len(change_list)} 个文件")
            for change in change_list[:3]:  # 只显示前3个
                print(f"    - {change.path}")
    
    # 验证预期的变化
    assert len(changes['added']) >= 1, "应该检测到新增文件"
    assert len(changes['modified']) >= 1, "应该检测到修改文件"
    assert len(changes['removed']) >= 1, "应该检测到删除文件"
    
    return delta_id

def test_work_queue_extensions(db_path: str):
    """测试工作队列扩展功能"""
    print("🔍 测试工作队列扩展功能...")
    
    conn = sqlite3.connect(db_path)
    
    # 测试新的扫描任务类型
    scan_tasks = [
        {
            "type": "scan_enum",
            "payload": {
                "session_id": "test_session",
                "root_path": "/test/path",
                "checkpoint": {"stage": "enum", "offset": 0}
            }
        },
        {
            "type": "scan_meta", 
            "payload": {
                "session_id": "test_session",
                "file_path": "mods/test.jar",
                "checkpoint": {"stage": "meta", "last_step": "manifest"}
            }
        },
        {
            "type": "scan_lang",
            "payload": {
                "session_id": "test_session",
                "lang_file_path": "assets/mod/lang/en_us.json",
                "checkpoint": {"stage": "lang", "last_key": "item.test"}
            }
        },
        {
            "type": "scan_verify",
            "payload": {
                "session_id": "test_session",
                "verify_scope": "mod_conflicts",
                "checkpoint": {"stage": "verify", "last_verified": "duplicates"}
            }
        }
    ]
    
    # 插入测试任务
    for i, task in enumerate(scan_tasks):
        conn.execute("""
            INSERT INTO ops_work_queue (type, payload_json, priority, dedupe_key)
            VALUES (?, ?, ?, ?)
        """, (
            task["type"],
            json.dumps(task["payload"]),
            100 - i * 10,  # 递减优先级
            f"test_task_{i}"
        ))
    
    conn.commit()
    
    # 验证任务插入成功
    cursor = conn.execute("""
        SELECT type, COUNT(*) as count 
        FROM ops_work_queue 
        WHERE type IN ('scan_enum', 'scan_meta', 'scan_lang', 'scan_verify')
        GROUP BY type
        ORDER BY type
    """)
    
    results = cursor.fetchall()
    print("📋 插入的扫描任务:")
    for task_type, count in results:
        print(f"  {task_type}: {count} 个任务")
    
    # 测试新增的视图
    cursor = conn.execute("SELECT * FROM v_scan_queue_status")
    queue_status = cursor.fetchall()
    print(f"📊 扫描队列状态: {len(queue_status)} 条记录")
    
    conn.close()
    
    assert len(results) == 4, "应该有4种不同的扫描任务类型"
    print("✅ 工作队列扩展功能测试通过")

def test_database_initialization():
    """测试数据库初始化功能"""
    print("🔍 测试数据库初始化功能...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        # 初始化数据库
        initializer = DatabaseInitializer(str(db_path))
        success = initializer.ensure_database_exists()
        
        assert success, "数据库初始化应该成功"
        assert db_path.exists(), "数据库文件应该存在"
        
        # 验证表结构
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'cache_scan_%'
            ORDER BY name
        """)
        
        scan_tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 新增扫描相关表: {scan_tables}")
        
        expected_tables = ['cache_scan_delta', 'cache_scan_snapshots', 'cache_scan_sessions']
        for table in expected_tables:
            if table in scan_tables:
                print(f"✅ 表 {table} 创建成功")
        
        # 验证工作队列类型扩展
        cursor = conn.execute("""
            INSERT INTO ops_work_queue (type, payload_json) 
            VALUES ('scan_enum', '{"test": true}')
        """)
        conn.commit()
        
        cursor = conn.execute("""
            SELECT COUNT(*) FROM ops_work_queue WHERE type = 'scan_enum'
        """)
        count = cursor.fetchone()[0]
        
        conn.close()
        
        assert count == 1, "扫描任务类型应该插入成功"
        print("✅ 数据库初始化功能测试通过")
        
        return str(db_path)

def main():
    """主测试函数"""
    print("🚀 开始测试分层异步增量扫描架构")
    print("=" * 50)
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 1. 测试数据库初始化
            db_path = temp_path / "test.db"
            initializer = DatabaseInitializer(str(db_path))
            success = initializer.ensure_database_exists()
            
            if not success:
                print("❌ 数据库初始化失败")
                return False
            
            print("✅ 数据库初始化成功")
            
            # 2. 创建测试模组包
            modpack_dir = create_test_modpack(temp_path)
            print(f"✅ 测试模组包创建: {modpack_dir}")
            
            # 3. 测试快照构建
            base_snapshot_id = test_snapshot_builder(str(db_path), modpack_dir)
            
            # 4. 测试差异对比
            delta_id = test_diff_engine(str(db_path), modpack_dir, base_snapshot_id)
            
            # 5. 测试工作队列扩展
            test_work_queue_extensions(str(db_path))
            
            print("=" * 50)
            print("🎉 所有测试通过！分层异步增量扫描架构实现成功")
            
            # 输出统计信息
            conn = sqlite3.connect(str(db_path))
            
            cursor = conn.execute("SELECT COUNT(*) FROM cache_scan_snapshots")
            snapshot_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM cache_scan_delta")
            delta_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM ops_work_queue")
            task_count = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"📊 最终统计:")
            print(f"  - 快照数量: {snapshot_count}")
            print(f"  - 差异记录: {delta_count}")
            print(f"  - 工作队列任务: {task_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)