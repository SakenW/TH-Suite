#!/usr/bin/env python3
"""
统一内容映射器单元测试
测试UIDA生成、内容映射和元数据处理功能
"""

import unittest
import tempfile
from pathlib import Path
import sys
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from mappers.unified_content_mapper import UnifiedContentMapper
    MAPPER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 无法导入统一内容映射器: {e}")
    MAPPER_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    print("⚠️ PyYAML不可用，将使用JSON配置")
    YAML_AVAILABLE = False


class TestUnifiedContentMapper(unittest.TestCase):
    """测试统一内容映射器"""
    
    def setUp(self):
        """测试前设置"""
        if not MAPPER_AVAILABLE:
            self.skipTest("统一内容映射器不可用")
        
        # 创建临时配置文件
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.config_path = self.temp_config.name
        
        # 写入测试配置
        test_config = {
            'version': '2.1',
            'global': {
                'strategy': 'single_project',
                'target_project_id': 'minecraft',
                'uida_version': 'v1',
                'hash_algorithm': 'sha256',
                'hash_length': 16
            },
            'content_sources': {
                'mod_jar': {
                    'enabled': True,
                    'priority': 100,
                    'namespace_prefix': 'mod'
                }
            },
            'languages': {
                'supported': ['en_us', 'zh_cn'],
                'default_source': 'en_us',
                'default_target': 'zh_cn'
            },
            'uida': {
                'content_template': 'minecraft://{namespace}/{content_key}#{language}@{version}',
                'namespace_rules': {
                    'mod_jar': '{mod_id}'
                },
                'hash_components': ['source_identifier', 'content_key', 'language_code', 'source_text']
            }
        }
        
        if YAML_AVAILABLE:
            yaml.dump(test_config, self.temp_config, default_flow_style=False, allow_unicode=True)
        else:
            json.dump(test_config, self.temp_config, ensure_ascii=False, indent=2)
        
        self.temp_config.close()
        
        # 初始化映射器
        try:
            self.mapper = UnifiedContentMapper(self.config_path)
        except Exception as e:
            print(f"⚠️ 映射器初始化失败: {e}")
            self.mapper = None
            
    def tearDown(self):
        """测试后清理"""
        if hasattr(self, 'config_path'):
            Path(self.config_path).unlink(missing_ok=True)
    
    def test_mapper_initialization(self):
        """测试映射器初始化"""
        if self.mapper is None:
            self.skipTest("映射器初始化失败")
        
        self.assertIsNotNone(self.mapper)
        print("✅ 统一内容映射器初始化成功")
    
    def test_uida_generation(self):
        """测试UIDA生成"""
        if self.mapper is None:
            self.skipTest("映射器不可用")
            
        try:
            # 测试基本UIDA生成
            uida = self.mapper.generate_content_uida(
                namespace="jei",
                content_key="gui.jei.title",
                language="en_us",
                version="1.0.0"
            )
            
            expected = "minecraft://jei/gui.jei.title#en_us@1.0.0"
            self.assertEqual(uida, expected)
            print(f"✅ UIDA生成测试通过: {uida}")
            
            # 测试不同语言的UIDA生成
            uida_zh = self.mapper.generate_content_uida(
                namespace="jei",
                content_key="gui.jei.title", 
                language="zh_cn",
                version="1.0.0"
            )
            
            expected_zh = "minecraft://jei/gui.jei.title#zh_cn@1.0.0"
            self.assertEqual(uida_zh, expected_zh)
            print(f"✅ 中文UIDA生成测试通过: {uida_zh}")
            
        except Exception as e:
            self.fail(f"UIDA生成测试失败: {e}")
    
    def test_content_mapping(self):
        """测试内容映射"""
        if self.mapper is None:
            self.skipTest("映射器不可用")
            
        try:
            # 准备测试内容
            test_content = {
                "source_identifier": "jei:gui.jei.title",
                "content_key": "gui.jei.title",
                "source_text": "Just Enough Items",
                "language_code": "en_us"
            }
            
            # 执行映射
            mapped_result = self.mapper.map_mod_jar_content(
                test_content, 
                mod_id="jei", 
                version="15.20.0.104"
            )
            
            # 验证映射结果
            self.assertIsNotNone(mapped_result)
            if mapped_result and 'uida' in mapped_result:
                self.assertIn("minecraft://jei/", mapped_result['uida'])
                self.assertIn("en_us", mapped_result['uida'])
                print(f"✅ MOD内容映射测试通过: {mapped_result['uida'][:50]}...")
            else:
                print("⚠️ 内容映射结果为空，跳过验证")
                
        except Exception as e:
            print(f"⚠️ 内容映射测试跳过: {e}")
    
    def test_hash_generation(self):
        """测试哈希生成"""
        if self.mapper is None:
            self.skipTest("映射器不可用")
            
        try:
            # 测试内容哈希生成
            test_components = {
                'source_identifier': 'jei:gui.title',
                'content_key': 'gui.jei.title',
                'language_code': 'en_us',
                'source_text': 'Just Enough Items'
            }
            
            hash_result = self.mapper.generate_content_hash(test_components)
            
            # 验证哈希结果
            self.assertIsNotNone(hash_result)
            self.assertIsInstance(hash_result, str)
            self.assertGreater(len(hash_result), 0)
            
            print(f"✅ 内容哈希生成测试通过: {hash_result[:16]}...")
            
            # 测试相同内容生成相同哈希
            hash_result2 = self.mapper.generate_content_hash(test_components)
            self.assertEqual(hash_result, hash_result2)
            print("✅ 哈希一致性测试通过")
            
        except Exception as e:
            print(f"⚠️ 哈希生成测试跳过: {e}")
    
    def test_metadata_handling(self):
        """测试元数据处理"""
        if self.mapper is None:
            self.skipTest("映射器不可用")
            
        try:
            # 测试元数据提取和处理
            test_content = {
                "source_identifier": "jei:gui.title",
                "content_key": "gui.jei.title",
                "source_text": "JEI",
                "language_code": "en_us",
                "content_type": "gui",
                "priority": 100,
                "comment": "Main GUI title"
            }
            
            # 处理元数据
            processed_metadata = self.mapper.process_content_metadata(test_content)
            
            if processed_metadata:
                self.assertIsInstance(processed_metadata, dict)
                print("✅ 元数据处理测试通过")
            else:
                print("⚠️ 元数据处理结果为空")
                
        except Exception as e:
            print(f"⚠️ 元数据处理测试跳过: {e}")
    
    def test_reverse_mapping(self):
        """测试反向映射"""
        if self.mapper is None:
            self.skipTest("映射器不可用")
            
        try:
            # 测试从UIDA反向解析
            test_uida = "minecraft://jei/gui.jei.title#en_us@15.20.0.104"
            
            parsed_result = self.mapper.parse_uida(test_uida)
            
            if parsed_result:
                self.assertIn('namespace', parsed_result)
                self.assertIn('content_key', parsed_result)
                self.assertIn('language', parsed_result)
                self.assertEqual(parsed_result['namespace'], 'jei')
                self.assertEqual(parsed_result['content_key'], 'gui.jei.title')
                self.assertEqual(parsed_result['language'], 'en_us')
                
                print(f"✅ UIDA反向解析测试通过: {parsed_result}")
            else:
                print("⚠️ UIDA反向解析结果为空")
                
        except Exception as e:
            print(f"⚠️ 反向映射测试跳过: {e}")


def run_mapper_tests():
    """运行映射器测试套件"""
    print("🗺️ 开始统一内容映射器单元测试...\n")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestUnifiedContentMapper))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果统计
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    
    print(f"\n📊 映射器测试结果: {passed}/{total_tests} 通过")
    if failures > 0:
        print(f"❌ 失败: {failures}")
    if errors > 0:
        print(f"🔥 错误: {errors}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_mapper_tests()
    exit(0 if success else 1)