#!/usr/bin/env python3
"""
测试完整的扫描流程，找出数据库写入问题
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加路径
sys.path.insert(0, '/home/saken/project/TH-Suite/apps/mc_l10n/backend')

async def test_full_scan_flow():
    """测试完整的扫描流程"""
    print("🔍 开始测试完整扫描流程")
    
    try:
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        # 获取扫描服务
        service = get_simple_minecraft_scanner_service()
        print(f"✅ 获取扫描服务成功，db_path: {service.db_path}")
        
        # 创建一个临时测试目录结构
        test_dir = Path("/tmp/test_minecraft_scan")
        test_dir.mkdir(exist_ok=True)
        
        # 创建一个模拟的mod文件
        (test_dir / "test_mod.jar").touch()
        
        print(f"📁 创建测试目录: {test_dir}")
        
        # 启动扫描
        scan_result = await service.start_scan(
            target_path=str(test_dir),
            incremental=False,
            scan_options={
                "include_subdirectories": True,
                "validate_after_scan": True,
                "generate_statistics": True,
                "file_extensions": [".jar", ".zip"],
                "max_depth": 10,
                "max_file_size_mb": 500
            }
        )
        
        print(f"📊 扫描启动结果: {json.dumps(scan_result, indent=2, ensure_ascii=False)}")
        
        if not scan_result.get("success"):
            print("❌ 扫描启动失败")
            return False
        
        scan_id = scan_result["scan_id"]
        print(f"🔄 扫描ID: {scan_id}")
        
        # 等待扫描完成
        for i in range(30):  # 最多等待30秒
            await asyncio.sleep(1)
            status_result = await service.get_scan_status(scan_id)
            
            if status_result.get("success"):
                status = status_result.get("status", "unknown")
                progress = status_result.get("progress", 0)
                print(f"⏳ 扫描状态: {status}, 进度: {progress}%")
                
                if status in ["completed", "failed"]:
                    break
            else:
                print(f"❌ 获取状态失败: {status_result}")
                break
        
        # 检查最终状态
        final_status = await service.get_scan_status(scan_id)
        print(f"🏁 最终状态: {json.dumps(final_status, indent=2, ensure_ascii=False)}")
        
        # 检查数据库中是否有数据
        import sqlite3
        db_path = Path("data/mc_l10n_v2_1.db")
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM packs")
            pack_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mod_version_instances")
            mod_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM pack_mod_relations")
            relation_count = cursor.fetchone()[0]
            
            print(f"📋 数据库验证结果:")
            print(f"  - Pack记录: {pack_count}")
            print(f"  - Mod记录: {mod_count}")
            print(f"  - 关联记录: {relation_count}")
            
            # 显示具体的数据
            cursor.execute("SELECT name, project_type, path FROM packs")
            packs = cursor.fetchall()
            if packs:
                print("📦 找到的Pack:")
                for pack in packs:
                    print(f"  - {pack[0]} ({pack[1]}) @ {pack[2]}")
            
            cursor.execute("SELECT mod_name, jar_file_path FROM mod_version_instances")
            mods = cursor.fetchall()
            if mods:
                print("🔧 找到的Mod:")
                for mod in mods:
                    print(f"  - {mod[0]} @ {mod[1]}")
            
            conn.close()
            
            if pack_count > 0 or mod_count > 0:
                print("🎉 数据库写入测试成功！")
                return True
            else:
                print("❌ 数据库中没有找到预期的数据")
                return False
        else:
            print("❌ 数据库文件不存在")
            return False
            
        # 清理测试文件
        (test_dir / "test_mod.jar").unlink(missing_ok=True)
        test_dir.rmdir()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def main():
    print("🚀 开始完整扫描流程测试")
    success = await test_full_scan_flow()
    print("🎯 测试完成" if success else "❌ 测试失败")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)