#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复版的MOD扫描器
正确处理TOML解析和变量替换
"""

import sqlite3
import json
import zipfile
import hashlib
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# 尝试导入toml库
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # fallback
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)

class FixedModScanner:
    """修复版的MOD扫描器"""
    
    def __init__(self, db_path: str = "mc_l10n.db"):
        self.db_path = db_path
        
    def scan_directory(self, directory: str) -> Dict[str, Any]:
        """扫描目录中的所有MOD"""
        target_dir = Path(directory)
        if not target_dir.exists():
            raise ValueError(f"目录不存在: {directory}")
        
        results = {
            "total_mods": 0,
            "successful": 0,
            "failed": 0,
            "mods": []
        }
        
        # 查找所有JAR文件
        jar_files = list(target_dir.glob("**/*.jar"))
        results["total_mods"] = len(jar_files)
        
        for jar_path in jar_files:
            try:
                mod_info = self.extract_mod_info(jar_path)
                if mod_info:
                    results["mods"].append(mod_info)
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    logger.warning(f"无法提取MOD信息: {jar_path}")
            except Exception as e:
                results["failed"] += 1
                logger.error(f"处理MOD失败 {jar_path}: {e}")
        
        return results
    
    def extract_mod_info(self, jar_path: Path) -> Optional[Dict[str, Any]]:
        """从JAR文件提取MOD信息"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 检查不同类型的元数据文件
                if 'META-INF/mods.toml' in file_list:
                    # Forge 1.13+
                    content = jar.read('META-INF/mods.toml')
                    return self._parse_forge_toml(content, jar_path)
                    
                elif 'fabric.mod.json' in file_list:
                    # Fabric
                    content = jar.read('fabric.mod.json')
                    return self._parse_fabric_json(content, jar_path)
                    
                elif 'mcmod.info' in file_list:
                    # Forge 1.12及更早
                    content = jar.read('mcmod.info')
                    return self._parse_mcmod_info(content, jar_path)
                    
                elif 'quilt.mod.json' in file_list:
                    # Quilt
                    content = jar.read('quilt.mod.json')
                    return self._parse_quilt_json(content, jar_path)
                    
                else:
                    # 没有找到元数据文件，使用文件名推断
                    return self._infer_from_filename(jar_path)
                    
        except Exception as e:
            logger.error(f"解析JAR文件失败 {jar_path}: {e}")
            return None
    
    def _parse_forge_toml(self, content: bytes, jar_path: Path) -> Dict[str, Any]:
        """解析Forge的mods.toml文件"""
        mod_info = {
            'file_path': str(jar_path),
            'file_hash': self._calculate_hash(jar_path),
            'mod_loader': 'forge',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            # 解析TOML内容
            text = content.decode('utf-8', errors='ignore')
            
            # 如果有tomllib，使用它
            if tomllib:
                # 先清理内容：移除注释和变量
                cleaned_text = self._clean_toml_content(text)
                try:
                    data = tomllib.loads(cleaned_text)
                    
                    # 提取MOD信息
                    if 'mods' in data and len(data['mods']) > 0:
                        mod = data['mods'][0]  # 通常只有一个mod
                        mod_info['mod_id'] = mod.get('modId', jar_path.stem)
                        mod_info['name'] = mod.get('displayName', mod.get('modId', jar_path.stem))
                        mod_info['display_name'] = mod.get('displayName', '')
                        mod_info['version'] = mod.get('version', '${file.jarVersion}')
                        
                        # 处理版本变量
                        if '${' in mod_info['version']:
                            # 尝试从文件名提取版本
                            mod_info['version'] = self._extract_version_from_filename(jar_path)
                    
                    # 提取依赖信息中的MC版本
                    if 'dependencies' in data:
                        for dep_key, deps in data['dependencies'].items():
                            if isinstance(deps, list):
                                for dep in deps:
                                    if isinstance(dep, dict) and dep.get('modId') == 'minecraft':
                                        version_range = dep.get('versionRange', '')
                                        mod_info['minecraft_version'] = self._parse_version_range(version_range)
                                        break
                                        
                except Exception as e:
                    logger.warning(f"tomllib解析失败，使用简单解析: {e}")
                    return self._simple_toml_parse(text, mod_info, jar_path)
            else:
                # 没有tomllib，使用简单解析
                return self._simple_toml_parse(text, mod_info, jar_path)
                
        except Exception as e:
            logger.error(f"解析mods.toml失败 {jar_path}: {e}")
            mod_info.update({
                'mod_id': jar_path.stem,
                'name': jar_path.stem,
                'version': 'unknown'
            })
        
        return mod_info
    
    def _clean_toml_content(self, text: str) -> str:
        """清理TOML内容，移除注释和处理变量"""
        lines = []
        for line in text.split('\n'):
            # 移除行内注释
            if '#' in line:
                # 但要保留引号内的#
                in_quotes = False
                cleaned_line = []
                for i, char in enumerate(line):
                    if char in '"\'':
                        in_quotes = not in_quotes
                    if char == '#' and not in_quotes:
                        break
                    cleaned_line.append(char)
                line = ''.join(cleaned_line)
            
            # 处理变量替换
            if '${file.jarVersion}' in line:
                line = line.replace('${file.jarVersion}', 'unknown')
            
            lines.append(line.strip())
        
        return '\n'.join(lines)
    
    def _simple_toml_parse(self, text: str, mod_info: Dict, jar_path: Path) -> Dict[str, Any]:
        """简单的TOML解析（后备方案）"""
        # 使用正则表达式提取关键字段
        patterns = {
            'modId': r'modId\s*=\s*["\']([^"\']+)["\']',
            'displayName': r'displayName\s*=\s*["\']([^"\']+)["\']',
            'version': r'version\s*=\s*["\']([^"\']+)["\']',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                value = match.group(1)
                if key == 'modId':
                    mod_info['mod_id'] = value
                elif key == 'displayName':
                    mod_info['name'] = value
                    mod_info['display_name'] = value
                elif key == 'version':
                    if '${' not in value:
                        mod_info['version'] = value
                    else:
                        mod_info['version'] = self._extract_version_from_filename(jar_path)
        
        # 提取MC版本
        mc_version_pattern = r'minecraft.*versionRange\s*=\s*["\']([^"\']+)["\']'
        match = re.search(mc_version_pattern, text)
        if match:
            mod_info['minecraft_version'] = self._parse_version_range(match.group(1))
        
        # 确保有基本信息
        if 'mod_id' not in mod_info:
            mod_info['mod_id'] = jar_path.stem
        if 'name' not in mod_info:
            mod_info['name'] = mod_info.get('mod_id', jar_path.stem)
        if 'version' not in mod_info:
            mod_info['version'] = self._extract_version_from_filename(jar_path)
        
        return mod_info
    
    def _parse_fabric_json(self, content: bytes, jar_path: Path) -> Dict[str, Any]:
        """解析Fabric的fabric.mod.json文件"""
        mod_info = {
            'file_path': str(jar_path),
            'file_hash': self._calculate_hash(jar_path),
            'mod_loader': 'fabric',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            data = json.loads(content.decode('utf-8', errors='ignore'))
            mod_info['mod_id'] = data.get('id', jar_path.stem)
            mod_info['name'] = data.get('name', mod_info['mod_id'])
            mod_info['display_name'] = data.get('name', '')
            mod_info['version'] = data.get('version', 'unknown')
            
            # 提取MC版本
            if 'depends' in data:
                mc_version = data['depends'].get('minecraft', '')
                if mc_version:
                    mod_info['minecraft_version'] = self._parse_version_range(mc_version)
                    
        except Exception as e:
            logger.error(f"解析fabric.mod.json失败 {jar_path}: {e}")
            mod_info.update({
                'mod_id': jar_path.stem,
                'name': jar_path.stem,
                'version': 'unknown'
            })
        
        return mod_info
    
    def _parse_mcmod_info(self, content: bytes, jar_path: Path) -> Dict[str, Any]:
        """解析旧版Forge的mcmod.info文件"""
        mod_info = {
            'file_path': str(jar_path),
            'file_hash': self._calculate_hash(jar_path),
            'mod_loader': 'forge',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            data = json.loads(content.decode('utf-8', errors='ignore'))
            if isinstance(data, list) and len(data) > 0:
                mod = data[0]
            elif isinstance(data, dict):
                mod = data
            else:
                raise ValueError("未知的mcmod.info格式")
            
            mod_info['mod_id'] = mod.get('modid', jar_path.stem)
            mod_info['name'] = mod.get('name', mod_info['mod_id'])
            mod_info['display_name'] = mod.get('name', '')
            mod_info['version'] = mod.get('version', 'unknown')
            mod_info['minecraft_version'] = mod.get('mcversion', '')
            
        except Exception as e:
            logger.error(f"解析mcmod.info失败 {jar_path}: {e}")
            mod_info.update({
                'mod_id': jar_path.stem,
                'name': jar_path.stem,
                'version': 'unknown'
            })
        
        return mod_info
    
    def _parse_quilt_json(self, content: bytes, jar_path: Path) -> Dict[str, Any]:
        """解析Quilt的quilt.mod.json文件"""
        # 类似Fabric的处理
        return self._parse_fabric_json(content, jar_path)
    
    def _infer_from_filename(self, jar_path: Path) -> Dict[str, Any]:
        """从文件名推断MOD信息"""
        filename = jar_path.stem
        
        # 尝试从文件名提取信息
        # 常见格式: modname-version 或 modname_version
        parts = re.split(r'[-_]', filename)
        
        mod_info = {
            'mod_id': parts[0] if parts else filename,
            'name': parts[0] if parts else filename,
            'version': self._extract_version_from_filename(jar_path),
            'file_path': str(jar_path),
            'file_hash': self._calculate_hash(jar_path),
            'mod_loader': 'unknown',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        return mod_info
    
    def _extract_version_from_filename(self, jar_path: Path) -> str:
        """从文件名提取版本号"""
        filename = jar_path.stem
        
        # 匹配常见版本号模式
        version_patterns = [
            r'[-_]([0-9]+\.[0-9]+\.[0-9]+)',  # 1.2.3
            r'[-_]([0-9]+\.[0-9]+)',           # 1.2
            r'[-_]v([0-9]+\.[0-9]+\.[0-9]+)',  # v1.2.3
            r'[-_]([0-9]+\.[0-9]+\.[0-9]+-[0-9]+)',  # 1.2.3-45
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        
        return 'unknown'
    
    def _parse_version_range(self, version_range: str) -> str:
        """解析版本范围字符串"""
        # 移除版本范围符号，只保留版本号
        # 例如: "[1.18.2,1.19)" -> "1.18.2"
        version_range = version_range.strip('[]()').split(',')[0]
        return version_range.strip()
    
    def _calculate_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return hashlib.md5(str(file_path).encode()).hexdigest()
    
    def save_to_database(self, mods: List[Dict[str, Any]], db_path: Optional[str] = None) -> int:
        """保存MOD信息到数据库"""
        if not db_path:
            db_path = self.db_path
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        try:
            for mod in mods:
                cursor.execute("""
                    INSERT OR REPLACE INTO mods (
                        mod_id, name, display_name, version, minecraft_version,
                        mod_loader, file_path, file_hash, metadata, scan_result,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mod.get('mod_id'),
                    mod.get('name'),
                    mod.get('display_name'),
                    mod.get('version'),
                    mod.get('minecraft_version'),
                    mod.get('mod_loader'),
                    mod.get('file_path'),
                    mod.get('file_hash'),
                    json.dumps(mod.get('metadata', {})),
                    json.dumps(mod.get('scan_result', {})),
                    mod.get('created_at'),
                    mod.get('updated_at')
                ))
                saved_count += 1
            
            conn.commit()
            logger.info(f"成功保存 {saved_count} 个MOD记录")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存到数据库失败: {e}")
            raise
        finally:
            conn.close()
        
        return saved_count


def main():
    """测试扫描器"""
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("用法: python fixed_scanner.py <mod目录路径>")
        sys.exit(1)
    
    mod_dir = sys.argv[1]
    db_path = "mc_l10n.db"  # 使用主数据库文件
    
    print(f"开始扫描目录: {mod_dir}")
    print(f"数据库: {db_path}")
    
    scanner = FixedModScanner(db_path)
    results = scanner.scan_directory(mod_dir)
    
    print(f"\n扫描结果:")
    print(f"  总计: {results['total_mods']} 个MOD")
    print(f"  成功: {results['successful']} 个")
    print(f"  失败: {results['failed']} 个")
    
    if results['mods']:
        print(f"\n保存到数据库...")
        saved = scanner.save_to_database(results['mods'], db_path)
        print(f"  已保存: {saved} 条记录")
        
        # 显示前5个MOD的信息
        print(f"\n前5个MOD信息:")
        for i, mod in enumerate(results['mods'][:5], 1):
            print(f"\n  {i}. {mod['name']}")
            print(f"     mod_id: {mod['mod_id']}")
            print(f"     version: {mod['version']}")
            print(f"     mc_version: {mod.get('minecraft_version', 'N/A')}")
            print(f"     loader: {mod['mod_loader']}")


if __name__ == '__main__':
    main()