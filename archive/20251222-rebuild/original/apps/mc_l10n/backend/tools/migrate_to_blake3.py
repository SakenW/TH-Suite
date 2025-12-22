#!/usr/bin/env python
"""
迁移工具：将现有系统从MD5/SHA256哈希升级到BLAKE3
自动替换磁盘缓存和其他哈希使用
"""

import sys
import os
import re
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

sys.path.append('.')

import structlog
from services.content_addressing import (
    ContentAddressingSystem, 
    HashAlgorithm, 
    compute_cid,
    benchmark_hash_algorithms
)
from services.blake3_disk_cache import Blake3DiskCache

logger = structlog.get_logger(__name__)

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)


class Blake3MigrationTool:
    """BLAKE3迁移工具"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.migration_log = []
        
        # 需要更新的文件模式
        self.file_patterns = [
            "**/*.py",  # Python文件
            "**/*.sql", # SQL文件（如果有哈希相关）
        ]
        
        # 需要替换的哈希模式
        self.hash_patterns = {
            # hashlib.md5 -> blake3
            r'hashlib\.md5\(\)': 'blake3.blake3()',
            r'hashlib\.md5\(([^)]+)\)': r'blake3.blake3(\1)',
            
            # hashlib.sha256 -> blake3 (在内容寻址场景)
            r'hashlib\.sha256\(\)\.hexdigest\(\)': 'blake3.blake3().hexdigest()',
            r'hashlib\.sha256\(([^)]+)\)\.hexdigest\(\)': r'blake3.blake3(\1).hexdigest()',
            
            # 导入语句
            r'import hashlib': 'import blake3\nimport hashlib  # 保留用于兼容性',
        }
        
        logger.info("BLAKE3迁移工具初始化", project_root=str(self.project_root))
    
    def analyze_current_usage(self) -> Dict[str, Any]:
        """分析当前的哈希使用情况"""
        logger.info("开始分析当前哈希使用情况")
        
        analysis = {
            "files_with_hash": [],
            "hash_usage_count": {
                "md5": 0,
                "sha256": 0,
                "other": 0
            },
            "potential_replacements": []
        }
        
        for pattern in self.file_patterns:
            for file_path in self.project_root.glob(pattern):
                if self._should_skip_file(file_path):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 检查哈希使用
                    hash_matches = self._find_hash_usage(content)
                    if hash_matches:
                        analysis["files_with_hash"].append({
                            "file": str(file_path),
                            "matches": hash_matches
                        })
                        
                        # 统计使用次数
                        for match_type, matches in hash_matches.items():
                            analysis["hash_usage_count"][match_type] += len(matches)
                    
                except Exception as e:
                    logger.warning("文件分析失败", file_path=str(file_path), error=str(e))
        
        logger.info("哈希使用情况分析完成", 
                   files_found=len(analysis["files_with_hash"]),
                   total_md5=analysis["hash_usage_count"]["md5"],
                   total_sha256=analysis["hash_usage_count"]["sha256"])
        
        return analysis
    
    def _find_hash_usage(self, content: str) -> Dict[str, List[str]]:
        """查找内容中的哈希使用"""
        matches = {
            "md5": [],
            "sha256": [],
            "other": []
        }
        
        # MD5模式
        md5_patterns = [
            r'hashlib\.md5\([^)]*\)',
            r'\.md5\(\)',
            r'md5\s*=',
            r'MD5\s*=',
        ]
        
        # SHA256模式
        sha256_patterns = [
            r'hashlib\.sha256\([^)]*\)',
            r'\.sha256\(\)',
            r'sha256\s*=',
            r'SHA256\s*=',
        ]
        
        for pattern in md5_patterns:
            found = re.findall(pattern, content, re.IGNORECASE)
            matches["md5"].extend(found)
        
        for pattern in sha256_patterns:
            found = re.findall(pattern, content, re.IGNORECASE)
            matches["sha256"].extend(found)
        
        return {k: v for k, v in matches.items() if v}
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        skip_patterns = [
            "__pycache__",
            ".git",
            ".pytest_cache",
            "node_modules",
            "venv",
            ".venv",
            "migrations",  # 数据库迁移文件通常不需要修改
            "test_blake3_content_addressing.py",  # 我们刚创建的测试文件
            "migrate_to_blake3.py",  # 本文件
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)
    
    def perform_migration(self, dry_run: bool = True) -> Dict[str, Any]:
        """执行BLAKE3迁移"""
        logger.info("开始执行BLAKE3迁移", dry_run=dry_run)
        
        migration_results = {
            "modified_files": [],
            "total_replacements": 0,
            "errors": []
        }
        
        for pattern in self.file_patterns:
            for file_path in self.project_root.glob(pattern):
                if self._should_skip_file(file_path):
                    continue
                
                try:
                    result = self._migrate_file(file_path, dry_run)
                    if result["replacements"] > 0:
                        migration_results["modified_files"].append(result)
                        migration_results["total_replacements"] += result["replacements"]
                    
                except Exception as e:
                    error_info = {
                        "file": str(file_path),
                        "error": str(e)
                    }
                    migration_results["errors"].append(error_info)
                    logger.error("文件迁移失败", **error_info)
        
        logger.info("BLAKE3迁移完成",
                   modified_files=len(migration_results["modified_files"]),
                   total_replacements=migration_results["total_replacements"],
                   errors=len(migration_results["errors"]),
                   dry_run=dry_run)
        
        return migration_results
    
    def _migrate_file(self, file_path: Path, dry_run: bool = True) -> Dict[str, Any]:
        """迁移单个文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        modified_content = original_content
        replacements = 0
        
        # 应用所有替换模式
        for old_pattern, new_pattern in self.hash_patterns.items():
            new_content, count = re.subn(old_pattern, new_pattern, modified_content)
            if count > 0:
                modified_content = new_content
                replacements += count
                logger.debug("应用替换模式",
                           file=str(file_path),
                           pattern=old_pattern,
                           replacements=count)
        
        # 如果有修改且不是干运行，写入文件
        if replacements > 0 and not dry_run:
            # 备份原文件
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            if not backup_path.exists():
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            
            # 写入修改后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            logger.info("文件已迁移", 
                       file=str(file_path),
                       replacements=replacements,
                       backup=str(backup_path))
        
        return {
            "file": str(file_path),
            "replacements": replacements,
            "backup": str(backup_path) if replacements > 0 and not dry_run else None
        }
    
    def benchmark_performance(self) -> Dict[str, float]:
        """基准测试：比较迁移前后的性能"""
        logger.info("开始性能基准测试")
        
        # 测试不同大小的数据
        test_cases = [
            (b"small content", "小数据"),
            (b"x" * 1024, "1KB数据"),
            (b"x" * 10240, "10KB数据"),
            (b"x" * 102400, "100KB数据"),
        ]
        
        results = {}
        
        for data, description in test_cases:
            logger.info(f"测试 {description}")
            benchmark_result = benchmark_hash_algorithms(data, iterations=1000)
            results[description] = benchmark_result
            
            # 显示结果
            blake3_time = benchmark_result.get("blake3", 0)
            md5_time = benchmark_result.get("md5", 0)
            sha256_time = benchmark_result.get("sha256", 0)
            
            if md5_time > 0:
                md5_improvement = md5_time / blake3_time
                logger.info(f"{description} - BLAKE3比MD5快 {md5_improvement:.2f}倍")
            
            if sha256_time > 0:
                sha256_improvement = sha256_time / blake3_time
                logger.info(f"{description} - BLAKE3比SHA256快 {sha256_improvement:.2f}倍")
        
        return results
    
    def create_migration_report(self, analysis: Dict[str, Any], migration_results: Dict[str, Any]) -> str:
        """创建迁移报告"""
        report = [
            "# BLAKE3迁移报告",
            f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 迁移前分析",
            f"- 发现包含哈希的文件: {len(analysis['files_with_hash'])} 个",
            f"- MD5使用次数: {analysis['hash_usage_count']['md5']}",
            f"- SHA256使用次数: {analysis['hash_usage_count']['sha256']}",
            "",
            "## 迁移结果",
            f"- 修改的文件: {len(migration_results['modified_files'])} 个",
            f"- 总替换次数: {migration_results['total_replacements']}",
            f"- 发生错误: {len(migration_results['errors'])} 个",
            "",
        ]
        
        if migration_results['modified_files']:
            report.append("## 修改的文件")
            for file_info in migration_results['modified_files']:
                report.append(f"- {file_info['file']}: {file_info['replacements']} 次替换")
            report.append("")
        
        if migration_results['errors']:
            report.append("## 错误信息")
            for error_info in migration_results['errors']:
                report.append(f"- {error_info['file']}: {error_info['error']}")
            report.append("")
        
        report.extend([
            "## BLAKE3优势",
            "1. **性能**: 在大多数场景下比MD5和SHA256更快",
            "2. **安全性**: 密码学安全，抗碰撞攻击",
            "3. **并行化**: 支持SIMD和多线程优化",
            "4. **一致性**: 无长度扩展攻击",
            "",
            "## 注意事项",
            "1. 确保所有依赖的系统都支持BLAKE3",
            "2. 如果需要与外部系统兼容，可能需要保留原有哈希算法",
            "3. 数据库中存储的哈希值需要重新计算",
            "4. 缓存文件可能需要清理重建",
        ])
        
        return "\\n".join(report)
    
    def verify_migration(self) -> bool:
        """验证迁移结果"""
        logger.info("开始验证迁移结果")
        
        try:
            # 测试BLAKE3功能
            cas = ContentAddressingSystem(HashAlgorithm.BLAKE3)
            test_content = "迁移验证测试内容"
            cid = cas.compute_cid(test_content)
            
            if cid.algorithm == HashAlgorithm.BLAKE3:
                logger.info("✓ BLAKE3内容寻址系统工作正常")
            else:
                logger.error("✗ BLAKE3内容寻址系统异常")
                return False
            
            # 测试BLAKE3缓存
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                cache = Blake3DiskCache(cache_dir=temp_dir, max_size_mb=1)
                
                # 这里需要等待初始化完成
                import asyncio
                async def test_cache():
                    await cache.initialize()
                    success = await cache.put("test_key", {"test": "data"})
                    if success:
                        data = await cache.get("test_key")
                        if data and data.get("test") == "data":
                            logger.info("✓ BLAKE3磁盘缓存工作正常")
                            await cache.shutdown()
                            return True
                    await cache.shutdown()
                    return False
                
                if asyncio.run(test_cache()):
                    logger.info("迁移验证完成: 所有BLAKE3功能正常")
                    return True
                else:
                    logger.error("迁移验证失败: BLAKE3磁盘缓存异常")
                    return False
        
        except Exception as e:
            logger.error("迁移验证异常", error=str(e))
            return False


def main():
    """主函数"""
    print("🚀 BLAKE3迁移工具")
    print("=" * 50)
    
    # 创建迁移工具
    migration_tool = Blake3MigrationTool()
    
    # 步骤1: 分析当前使用情况
    print("📊 分析当前哈希使用情况...")
    analysis = migration_tool.analyze_current_usage()
    
    # 步骤2: 性能基准测试
    print("⚡ 执行性能基准测试...")
    benchmark_results = migration_tool.benchmark_performance()
    
    # 步骤3: 干运行迁移（预览）
    print("🔍 执行迁移预览（干运行）...")
    dry_run_results = migration_tool.perform_migration(dry_run=True)
    
    # 步骤4: 生成报告
    report = migration_tool.create_migration_report(analysis, dry_run_results)
    
    # 保存报告
    report_path = Path("blake3_migration_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📄 迁移报告已生成: {report_path}")
    print("\\n" + "=" * 50)
    print("迁移预览完成!")
    print(f"发现 {len(analysis['files_with_hash'])} 个包含哈希的文件")
    print(f"预计修改 {len(dry_run_results['modified_files'])} 个文件")
    print(f"总共 {dry_run_results['total_replacements']} 次替换")
    
    if dry_run_results['errors']:
        print(f"⚠️  发现 {len(dry_run_results['errors'])} 个潜在问题")
    
    print("\\n要执行实际迁移，请运行:")
    print("python tools/migrate_to_blake3.py --execute")
    
    return 0


if __name__ == "__main__":
    import sys
    if "--execute" in sys.argv:
        print("⚠️  执行实际迁移功能暂未实现")
        print("请手动检查迁移报告后谨慎执行")
    else:
        exit(main())