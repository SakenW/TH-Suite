"""
内存优化扫描方案研究
研究适合低配置电脑的扫描策略和现成库
"""

import sys
import os
import zipfile
import json
import time
import gc
import psutil
from pathlib import Path
from typing import Iterator, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MemoryStats:
    """内存统计"""
    rss_mb: float  # 物理内存
    vms_mb: float  # 虚拟内存
    percent: float  # 内存占用百分比


def get_memory_usage() -> MemoryStats:
    """获取当前内存使用情况"""
    process = psutil.Process()
    memory_info = process.memory_info()
    return MemoryStats(
        rss_mb=memory_info.rss / 1024**2,
        vms_mb=memory_info.vms / 1024**2,
        percent=process.memory_percent()
    )


def print_memory_stats(label: str):
    """打印内存统计"""
    stats = get_memory_usage()
    print(f"{label}: RSS={stats.rss_mb:.1f}MB, VMS={stats.vms_mb:.1f}MB, %={stats.percent:.1f}%")


class StreamingZipScanner:
    """流式ZIP扫描器 - 低内存版本"""
    
    def __init__(self, memory_limit_mb: int = 512):
        self.memory_limit_mb = memory_limit_mb
        self.processed_files = 0
        
    def scan_jar_streaming(self, jar_path: Path) -> Iterator[Dict[str, Any]]:
        """流式扫描JAR文件，逐个yield结果而不存储在内存中"""
        print_memory_stats(f"开始扫描 {jar_path.name}")
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 1. 首先检查是否为MOD
                is_mod = self._check_mod_streaming(jar)
                if not is_mod:
                    return
                
                # 2. 提取基础元数据
                mod_metadata = self._extract_metadata_streaming(jar)
                
                # 3. 流式处理语言文件
                for lang_info in self._process_language_files_streaming(jar, mod_metadata["mod_id"]):
                    yield {
                        "type": "language_file",
                        "mod_metadata": mod_metadata,
                        **lang_info
                    }
                    
                    # 内存检查和清理
                    self._check_memory_usage()
                    
        except Exception as e:
            print(f"流式扫描失败 {jar_path}: {e}")
    
    def _check_mod_streaming(self, jar: zipfile.ZipFile) -> bool:
        """流式检查是否为MOD - 只读取必要的文件名"""
        try:
            # 使用生成器避免一次性加载所有文件名
            file_names = jar.namelist()  # 这个操作相对轻量
            
            # 检查MOD标识文件
            mod_indicators = {
                'META-INF/mods.toml', 'fabric.mod.json', 
                'quilt.mod.json', 'mcmod.info', 'META-INF/neoforge.mods.toml'
            }
            
            return any(indicator in file_names for indicator in mod_indicators)
            
        except Exception:
            return False
    
    def _extract_metadata_streaming(self, jar: zipfile.ZipFile) -> Dict[str, Any]:
        """流式提取元数据 - 只读取单个文件"""
        metadata = {
            "mod_id": "unknown",
            "name": "Unknown Mod", 
            "version": "unknown",
            "authors": [],
            "description": ""
        }
        
        try:
            file_names = jar.namelist()
            
            # 优先级顺序检查元数据文件
            metadata_files = [
                ('fabric.mod.json', self._parse_fabric_streaming),
                ('quilt.mod.json', self._parse_quilt_streaming),
                ('META-INF/mods.toml', self._parse_forge_streaming),
                ('mcmod.info', self._parse_mcmod_streaming)
            ]
            
            for filename, parser in metadata_files:
                if filename in file_names:
                    try:
                        with jar.open(filename) as f:
                            # 限制读取大小，避免巨大的元数据文件
                            content = f.read(1024 * 1024)  # 最多1MB
                            parsed = parser(content)
                            metadata.update(parsed)
                            break
                    except Exception as e:
                        print(f"解析元数据失败 {filename}: {e}")
                        continue
                        
        except Exception as e:
            print(f"提取元数据失败: {e}")
            
        return metadata
    
    def _process_language_files_streaming(self, jar: zipfile.ZipFile, mod_id: str) -> Iterator[Dict[str, Any]]:
        """流式处理语言文件 - 逐个处理，不在内存中积累"""
        try:
            file_names = jar.namelist()
            
            # 找到语言文件
            lang_files = [f for f in file_names if '/lang/' in f and f.endswith('.json')]
            
            for lang_file_path in lang_files:
                try:
                    with jar.open(lang_file_path) as f:
                        # 限制读取大小
                        content = f.read(512 * 1024)  # 最多512KB per language file
                        
                        # 解析JSON
                        lang_data = json.loads(content.decode('utf-8'))
                        entries_count = len(lang_data) if isinstance(lang_data, dict) else 0
                        
                        # 只保留前5个示例键，释放大量内容
                        sample_keys = list(lang_data.keys())[:5] if isinstance(lang_data, dict) else []
                        
                        lang_code = Path(lang_file_path).stem
                        
                        yield {
                            "language": lang_code,
                            "path": lang_file_path,
                            "mod_id": mod_id,
                            "key_count": entries_count,
                            "sample_keys": sample_keys
                            # 注意：不保存完整的lang_data，节省内存
                        }
                        
                        # 手动清理
                        del lang_data
                        del content
                        
                except Exception as e:
                    print(f"处理语言文件失败 {lang_file_path}: {e}")
                    continue
                    
        except Exception as e:
            print(f"语言文件流式处理失败: {e}")
    
    def _parse_fabric_streaming(self, content: bytes) -> Dict[str, Any]:
        """流式解析Fabric元数据"""
        try:
            data = json.loads(content.decode('utf-8'))
            return {
                "mod_id": data.get("id", "unknown"),
                "name": data.get("name", "Unknown"),
                "version": data.get("version", "unknown"),
                "authors": data.get("authors", []),
                "description": data.get("description", "")
            }
        except Exception:
            return {}
    
    def _parse_quilt_streaming(self, content: bytes) -> Dict[str, Any]:
        """流式解析Quilt元数据"""
        try:
            data = json.loads(content.decode('utf-8'))
            quilt_loader = data.get("quilt_loader", {})
            return {
                "mod_id": quilt_loader.get("id", "unknown"),
                "name": quilt_loader.get("metadata", {}).get("name", "Unknown"),
                "version": quilt_loader.get("version", "unknown"),
                "authors": list(quilt_loader.get("metadata", {}).get("contributors", {}).keys()),
                "description": quilt_loader.get("metadata", {}).get("description", "")
            }
        except Exception:
            return {}
    
    def _parse_forge_streaming(self, content: bytes) -> Dict[str, Any]:
        """流式解析Forge TOML"""
        try:
            import re
            text = content.decode('utf-8')
            
            patterns = {
                "mod_id": r'modId\s*=\s*["\']([^"\']+)["\']',
                "name": r'displayName\s*=\s*["\']([^"\']+)["\']',
                "version": r'version\s*=\s*["\']([^"\']+)["\']'
            }
            
            result = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                if match:
                    result[key] = match.group(1)
            
            return result
        except Exception:
            return {}
    
    def _parse_mcmod_streaming(self, content: bytes) -> Dict[str, Any]:
        """流式解析旧版Forge元数据"""
        try:
            data = json.loads(content.decode('utf-8'))
            if isinstance(data, list) and data:
                mod_info = data[0]
                return {
                    "mod_id": mod_info.get("modid", "unknown"),
                    "name": mod_info.get("name", "Unknown"),
                    "version": mod_info.get("version", "unknown"),
                    "authors": mod_info.get("authorList", []),
                    "description": mod_info.get("description", "")
                }
        except Exception:
            return {}
    
    def _check_memory_usage(self):
        """检查内存使用并在必要时清理"""
        current_memory = get_memory_usage()
        
        if current_memory.rss_mb > self.memory_limit_mb:
            print(f"⚠️ 内存使用超限 {current_memory.rss_mb:.1f}MB > {self.memory_limit_mb}MB，执行清理")
            gc.collect()  # 强制垃圾回收
            
            # 再次检查
            after_gc = get_memory_usage()
            print(f"🧹 清理后内存: {after_gc.rss_mb:.1f}MB")


class LowMemoryBatchScanner:
    """低内存批处理扫描器"""
    
    def __init__(self, batch_size: int = 3, memory_limit_mb: int = 512):
        self.batch_size = batch_size  # 每批处理的JAR数量
        self.memory_limit_mb = memory_limit_mb
        self.streaming_scanner = StreamingZipScanner(memory_limit_mb)
    
    def scan_directory_batch(self, directory: Path) -> Iterator[Dict[str, Any]]:
        """分批扫描目录"""
        print_memory_stats("开始批处理扫描")
        
        # 发现JAR文件
        jar_files = list(directory.rglob("*.jar"))
        print(f"发现 {len(jar_files)} 个JAR文件")
        
        # 分批处理
        for i in range(0, len(jar_files), self.batch_size):
            batch = jar_files[i:i + self.batch_size]
            print(f"\n📦 处理批次 {i//self.batch_size + 1}: {len(batch)} 个文件")
            
            # 处理当前批次
            for jar_file in batch:
                for result in self.streaming_scanner.scan_jar_streaming(jar_file):
                    yield result
            
            # 批次完成后清理内存
            gc.collect()
            print_memory_stats(f"批次 {i//self.batch_size + 1} 完成")


def test_memory_usage():
    """测试内存使用情况"""
    print("🧪 内存优化测试")
    print("=" * 50)
    
    print_memory_stats("初始状态")
    
    # 创建测试目录
    test_dir = Path("/tmp")
    
    print(f"\n🔍 使用低内存扫描器测试")
    
    scanner = LowMemoryBatchScanner(batch_size=2, memory_limit_mb=256)
    
    results = []
    for result in scanner.scan_directory_batch(test_dir):
        results.append(result)
        
        if len(results) % 10 == 0:
            print_memory_stats(f"处理了 {len(results)} 个结果")
    
    print(f"\n✅ 扫描完成，共发现 {len(results)} 个语言文件")
    print_memory_stats("最终状态")


if __name__ == "__main__":
    test_memory_usage()