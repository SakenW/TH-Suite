#!/usr/bin/env python3
"""为现有MOD回填版本信息"""
import sqlite3
import json
import uuid
from pathlib import Path

def backfill_mod_versions():
    """为现有的MOD回填版本信息"""
    db_path = "data/mc_l10n_v6.db"
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== 开始为现有MOD回填版本信息 ===")
    
    # 获取所有没有版本信息的MOD
    cursor.execute("""
        SELECT m.uid, m.modid, m.name 
        FROM core_mods m 
        LEFT JOIN core_mod_versions v ON m.uid = v.mod_uid 
        WHERE v.mod_uid IS NULL
    """)
    
    mods_without_versions = cursor.fetchall()
    
    if not mods_without_versions:
        print("✅ 所有MOD都已有版本信息")
        return
    
    print(f"📊 发现 {len(mods_without_versions)} 个MOD缺少版本信息")
    
    success_count = 0
    error_count = 0
    
    for mod in mods_without_versions:
        mod_uid = mod['uid']
        modid = mod['modid']
        name = mod['name']
        
        try:
            # 生成版本记录的UID
            version_uid = str(uuid.uuid4())
            
            # 从MOD名称智能推断版本信息
            # 这里使用一些基本的推断逻辑
            version = 'unknown'
            loader = 'unknown'
            mc_version = 'unknown'
            
            # 尝试从名称中提取一些信息
            if any(keyword in name.lower() for keyword in ['fabric', 'api']):
                loader = 'fabric'
            elif any(keyword in name.lower() for keyword in ['forge']):
                loader = 'forge'
            else:
                # 根据MOD数量分布，大部分可能是forge
                loader = 'forge'
            
            # 准备元数据JSON
            meta_json = json.dumps({
                'description': f'Auto-generated version info for {name}',
                'authors': [],
                'dependencies': [],
                'file_path': None,
                'note': 'Backfilled version data'
            })
            
            # 插入版本记录
            cursor.execute("""
                INSERT INTO core_mod_versions (
                    uid, mod_uid, loader, mc_version, version, 
                    meta_json, source, discovered_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'backfill_script', CURRENT_TIMESTAMP)
            """, (
                version_uid, mod_uid, loader, mc_version, version, meta_json
            ))
            
            success_count += 1
            
            if success_count % 50 == 0:
                print(f"📈 已处理 {success_count} 个MOD...")
                
        except Exception as e:
            print(f"❌ 处理MOD失败 {modid}: {e}")
            error_count += 1
    
    # 提交所有更改
    conn.commit()
    conn.close()
    
    print(f"✅ 版本信息回填完成！")
    print(f"   成功: {success_count} 个MOD")
    print(f"   失败: {error_count} 个MOD")
    
    # 验证结果
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM core_mod_versions")
    total_versions = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM core_mods")
    total_mods = cursor.fetchone()[0]
    conn.close()
    
    print(f"📊 最终统计:")
    print(f"   总MOD数: {total_mods}")
    print(f"   总版本记录数: {total_versions}")
    print(f"   覆盖率: {(total_versions/total_mods*100):.1f}%")

if __name__ == "__main__":
    backfill_mod_versions()