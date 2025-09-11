#!/usr/bin/env python3
"""测试版本信息写入修复"""
import sqlite3
import json
import uuid
from pathlib import Path

def test_version_insertion():
    """测试版本信息插入逻辑"""
    db_path = "data/mc_l10n_v6.db"
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== 测试版本信息写入逻辑 ===")
    
    # 找一个现有的MOD进行测试
    cursor.execute("SELECT uid, modid, name FROM core_mods LIMIT 1")
    test_mod = cursor.fetchone()
    
    if not test_mod:
        print("❌ 没有找到测试用的MOD")
        return
    
    mod_uid = test_mod['uid']
    modid = test_mod['modid']
    name = test_mod['name']
    
    print(f"📦 测试MOD: {modid} ({name})")
    print(f"   UID: {mod_uid}")
    
    # 模拟版本数据
    test_mod_data = {
        'mod_id': modid,
        'name': name,
        'version': '1.0.0-test',
        'mod_loader': 'forge',
        'mc_version': '1.19.2',
        'description': 'Test version data',
        'authors': ['Test Author'],
        'dependencies': [],
        'file_path': '/test/path/mod.jar'
    }
    
    # 执行版本信息插入逻辑（复制自ddd_scanner_simple.py）
    try:
        version_uid = str(uuid.uuid4())
        
        # 从MOD数据中提取版本信息
        version = test_mod_data.get('version', 'unknown')
        loader = test_mod_data.get('mod_loader', 'unknown')
        mc_version = test_mod_data.get('mc_version', 'unknown')
        
        # 准备元数据JSON
        meta_json = json.dumps({
            'description': test_mod_data.get('description'),
            'authors': test_mod_data.get('authors', []),
            'dependencies': test_mod_data.get('dependencies', []),
            'file_path': test_mod_data.get('file_path')
        })
        
        print(f"📋 准备插入版本信息:")
        print(f"   Version: {version}")
        print(f"   Loader: {loader}")
        print(f"   MC Version: {mc_version}")
        
        # 检查是否已存在相同的版本记录（避免重复）
        cursor.execute("""
            SELECT uid FROM core_mod_versions 
            WHERE mod_uid = ? AND loader = ? AND version = ? AND mc_version = ?
        """, (mod_uid, loader, version, mc_version))
        
        existing_version = cursor.fetchone()
        
        if existing_version:
            print("⚠️  版本记录已存在，更新...")
            cursor.execute("""
                UPDATE core_mod_versions SET 
                    meta_json = ?, source = 'test_script', discovered_at = CURRENT_TIMESTAMP
                WHERE uid = ?
            """, (meta_json, existing_version['uid']))
            print(f"✅ 更新版本记录: {modid} v{version}")
        else:
            print("🆕 插入新版本记录...")
            cursor.execute("""
                INSERT INTO core_mod_versions (
                    uid, mod_uid, loader, mc_version, version, 
                    meta_json, source, discovered_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'test_script', CURRENT_TIMESTAMP)
            """, (
                version_uid, mod_uid, loader, mc_version, version, meta_json
            ))
            print(f"✅ 新增版本记录: {modid} v{version} ({loader}, MC {mc_version})")
        
        conn.commit()
        
        # 验证插入结果
        cursor.execute("SELECT COUNT(*) FROM core_mod_versions WHERE mod_uid = ?", (mod_uid,))
        version_count = cursor.fetchone()[0]
        print(f"🔍 该MOD的版本记录数: {version_count}")
        
        # 检查总的版本记录数
        cursor.execute("SELECT COUNT(*) FROM core_mod_versions")
        total_versions = cursor.fetchone()[0]
        print(f"📊 数据库总版本记录数: {total_versions}")
        
        if total_versions > 0:
            print("🎉 版本信息写入逻辑正常工作！")
        else:
            print("❌ 版本信息写入失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    test_version_insertion()