#!/usr/bin/env python3
"""
测试新的翻译存储逻辑
"""

import asyncio
import sys
import sqlite3
from pathlib import Path

# 添加路径
sys.path.insert(0, '/home/saken/project/TH-Suite/apps/mc_l10n/backend')

async def test_new_storage():
    """测试新的翻译存储逻辑"""
    print("🧪 测试新的翻译存储逻辑")
    
    try:
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        service = get_simple_minecraft_scanner_service()
        print(f"✅ 服务实例化成功")
        print(f"📁 数据库路径: {service.db_path}")
        
        # 启动一个扫描
        scan_id = await service.start_scan(
            target_path="/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse",
            incremental=False,
            scan_options={"include_subdirectories": True}
        )
        print(f"🔍 扫描已启动: {scan_id}")
        
        # 等待扫描完成
        max_wait = 60  # 最多等60秒
        waited = 0
        while waited < max_wait:
            scan_status = await service.get_scan_status(scan_id)
            print(f"📊 扫描状态: {scan_status.get('status')} - 进度: {scan_status.get('progress', 0)}%")
            
            if scan_status.get('status') in ['completed', 'failed', 'cancelled']:
                break
            
            await asyncio.sleep(2)
            waited += 2
        
        # 检查数据库结果
        if Path(service.db_path).exists():
            conn = sqlite3.connect(str(service.db_path))
            cursor = conn.cursor()
            
            print("\n📋 数据库结果分析:")
            
            # 检查content_instances表
            cursor.execute("SELECT COUNT(*) FROM content_instances")
            total_content = cursor.fetchone()[0]
            print(f"  总翻译记录数: {total_content}")
            
            # 检查不同content_type的分布
            cursor.execute("""
                SELECT content_type, COUNT(*) as count
                FROM content_instances 
                GROUP BY content_type 
                ORDER BY count DESC
            """)
            type_distribution = cursor.fetchall()
            print(f"  内容类型分布:")
            for content_type, count in type_distribution:
                print(f"    - {content_type}: {count} 条")
            
            # 检查实际翻译内容样例
            cursor.execute("""
                SELECT content_key, source_text, language_code, content_source 
                FROM content_instances 
                WHERE content_type = 'translation'
                ORDER BY LENGTH(source_text) DESC
                LIMIT 5
            """)
            sample_translations = cursor.fetchall()
            print(f"  翻译内容样例:")
            for key, text, lang, source in sample_translations:
                print(f"    - [{lang}] {key}: '{text[:50]}...' (来源: {source})")
            
            # 检查数据库大小
            db_size = Path(service.db_path).stat().st_size
            print(f"\n💾 数据库文件大小: {db_size} 字节 ({db_size/1024:.1f} KB)")
            
            conn.close()
            
            if total_content > 50000:  # 期望有大量翻译记录
                print("✅ 新存储逻辑测试成功！数据库包含大量翻译内容")
                return True
            else:
                print(f"❌ 翻译内容仍然不足，只有 {total_content} 条记录")
                return False
        else:
            print("❌ 数据库文件未创建")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_new_storage())
    exit(0 if success else 1)