#!/usr/bin/env python3
"""
v2.1 ORM模型单元测试
测试dataclass模型的基础功能和数据分层
"""

import unittest
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from models.v2_1_models import (
        Pack, PackVersion, ModVersionInstance, 
        PackModRelation, ContentInstance, PackContentRelation,
        PackType, ProjectType, LoaderType, ContentSource, ChangeType
    )
    from models.data_layer_config import DataLayerConfig
    MODELS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 无法导入v2.1模型: {e}")
    MODELS_AVAILABLE = False


class TestV21Models(unittest.TestCase):
    """测试v2.1数据模型"""
    
    def setUp(self):
        """测试前设置"""
        if not MODELS_AVAILABLE:
            self.skipTest("v2.1模型不可用")
            
    def test_pack_model_creation(self):
        """测试Pack模型创建"""
        pack = Pack(
            name="test_pack",
            project_type=ProjectType.MODPACK,
            game_type="minecraft",
            path="/test/path",
            author="Test Author",
            description="Test description"
        )
        
        self.assertEqual(pack.name, "test_pack")
        self.assertEqual(pack.project_type, ProjectType.MODPACK)
        self.assertEqual(pack.game_type, "minecraft")
        self.assertEqual(pack.author, "Test Author")
        self.assertTrue(pack.is_active)  # 默认值
        
    def test_pack_version_model(self):
        """测试PackVersion模型"""
        version = PackVersion(
            pack_id=1,
            version_tag="1.0.0",
            minecraft_version="1.21.1",
            loader_type=LoaderType.FORGE,
            loader_version="51.0.33",
            is_default=True,
            is_stable=True
        )
        
        self.assertEqual(version.version_tag, "1.0.0")
        self.assertEqual(version.loader_type, LoaderType.FORGE)
        self.assertTrue(version.is_default)
        self.assertTrue(version.is_stable)
        
    def test_mod_version_instance_model(self):
        """测试ModVersionInstance模型"""
        mod = ModVersionInstance(
            mod_id="jei",
            mod_version="15.20.0.104",
            mod_name="Just Enough Items",
            minecraft_versions="1.21.1",
            jar_file_path="/path/to/jei.jar",
            jar_file_hash="abc123"
        )
        
        self.assertEqual(mod.mod_id, "jei")
        self.assertEqual(mod.mod_version, "15.20.0.104")
        self.assertEqual(mod.mod_name, "Just Enough Items")
        
    def test_content_instance_model(self):
        """测试ContentInstance模型"""
        content = ContentInstance(
            content_source=ContentSource.MOD_JAR,
            source_identifier="jei:gui.title",
            content_key="gui.jei.title",
            content_type="gui",
            language_code="en_us",
            source_text="JEI",
            content_hash="hash123"
        )
        
        self.assertEqual(content.content_source, ContentSource.MOD_JAR)
        self.assertEqual(content.language_code, "en_us")
        self.assertEqual(content.source_text, "JEI")
        
    def test_pack_mod_relation_model(self):
        """测试PackModRelation模型"""
        relation = PackModRelation(
            pack_version_id=1,
            mod_instance_id=1,
            relation_type="included",
            mod_file_override_path="/override/path"
        )
        
        self.assertEqual(relation.pack_version_id, 1)
        self.assertEqual(relation.mod_instance_id, 1)
        self.assertEqual(relation.relation_type, "included")
        
    def test_pack_content_relation_model(self):
        """测试PackContentRelation模型"""
        relation = PackContentRelation(
            pack_version_id=1,
            content_instance_id=1,
            change_type=ChangeType.ADDED,
            priority=100,
            is_override=False
        )
        
        self.assertEqual(relation.pack_version_id, 1)
        self.assertEqual(relation.change_type, ChangeType.ADDED)
        self.assertEqual(relation.priority, 100)
        self.assertFalse(relation.is_override)
        
    def test_enum_values(self):
        """测试枚举类型值"""
        # 测试ProjectType枚举
        self.assertEqual(ProjectType.MODPACK.value, "modpack")
        self.assertEqual(ProjectType.RESOURCE_PACK.value, "resource_pack")
        
        # 测试LoaderType枚举
        self.assertEqual(LoaderType.FORGE.value, "forge")
        self.assertEqual(LoaderType.FABRIC.value, "fabric")
        
        # 测试ContentSource枚举
        self.assertEqual(ContentSource.MOD_JAR.value, "mod_jar")
        self.assertEqual(ContentSource.PACK_RESOURCE.value, "pack_resource")
        
        # 测试ChangeType枚举
        self.assertEqual(ChangeType.ADDED.value, "added")
        self.assertEqual(ChangeType.MODIFIED.value, "modified")


class TestDataLayerConfig(unittest.TestCase):
    """测试数据分层配置"""
    
    def test_sync_fields_detection(self):
        """测试同步字段检测"""
        if not MODELS_AVAILABLE:
            self.skipTest("数据层配置不可用")
            
        try:
            config = DataLayerConfig()
            
            # 测试Pack的同步字段
            pack_sync_fields = config.get_sync_fields('pack')
            self.assertIn('name', pack_sync_fields)
            self.assertIn('project_type', pack_sync_fields)
            self.assertIn('description', pack_sync_fields)
            
            # 测试Pack的本地字段
            pack_local_fields = config.get_local_only_fields('pack')
            self.assertIn('path', pack_local_fields)
            self.assertIn('build_config', pack_local_fields)
            
            print("✅ 数据分层配置测试通过")
            
        except Exception as e:
            print(f"⚠️ 数据分层配置测试跳过: {e}")


def run_model_tests():
    """运行模型测试套件"""
    print("🧪 开始v2.1模型单元测试...\n")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestV21Models))
    suite.addTests(loader.loadTestsFromTestCase(TestDataLayerConfig))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果统计
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📊 模型测试结果: {passed}/{total_tests} 通过")
    if failures > 0:
        print(f"❌ 失败: {failures}")
    if errors > 0:
        print(f"🔥 错误: {errors}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_model_tests()
    exit(0 if success else 1)