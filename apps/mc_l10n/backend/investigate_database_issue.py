#!/usr/bin/env python3
"""
深度调查数据库问题 - 844KB异常
"""

import sqlite3
import sys
from pathlib import Path

def investigate_database():
    """深度调查数据库问题"""
    print("🔍 深度调查数据库问题")
    
    db_path = Path("data/mc_l10n_v2_1.db")
    print(f"📁 数据库路径: {db_path.absolute()}")
    print(f"📊 文件大小: {db_path.stat().st_size} 字节 ({db_path.stat().st_size/1024:.1f} KB)")
    
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        
        print("\n📋 表结构和记录数:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        total_records = 0
        for table in tables:
            table_name = table[0]
            if not table_name.startswith('sqlite_'):
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                total_records += count
                print(f"  📄 {table_name}: {count} 条记录")
        
        print(f"\n🎯 总记录数: {total_records}")
        
        # 检查content_instances表的实际内容
        print("\n🔍 检查content_instances表:")
        cursor.execute("SELECT COUNT(*) FROM content_instances")
        content_count = cursor.fetchone()[0]
        print(f"  总记录数: {content_count}")
        
        if content_count > 0:
            # 查看内容分布
            cursor.execute("""
                SELECT content_source, COUNT(*) as count 
                FROM content_instances 
                GROUP BY content_source 
                ORDER BY count DESC 
                LIMIT 10
            """)
            sources = cursor.fetchall()
            print(f"  按来源分布 (前10):")
            for source, count in sources:
                print(f"    - {source}: {count}")
            
            # 查看语言分布  
            cursor.execute("""
                SELECT language_code, COUNT(*) as count
                FROM content_instances
                GROUP BY language_code
                ORDER BY count DESC
                LIMIT 10
            """)
            langs = cursor.fetchall()
            print(f"  按语言分布 (前10):")
            for lang, count in langs:
                print(f"    - {lang}: {count}")
            
            # 检查source_text字段
            cursor.execute("""
                SELECT source_text, COUNT(*) as count
                FROM content_instances
                GROUP BY source_text
                ORDER BY count DESC
                LIMIT 5
            """)
            texts = cursor.fetchall()
            print(f"  source_text内容:")
            for text, count in texts:
                print(f"    - '{text}': {count} 次")
        
        # 检查数据库文件大小异常的可能原因
        print("\n💾 数据库空间分析:")
        
        # 获取页面大小和页面数
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        
        calculated_size = page_size * page_count
        actual_size = db_path.stat().st_size
        
        print(f"  页面大小: {page_size} 字节")
        print(f"  页面数量: {page_count}")
        print(f"  计算大小: {calculated_size} 字节")
        print(f"  实际大小: {actual_size} 字节")
        print(f"  大小差异: {abs(calculated_size - actual_size)} 字节")
        
        # 检查是否有实际的翻译文本内容
        cursor.execute("""
            SELECT file_path, language_code, content_key, LENGTH(source_text) as text_length
            FROM content_instances 
            ORDER BY text_length DESC
            LIMIT 5
        """)
        text_samples = cursor.fetchall()
        print(f"\n📝 翻译文本示例:")
        for file_path, lang, key, length in text_samples:
            print(f"  {lang} - {key}: {length} 字符")
            print(f"    文件: {file_path}")
        
        # 检查数据库是否被真正写入
        cursor.execute("SELECT MAX(created_at) FROM content_instances")
        latest_time = cursor.fetchone()[0]
        print(f"\n⏰ 最新记录时间: {latest_time}")
        
    except Exception as e:
        print(f"❌ 调查失败: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        conn.close()

def check_actual_scan_functionality():
    """检查实际扫描功能"""
    print("\n🔧 检查实际扫描功能...")
    
    try:
        sys.path.insert(0, '/home/saken/project/TH-Suite/apps/mc_l10n/backend')
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        service = get_simple_minecraft_scanner_service()
        print(f"✅ 服务实例创建成功")
        print(f"📁 数据库路径: {service.db_path}")
        
        # 检查当前活跃扫描
        active_scans = service._active_scans
        print(f"🔄 活跃扫描数: {len(active_scans)}")
        
        if active_scans:
            for scan_id, scan_info in active_scans.items():
                print(f"  扫描ID: {scan_id}")
                print(f"  状态: {scan_info.get('status', 'unknown')}")
                print(f"  进度: {scan_info.get('progress', 0)}%")
        
    except Exception as e:
        print(f"❌ 扫描功能检查失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    investigate_database()
    check_actual_scan_functionality()