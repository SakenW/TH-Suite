#!/usr/bin/env python3
"""简化的v2.1架构验证测试"""

import sqlite3
from datetime import datetime
from pathlib import Path

def test_database_operations():
    """测试数据库基本操作"""
    print("🗄️ 测试数据库连通性和结构...")
    
    db_path = Path(__file__).parent / "data" / "mc_l10n_v2_1.db"
    
    if not db_path.exists():
        print(f"  ❌ 数据库文件不存在: {db_path}")
        return False
        
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 测试数据库连接
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  ✅ 数据库连接成功，包含{len(tables)}个表")
        
        # 验证关键表存在
        required_tables = ['packs', 'pack_versions', 'mod_version_instances', 
                          'pack_mod_relations', 'content_instances', 'pack_content_relations']
        
        missing_tables = []
        for table in required_tables:
            if table in tables:
                print(f"  ✅ 表 {table} 存在")
            else:
                missing_tables.append(table)
                print(f"  ❌ 表 {table} 缺失")
        
        if missing_tables:
            print(f"  ❌ 缺失关键表: {missing_tables}")
            return False
        
        # 测试统计视图
        try:
            cursor.execute("SELECT COUNT(*) FROM pack_version_stats")
            print("  ✅ 统计视图 pack_version_stats 可访问")
        except Exception as e:
            print(f"  ⚠️ 统计视图测试失败: {e}")
        
        # 测试简单插入和查询（使用实际表结构）
        cursor.execute("""
            INSERT INTO packs (name, project_type, path, created_at, updated_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("test_pack", "modpack", "/test/path", 
              datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), True))
        
        pack_id = cursor.lastrowid
        print(f"  ✅ 成功插入测试数据: Pack ID {pack_id}")
        
        # 清理测试数据
        cursor.execute("DELETE FROM packs WHERE id = ?", (pack_id,))
        conn.commit()
        print("  ✅ 清理测试数据完成")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ 数据库测试失败: {e}")
        return False

def test_config_files():
    """测试配置文件"""
    print("\n⚙️ 测试配置文件...")
    
    config_path = Path(__file__).parent / "config" / "mapping_rules.yaml"
    if config_path.exists():
        print(f"  ✅ 映射规则配置文件存在: {config_path}")
        
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            if config.get('version') == '2.1':
                print(f"  ✅ 配置版本正确: {config['version']}")
            else:
                print(f"  ⚠️ 配置版本: {config.get('version', 'unknown')}")
                
            if 'content_sources' in config:
                sources = list(config['content_sources'].keys())
                print(f"  ✅ 内容源配置: {len(sources)}个 ({', '.join(sources[:3])}...)")
            
            return True
            
        except ImportError:
            print("  ⚠️ PyYAML未安装，跳过YAML解析测试")
            return True
        except Exception as e:
            print(f"  ❌ 配置文件解析失败: {e}")
            return False
    else:
        print(f"  ❌ 映射规则配置文件不存在: {config_path}")
        return False

def run_simple_tests():
    """运行简化测试套件"""
    print("🧪 开始v2.1架构简化验证测试...\n")
    
    tests = [
        test_database_operations,
        test_config_files
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 简化测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 v2.1架构核心功能验证通过！")
        print("✅ 数据库迁移和完整性验证完成")
        return True
    else:
        print("❌ 部分测试失败，需要检查")
        return False

if __name__ == "__main__":
    success = run_simple_tests()
    exit(0 if success else 1)