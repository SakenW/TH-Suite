#!/usr/bin/env python3
"""清理数据库中错误的MOD数据"""

import sys
import sqlite3
import re
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.ddd_scanner_simple import DDDScanner

def parse_filename_intelligently(filename: str) -> tuple[str, str]:
    """智能解析文件名（复制自扫描器）"""
    import re
    
    # 模式1: 匹配 name-mcversion-modversion 格式
    match1 = re.match(r'^(.+?)-(\d+\.\d+(?:\.\d+)?(?:-\d+\.\d+(?:\.\d+)?)*)$', filename)
    if match1:
        name_part, version_part = match1.groups()
        return name_part, version_part
        
    # 模式2: 匹配 name-version 格式
    match2 = re.match(r'^(.+?)-((?:\d+\.\d+(?:\.\d+)?.*?|v\d+\.\d+.*?))$', filename)
    if match2:
        name_part, version_part = match2.groups()
        if len(name_part) >= 3:
            return name_part, version_part
            
    # 模式3: 匹配末尾有版本号的格式
    match3 = re.match(r'^(.+?)_(\d+\.\d+(?:\.\d+)?)$', filename)
    if match3:
        name_part, version_part = match3.groups()
        return name_part, version_part
        
    return filename, ""

def cleanup_mod_data():
    """清理MOD数据"""
    # 使用相对路径获取数据库位置
    db_path = project_root / "data" / "mc_l10n_v6.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🧹 开始清理错误的MOD数据...")
    print("=" * 80)
    
    # 1. 查找所有可能有问题的模组（根据实际表结构）
    cursor.execute("""
        SELECT uid, name, modid, created_at
        FROM core_mods 
        WHERE name LIKE '%-%.%-%' OR name LIKE '%-%.%.%-%' OR name LIKE '%_%.%'
        ORDER BY created_at DESC
    """)
    
    problematic_mods = cursor.fetchall()
    print(f"📊 发现 {len(problematic_mods)} 个可能有问题的模组")
    
    if not problematic_mods:
        print("✅ 没有发现问题模组，数据库已清理！")
        conn.close()
        return
    
    print("\n🔍 分析前10个问题案例:")
    for i, mod in enumerate(problematic_mods[:10]):
        uid, name, modid, created_at = mod
        clean_name, extracted_version = parse_filename_intelligently(name)
        
        print(f"  {i+1}. 原始名称: {name}")
        print(f"     修正后: {clean_name} (版本: {extracted_version})")
        print(f"     ModID: {modid}")
        print()
    
    # 确认用户是否要继续
    print(f"⚠️  即将修复 {len(problematic_mods)} 个模组的名称和版本信息")
    confirm = input("是否继续？(y/N): ")
    
    if confirm.lower() != 'y':
        print("❌ 操作已取消")
        conn.close()
        return
    
    # 2. 逐个修复模组数据
    print("\n🔧 开始修复模组数据...")
    
    fixed_count = 0
    skipped_count = 0
    
    for mod in problematic_mods:
        uid, name, modid, created_at = mod
        
        # 使用新的解析逻辑
        clean_name, extracted_version = parse_filename_intelligently(name)
        
        # 检查是否真的需要修复
        if clean_name == name and not extracted_version:
            skipped_count += 1
            continue
            
        # 决定新的modid
        new_modid = modid if modid != name else clean_name
        
        try:
            # 更新core_mods表
            cursor.execute("""
                UPDATE core_mods 
                SET name = ?, modid = ?
                WHERE uid = ?
            """, (clean_name, new_modid, uid))
            
            # 如果有版本信息，更新core_mod_versions表
            if extracted_version:
                # 查找对应的版本记录
                cursor.execute("""
                    SELECT uid FROM core_mod_versions WHERE mod_uid = ?
                """, (uid,))
                version_records = cursor.fetchall()
                
                # 更新所有版本记录的version字段
                for version_record in version_records:
                    cursor.execute("""
                        UPDATE core_mod_versions 
                        SET version = ?
                        WHERE uid = ?
                    """, (extracted_version, version_record[0]))
            
            fixed_count += 1
            
            if fixed_count <= 10:  # 只显示前10个修复结果
                print(f"  ✅ 修复: {name} → {clean_name}")
                if extracted_version:
                    print(f"      版本: {extracted_version}")
            elif fixed_count == 11:
                print("  ... (更多修复结果已省略)")
                
        except Exception as e:
            print(f"  ❌ 修复失败: {name}, 错误: {e}")
    
    # 提交更改
    conn.commit()
    
    print(f"\n📊 修复完成统计:")
    print(f"  ✅ 成功修复: {fixed_count} 个模组")
    print(f"  ⏭️  跳过: {skipped_count} 个模组")
    
    # 3. 验证修复结果
    print("\n🔍 验证修复结果...")
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM core_mods 
        WHERE name LIKE '%-%.%-%' OR name LIKE '%-%.%.%-%' OR name LIKE '%_%.%'
    """)
    remaining_problems = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM core_mods")
    total_mods = cursor.fetchone()[0]
    
    print(f"  📊 总模组数: {total_mods}")
    print(f"  🚨 剩余问题: {remaining_problems}")
    print(f"  ✅ 修复率: {((len(problematic_mods) - remaining_problems) / len(problematic_mods) * 100):.1f}%")
    
    if remaining_problems == 0:
        print("\n🎉 所有MOD数据已成功清理！")
    else:
        print(f"\n⚠️  仍有 {remaining_problems} 个模组需要手动检查")
    
    conn.close()

if __name__ == "__main__":
    cleanup_mod_data()