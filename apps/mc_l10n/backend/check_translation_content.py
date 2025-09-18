#!/usr/bin/env python3
"""
检查翻译内容是否正确存储到数据库中
"""

import sqlite3
from pathlib import Path

def check_translation_content():
    """检查翻译内容存储情况"""
    db_path = Path("data/mc_l10n_v2_1.db")
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    print(f"📁 连接数据库: {db_path}")
    conn = sqlite3.connect(str(db_path))
    
    try:
        cursor = conn.cursor()
        
        # 1. 检查content_instances表记录数
        cursor.execute("SELECT COUNT(*) FROM content_instances")
        content_count = cursor.fetchone()[0]
        print(f"📊 content_instances表记录数: {content_count}")
        
        # 2. 检查pack_content_relations表记录数  
        cursor.execute("SELECT COUNT(*) FROM pack_content_relations")
        relation_count = cursor.fetchone()[0]
        print(f"📊 pack_content_relations表记录数: {relation_count}")
        
        if content_count > 0:
            # 3. 显示前几条content_instances记录
            cursor.execute("""
                SELECT content_key, content_source, language_code, content_type, file_path
                FROM content_instances 
                LIMIT 10
            """)
            contents = cursor.fetchall()
            
            print(f"\n📋 content_instances前10条记录:")
            for i, content in enumerate(contents, 1):
                content_key, content_source, language_code, content_type, file_path = content
                print(f"  {i}. {content_source} - {language_code} - {content_key}")
                print(f"     文件路径: {file_path}")
            
            # 4. 按语言统计
            cursor.execute("""
                SELECT language_code, COUNT(*) as count
                FROM content_instances 
                GROUP BY language_code
                ORDER BY count DESC
            """)
            lang_stats = cursor.fetchall()
            
            print(f"\n📊 按语言统计:")
            for lang_code, count in lang_stats:
                print(f"  {lang_code}: {count} 条记录")
            
            # 5. 按MOD统计
            cursor.execute("""
                SELECT content_source, COUNT(*) as count
                FROM content_instances 
                GROUP BY content_source
                ORDER BY count DESC
                LIMIT 10
            """)
            mod_stats = cursor.fetchall()
            
            print(f"\n📊 按MOD统计（前10）:")
            for mod_name, count in mod_stats:
                print(f"  {mod_name}: {count} 条翻译")
        
        else:
            print("❌ content_instances表为空，翻译内容未被保存")
            
            # 检查扫描是否发现了语言文件
            print("\n🔍 检查最近扫描结果...")
            cursor.execute("""
                SELECT scan_id, statistics
                FROM scan_results 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            recent_scans = cursor.fetchall()
            
            for scan_id, stats in recent_scans:
                print(f"扫描ID {scan_id}: {stats}")
        
        return content_count > 0
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = check_translation_content()
    print(f"\n{'🎉 翻译内容存储正常' if success else '❌ 翻译内容存储异常'}")