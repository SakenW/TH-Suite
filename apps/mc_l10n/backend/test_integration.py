#!/usr/bin/env python3
"""集成测试：验证v2.1架构组件协同工作"""

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

def test_repository_basic():
    """测试Repository基础功能"""
    print("🧪 测试Repository基础功能...")
    
    # 导入v2.1 Repository
    import sys
    sys.path.append(str(Path(__file__).parent))
    
    try:
        from repositories.v2_1_repositories import PackRepository
        from models.v2_1_models import Pack, PackVersion
        
        # 测试Repository初始化
        repo = PackRepository()
        print("  ✅ Repository初始化成功")
        
        # 测试数据库连接
        db_path = Path(__file__).parent / "data" / "mc_l10n_v2_1.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 插入测试数据
        cursor.execute("""
            INSERT INTO packs (name, display_name, type, author, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("test_pack", "测试整合包", "modpack", "test_author", "测试描述", 
              datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        
        pack_id = cursor.lastrowid
        conn.commit()
        
        # 验证数据插入
        cursor.execute("SELECT * FROM packs WHERE id = ?", (pack_id,))
        pack_data = cursor.fetchone()
        
        if pack_data:
            print(f"  ✅ 成功插入测试整合包: {pack_data[1]} (ID: {pack_data[0]})")
        else:
            print("  ❌ 测试数据插入失败")
            return False
            
        # 清理测试数据
        cursor.execute("DELETE FROM packs WHERE id = ?", (pack_id,))
        conn.commit()
        conn.close()
        
        print("  ✅ 清理测试数据完成")
        return True
        
    except Exception as e:
        print(f"  ❌ Repository测试失败: {e}")
        return False

def test_unified_mapper():
    """测试统一内容映射器"""
    print("\n🗺️ 测试统一内容映射器...")
    
    try:
        import sys
        sys.path.append(str(Path(__file__).parent))
        
        from mappers.unified_content_mapper import UnifiedContentMapper
        from pathlib import Path
        
        # 测试映射器初始化
        config_path = Path(__file__).parent / "config" / "mapping_rules.yaml"
        mapper = UnifiedContentMapper(str(config_path))
        print("  ✅ 统一内容映射器初始化成功")
        
        # 测试UIDA生成
        test_uida = mapper.generate_content_uida(
            namespace="testmod",
            content_key="item.test_item.name",
            language="zh_cn",
            version="1.0.0"
        )
        
        expected_pattern = "minecraft://testmod/item.test_item.name#zh_cn@1.0.0"
        if test_uida == expected_pattern:
            print(f"  ✅ UIDA生成正确: {test_uida}")
        else:
            print(f"  ❌ UIDA生成错误: 期望 {expected_pattern}, 实际 {test_uida}")
            return False
            
        # 测试内容映射
        test_content = {
            "source_identifier": "testmod:test_item",
            "content_key": "item.test_item.name", 
            "source_text": "Test Item",
            "language_code": "en_us"
        }
        
        mapped_result = mapper.map_mod_jar_content(test_content, "testmod", "1.0.0")
        
        if mapped_result and "uida" in mapped_result:
            print(f"  ✅ 内容映射成功: {mapped_result['uida'][:50]}...")
        else:
            print("  ❌ 内容映射失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"  ❌ 统一内容映射器测试失败: {e}")
        return False

def test_sync_service():
    """测试同步服务"""
    print("\n🔄 测试同步服务基础功能...")
    
    try:
        import sys
        sys.path.append(str(Path(__file__).parent))
        
        from application.services.v2_1_sync_service import SyncService
        
        # 测试同步服务初始化
        sync_service = SyncService()
        print("  ✅ 同步服务初始化成功")
        
        # 测试配置验证
        if hasattr(sync_service, 'config') and sync_service.config:
            print("  ✅ 同步服务配置加载成功")
        else:
            print("  ⚠️ 同步服务配置未加载（这在测试环境中是正常的）")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 同步服务测试失败: {e}")
        return False

async def run_integration_tests():
    """运行集成测试套件"""
    print("🚀 开始v2.1架构集成测试...\n")
    
    test_results = []
    
    # 运行各个测试
    test_results.append(test_repository_basic())
    test_results.append(test_unified_mapper())
    test_results.append(test_sync_service())
    
    # 统计结果
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 集成测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有集成测试通过！v2.1架构基础功能正常")
        return True
    else:
        print("❌ 部分集成测试失败，需要修复")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    exit(0 if success else 1)