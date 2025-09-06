#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整的MOD扫描器
包括语言文件和翻译条目的提取
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
import uuid

# 尝试导入toml库
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # fallback
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)

class FullModScanner:
    """完整的MOD扫描器，包含语言文件提取"""
    
    def __init__(self, db_path: str = "mc_l10n.db"):
        self.db_path = db_path
        self.scan_id = None
        
    def start_scan_session(self, target_path: str) -> str:
        """创建扫描会话"""
        self.scan_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO scan_sessions (
                    scan_id, status, target_path, game_type, scan_mode, 
                    started_at, progress_percent, total_files, processed_files
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.scan_id, 'scanning', target_path, 'minecraft', 'full',
                datetime.now().isoformat(), 0.0, 0, 0
            ))
            conn.commit()
            logger.info(f"创建扫描会话: {self.scan_id}")
        except Exception as e:
            logger.error(f"创建扫描会话失败: {e}")
        finally:
            conn.close()
        
        return self.scan_id
    
    def complete_scan_session(self, stats: Dict[str, int]):
        """完成扫描会话"""
        if not self.scan_id:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE scan_sessions 
                SET status = 'completed',
                    completed_at = ?,
                    progress_percent = 100,
                    statistics = ?
                WHERE scan_id = ?
            """, (
                datetime.now().isoformat(),
                json.dumps(stats),
                self.scan_id
            ))
            conn.commit()
            logger.info(f"完成扫描会话: {self.scan_id}")
        except Exception as e:
            logger.error(f"更新扫描会话失败: {e}")
        finally:
            conn.close()
    
    def scan_directory(self, directory: str) -> Dict[str, Any]:
        """完整扫描目录中的所有MOD"""
        target_dir = Path(directory)
        if not target_dir.exists():
            raise ValueError(f"目录不存在: {directory}")
        
        # 创建扫描会话
        self.start_scan_session(directory)
        
        results = {
            "scan_id": self.scan_id,
            "total_mods": 0,
            "successful": 0,
            "failed": 0,
            "total_language_files": 0,
            "total_translation_entries": 0,
            "mods": []
        }
        
        # 查找所有JAR文件
        jar_files = list(target_dir.glob("**/*.jar"))
        results["total_mods"] = len(jar_files)
        
        for i, jar_path in enumerate(jar_files, 1):
            try:
                logger.info(f"扫描 {i}/{len(jar_files)}: {jar_path.name}")
                
                # 提取MOD信息
                mod_info = self.extract_mod_info(jar_path)
                if mod_info:
                    # 提取语言文件
                    language_files = self.extract_language_files(jar_path, mod_info['mod_id'])
                    mod_info['language_files'] = language_files
                    
                    results["mods"].append(mod_info)
                    results["successful"] += 1
                    results["total_language_files"] += len(language_files)
                    
                    # 统计翻译条目
                    for lang_file in language_files:
                        results["total_translation_entries"] += lang_file.get('translation_count', 0)
                else:
                    results["failed"] += 1
                    logger.warning(f"无法提取MOD信息: {jar_path}")
                    
                # 更新进度
                self.update_scan_progress(i, len(jar_files))
                
            except Exception as e:
                results["failed"] += 1
                logger.error(f"处理MOD失败 {jar_path}: {e}")
        
        # 完成扫描会话
        self.complete_scan_session({
            "total_mods": results["total_mods"],
            "successful": results["successful"],
            "failed": results["failed"],
            "total_language_files": results["total_language_files"],
            "total_translation_entries": results["total_translation_entries"]
        })
        
        return results
    
    def update_scan_progress(self, current: int, total: int):
        """更新扫描进度"""
        if not self.scan_id:
            return
        
        progress = (current / total) * 100 if total > 0 else 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE scan_sessions 
                SET progress_percent = ?,
                    processed_files = ?,
                    total_files = ?
                WHERE scan_id = ?
            """, (progress, current, total, self.scan_id))
            conn.commit()
        except Exception as e:
            logger.error(f"更新进度失败: {e}")
        finally:
            conn.close()
    
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
                    
                else:
                    # 没有找到元数据文件，使用文件名推断
                    return self._infer_from_filename(jar_path)
                    
        except Exception as e:
            logger.error(f"解析JAR文件失败 {jar_path}: {e}")
            return None
    
    def extract_language_files(self, jar_path: Path, mod_id: str) -> List[Dict[str, Any]]:
        """从JAR文件提取语言文件"""
        language_files = []
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 查找语言文件
                # 常见路径模式：
                # - assets/modid/lang/*.json (1.13+)
                # - assets/modid/lang/*.lang (1.12-)
                
                for file_path in jar.namelist():
                    if self._is_language_file(file_path):
                        try:
                            content = jar.read(file_path)
                            lang_code = self._extract_language_code(file_path)
                            
                            # 解析语言文件内容
                            translations = self._parse_language_file(content, file_path)
                            
                            if translations:
                                lang_file = {
                                    'mod_id': mod_id,
                                    'language_code': lang_code,
                                    'file_path': file_path,
                                    'translation_count': len(translations),
                                    'translations': translations
                                }
                                language_files.append(lang_file)
                                logger.debug(f"找到语言文件: {file_path} ({len(translations)} 条翻译)")
                                
                        except Exception as e:
                            logger.warning(f"解析语言文件失败 {file_path}: {e}")
                
        except Exception as e:
            logger.error(f"提取语言文件失败 {jar_path}: {e}")
        
        return language_files
    
    def _is_language_file(self, file_path: str) -> bool:
        """判断是否是语言文件"""
        # 匹配语言文件路径
        return (
            '/lang/' in file_path and 
            (file_path.endswith('.json') or file_path.endswith('.lang'))
        )
    
    def _extract_language_code(self, file_path: str) -> str:
        """从文件路径提取语言代码"""
        # 提取文件名（不含扩展名）
        filename = Path(file_path).stem
        # 常见语言代码
        if filename in ['en_us', 'zh_cn', 'zh_tw', 'ja_jp', 'ko_kr', 'fr_fr', 'de_de', 'es_es', 'ru_ru']:
            return filename
        return filename
    
    def _parse_language_file(self, content: bytes, file_path: str) -> Dict[str, str]:
        """解析语言文件内容"""
        translations = {}
        
        try:
            if file_path.endswith('.json'):
                # JSON格式 (1.13+)
                data = json.loads(content.decode('utf-8', errors='ignore'))
                if isinstance(data, dict):
                    translations = data
                    
            elif file_path.endswith('.lang'):
                # Properties格式 (1.12-)
                lines = content.decode('utf-8', errors='ignore').split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        translations[key.strip()] = value.strip()
                        
        except Exception as e:
            logger.warning(f"解析语言文件内容失败 {file_path}: {e}")
        
        return translations
    
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
            text = content.decode('utf-8', errors='ignore')
            
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
            
        except Exception as e:
            logger.error(f"解析mods.toml失败 {jar_path}: {e}")
        
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
    
    def _infer_from_filename(self, jar_path: Path) -> Dict[str, Any]:
        """从文件名推断MOD信息"""
        filename = jar_path.stem
        
        mod_info = {
            'mod_id': filename.split('-')[0] if '-' in filename else filename,
            'name': filename.split('-')[0] if '-' in filename else filename,
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
        version_range = version_range.strip('[]()').split(',')[0]
        return version_range.strip()
    
    def _calculate_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return hashlib.md5(str(file_path).encode()).hexdigest()
    
    def save_to_database(self, mods: List[Dict[str, Any]], db_path: Optional[str] = None) -> Dict[str, int]:
        """保存完整的MOD数据到数据库"""
        if not db_path:
            db_path = self.db_path
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        stats = {
            'mods_saved': 0,
            'language_files_saved': 0,
            'translation_entries_saved': 0
        }
        
        try:
            for mod in mods:
                # 保存MOD信息
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
                stats['mods_saved'] += 1
                
                # 保存语言文件
                for lang_file in mod.get('language_files', []):
                    cursor.execute("""
                        INSERT INTO language_files (
                            mod_id, language_code, file_path, content, translation_count,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        mod.get('mod_id'),
                        lang_file.get('language_code'),
                        lang_file.get('file_path'),
                        json.dumps(lang_file.get('translations', {})),
                        lang_file.get('translation_count', 0),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    
                    # 获取语言文件ID
                    language_file_id = cursor.lastrowid
                    stats['language_files_saved'] += 1
                    
                    # 保存翻译条目
                    for key, value in lang_file.get('translations', {}).items():
                        cursor.execute("""
                            INSERT INTO translation_entries (
                                mod_id, language_file_id, translation_key, original_text,
                                translated_text, status, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            mod.get('mod_id'),
                            language_file_id,
                            key,
                            value if lang_file.get('language_code') == 'en_us' else '',
                            value if lang_file.get('language_code') != 'en_us' else '',
                            'translated' if lang_file.get('language_code') != 'en_us' else 'original',
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))
                        stats['translation_entries_saved'] += 1
            
            conn.commit()
            logger.info(f"保存成功 - MODs: {stats['mods_saved']}, 语言文件: {stats['language_files_saved']}, 翻译条目: {stats['translation_entries_saved']}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"保存到数据库失败: {e}")
            raise
        finally:
            conn.close()
        
        return stats


def main():
    """测试完整扫描器"""
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("用法: python full_scanner.py <mod目录路径>")
        sys.exit(1)
    
    mod_dir = sys.argv[1]
    db_path = "mc_l10n.db"
    
    print(f"\n{'='*60}")
    print(f"  完整MOD扫描器")
    print(f"{'='*60}")
    print(f"目标目录: {mod_dir}")
    print(f"数据库: {db_path}")
    print(f"{'='*60}\n")
    
    scanner = FullModScanner(db_path)
    results = scanner.scan_directory(mod_dir)
    
    print(f"\n扫描结果:")
    print(f"  扫描ID: {results['scan_id']}")
    print(f"  MOD总数: {results['total_mods']}")
    print(f"  成功: {results['successful']}")
    print(f"  失败: {results['failed']}")
    print(f"  语言文件: {results['total_language_files']}")
    print(f"  翻译条目: {results['total_translation_entries']}")
    
    if results['mods']:
        print(f"\n保存到数据库...")
        stats = scanner.save_to_database(results['mods'], db_path)
        print(f"  已保存MOD: {stats['mods_saved']}")
        print(f"  已保存语言文件: {stats['language_files_saved']}")
        print(f"  已保存翻译条目: {stats['translation_entries_saved']}")
        
        # 显示示例
        print(f"\n前3个MOD的语言文件信息:")
        for i, mod in enumerate(results['mods'][:3], 1):
            lang_files = mod.get('language_files', [])
            print(f"\n  {i}. {mod['name']} ({mod['mod_id']})")
            print(f"     语言文件数: {len(lang_files)}")
            if lang_files:
                for lang in lang_files[:3]:
                    print(f"       - {lang['language_code']}: {lang['translation_count']} 条翻译")


if __name__ == '__main__':
    main()