"""
文件完整性验证模块

实现BLAKE3哈希验证、校验和计算、文件完整性检查等功能
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, AsyncIterator, BinaryIO
import aiofiles
import blake3

from .config import SecurityConfig
from .errors import IntegrityError


class HashAlgorithm:
    """哈希算法常量"""
    BLAKE3 = "blake3"
    SHA256 = "sha256"
    SHA512 = "sha512"
    MD5 = "md5"
    CRC32 = "crc32"


class HashCalculator:
    """哈希计算器"""
    
    def __init__(self, algorithm: str = HashAlgorithm.BLAKE3):
        self.algorithm = algorithm
        self.logger = logging.getLogger(__name__)
    
    def create_hasher(self):
        """创建哈希器"""
        if self.algorithm == HashAlgorithm.BLAKE3:
            return blake3.blake3()
        elif self.algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256()
        elif self.algorithm == HashAlgorithm.SHA512:
            return hashlib.sha512()
        elif self.algorithm == HashAlgorithm.MD5:
            return hashlib.md5()
        else:
            raise IntegrityError(f"不支持的哈希算法: {self.algorithm}")
    
    async def calculate_data_hash(self, data: bytes) -> str:
        """计算数据哈希"""
        hasher = self.create_hasher()
        hasher.update(data)
        return hasher.hexdigest()
    
    async def calculate_file_hash(
        self, 
        file_path: Union[str, Path],
        chunk_size: int = 64 * 1024  # 64KB
    ) -> str:
        """计算文件哈希"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise IntegrityError(f"文件不存在: {file_path}")
        
        hasher = self.create_hasher()
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                while chunk := await f.read(chunk_size):
                    hasher.update(chunk)
            
            hash_value = hasher.hexdigest()
            self.logger.debug(
                f"计算文件哈希: {file_path}, 算法: {self.algorithm}, "
                f"哈希值: {hash_value[:16]}..."
            )
            
            return hash_value
            
        except Exception as e:
            raise IntegrityError(f"计算文件哈希失败: {e}")
    
    async def calculate_stream_hash(
        self, 
        stream: AsyncIterator[bytes]
    ) -> str:
        """计算流哈希"""
        hasher = self.create_hasher()
        
        try:
            async for chunk in stream:
                hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            raise IntegrityError(f"计算流哈希失败: {e}")
    
    async def calculate_incremental_hash(
        self, 
        initial_data: bytes,
        additional_chunks: AsyncIterator[bytes]
    ) -> str:
        """计算增量哈希"""
        hasher = self.create_hasher()
        hasher.update(initial_data)
        
        try:
            async for chunk in additional_chunks:
                hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            raise IntegrityError(f"计算增量哈希失败: {e}")


class ChecksumValidator:
    """校验和验证器"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.calculators = {
            algorithm: HashCalculator(algorithm)
            for algorithm in [
                HashAlgorithm.BLAKE3,
                HashAlgorithm.SHA256,
                HashAlgorithm.SHA512
            ]
        }
    
    async def validate_data(
        self, 
        data: bytes, 
        expected_hash: str, 
        algorithm: str = HashAlgorithm.BLAKE3
    ) -> bool:
        """验证数据完整性"""
        if algorithm not in self.calculators:
            raise IntegrityError(f"不支持的算法: {algorithm}")
        
        calculator = self.calculators[algorithm]
        actual_hash = await calculator.calculate_data_hash(data)
        
        is_valid = actual_hash.lower() == expected_hash.lower()
        
        if not is_valid:
            self.logger.warning(
                f"数据完整性验证失败: 期望 {expected_hash}, 实际 {actual_hash}"
            )
        
        return is_valid
    
    async def validate_file(
        self, 
        file_path: Union[str, Path], 
        expected_hash: str, 
        algorithm: str = HashAlgorithm.BLAKE3
    ) -> bool:
        """验证文件完整性"""
        if algorithm not in self.calculators:
            raise IntegrityError(f"不支持的算法: {algorithm}")
        
        calculator = self.calculators[algorithm]
        actual_hash = await calculator.calculate_file_hash(file_path)
        
        is_valid = actual_hash.lower() == expected_hash.lower()
        
        if not is_valid:
            self.logger.warning(
                f"文件完整性验证失败: {file_path}, "
                f"期望 {expected_hash}, 实际 {actual_hash}"
            )
        else:
            self.logger.debug(f"文件完整性验证通过: {file_path}")
        
        return is_valid
    
    async def validate_multiple_files(
        self, 
        file_hashes: Dict[Union[str, Path], str], 
        algorithm: str = HashAlgorithm.BLAKE3
    ) -> Dict[Union[str, Path], bool]:
        """批量验证文件完整性"""
        results = {}
        
        # 创建并发任务
        tasks = [
            self.validate_file(file_path, expected_hash, algorithm)
            for file_path, expected_hash in file_hashes.items()
        ]
        
        # 等待所有任务完成
        validation_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for (file_path, _), result in zip(file_hashes.items(), validation_results):
            if isinstance(result, Exception):
                self.logger.error(f"验证文件 {file_path} 时出错: {result}")
                results[file_path] = False
            else:
                results[file_path] = result
        
        # 统计结果
        total_files = len(file_hashes)
        valid_files = sum(1 for valid in results.values() if valid)
        
        self.logger.info(
            f"批量文件验证完成: {valid_files}/{total_files} 文件通过验证"
        )
        
        return results


class FileIntegrityChecker:
    """文件完整性检查器"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.validator = ChecksumValidator(config)
        self.calculator = HashCalculator(HashAlgorithm.BLAKE3)
    
    async def create_manifest(
        self, 
        directory: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None,
        algorithm: str = HashAlgorithm.BLAKE3
    ) -> Dict[str, str]:
        """创建目录完整性清单"""
        directory = Path(directory)
        
        if not directory.exists() or not directory.is_dir():
            raise IntegrityError(f"目录不存在或不是目录: {directory}")
        
        manifest = {}
        calculator = HashCalculator(algorithm)
        
        # 遍历所有文件
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                try:
                    # 计算相对路径
                    relative_path = file_path.relative_to(directory)
                    
                    # 计算文件哈希
                    file_hash = await calculator.calculate_file_hash(file_path)
                    manifest[str(relative_path)] = file_hash
                    
                except Exception as e:
                    self.logger.warning(f"计算文件哈希失败: {file_path}, {e}")
        
        self.logger.info(f"创建完整性清单: {directory}, 包含 {len(manifest)} 个文件")
        
        # 保存清单文件
        if output_file:
            await self._save_manifest(manifest, output_file)
        
        return manifest
    
    async def verify_manifest(
        self, 
        directory: Union[str, Path],
        manifest: Optional[Dict[str, str]] = None,
        manifest_file: Optional[Union[str, Path]] = None,
        algorithm: str = HashAlgorithm.BLAKE3
    ) -> Dict[str, bool]:
        """验证目录完整性清单"""
        directory = Path(directory)
        
        # 加载清单
        if manifest is None:
            if manifest_file:
                manifest = await self._load_manifest(manifest_file)
            else:
                raise IntegrityError("必须提供清单数据或清单文件")
        
        results = {}
        
        # 验证每个文件
        for relative_path, expected_hash in manifest.items():
            file_path = directory / relative_path
            
            if not file_path.exists():
                self.logger.warning(f"文件缺失: {file_path}")
                results[relative_path] = False
                continue
            
            try:
                is_valid = await self.validator.validate_file(
                    file_path, expected_hash, algorithm
                )
                results[relative_path] = is_valid
                
            except Exception as e:
                self.logger.error(f"验证文件失败: {file_path}, {e}")
                results[relative_path] = False
        
        # 检查是否有额外文件
        actual_files = set()
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(directory))
                actual_files.add(relative_path)
        
        expected_files = set(manifest.keys())
        extra_files = actual_files - expected_files
        
        if extra_files:
            self.logger.warning(f"发现额外文件: {extra_files}")
        
        # 统计结果
        total_files = len(manifest)
        valid_files = sum(1 for valid in results.values() if valid)
        
        self.logger.info(
            f"清单验证完成: {valid_files}/{total_files} 文件通过验证, "
            f"{len(extra_files)} 个额外文件"
        )
        
        return results
    
    async def _save_manifest(
        self, 
        manifest: Dict[str, str], 
        output_file: Union[str, Path]
    ) -> None:
        """保存清单文件"""
        import json
        
        output_file = Path(output_file)
        
        try:
            async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(manifest, indent=2, ensure_ascii=False))
            
            self.logger.debug(f"保存完整性清单: {output_file}")
            
        except Exception as e:
            raise IntegrityError(f"保存清单文件失败: {e}")
    
    async def _load_manifest(
        self, 
        manifest_file: Union[str, Path]
    ) -> Dict[str, str]:
        """加载清单文件"""
        import json
        
        manifest_file = Path(manifest_file)
        
        if not manifest_file.exists():
            raise IntegrityError(f"清单文件不存在: {manifest_file}")
        
        try:
            async with aiofiles.open(manifest_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                manifest = json.loads(content)
            
            self.logger.debug(f"加载完整性清单: {manifest_file}")
            return manifest
            
        except Exception as e:
            raise IntegrityError(f"加载清单文件失败: {e}")


class IntegrityVerifier:
    """完整性验证器"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.validator = ChecksumValidator(config)
        self.file_checker = FileIntegrityChecker(config)
    
    async def verify_transfer_integrity(
        self, 
        source_path: Union[str, Path],
        target_path: Union[str, Path],
        algorithm: str = HashAlgorithm.BLAKE3
    ) -> bool:
        """验证传输完整性"""
        calculator = HashCalculator(algorithm)
        
        try:
            # 计算源文件哈希
            source_hash = await calculator.calculate_file_hash(source_path)
            
            # 计算目标文件哈希
            target_hash = await calculator.calculate_file_hash(target_path)
            
            # 比较哈希值
            is_valid = source_hash.lower() == target_hash.lower()
            
            if is_valid:
                self.logger.info(f"传输完整性验证通过: {source_path} -> {target_path}")
            else:
                self.logger.error(
                    f"传输完整性验证失败: {source_path} -> {target_path}, "
                    f"源文件哈希: {source_hash}, 目标文件哈希: {target_hash}"
                )
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"传输完整性验证失败: {e}")
            return False
    
    async def verify_backup_integrity(
        self, 
        original_path: Union[str, Path],
        backup_path: Union[str, Path],
        algorithm: str = HashAlgorithm.BLAKE3
    ) -> bool:
        """验证备份完整性"""
        return await self.verify_transfer_integrity(
            original_path, backup_path, algorithm
        )
    
    async def create_integrity_report(
        self, 
        directory: Union[str, Path],
        algorithm: str = HashAlgorithm.BLAKE3
    ) -> Dict[str, any]:
        """创建完整性报告"""
        directory = Path(directory)
        
        # 创建清单
        manifest = await self.file_checker.create_manifest(directory, algorithm=algorithm)
        
        # 统计信息
        total_files = len(manifest)
        total_size = sum(
            (directory / file_path).stat().st_size 
            for file_path in manifest.keys()
            if (directory / file_path).exists()
        )
        
        report = {
            'directory': str(directory),
            'algorithm': algorithm,
            'total_files': total_files,
            'total_size': total_size,
            'manifest': manifest,
            'created_at': __import__('datetime').datetime.now().isoformat()
        }
        
        self.logger.info(
            f"创建完整性报告: {directory}, {total_files} 个文件, "
            f"总大小: {total_size / (1024*1024):.2f} MB"
        )
        
        return report
    
    async def verify_integrity_report(
        self, 
        report: Dict[str, any]
    ) -> Dict[str, bool]:
        """验证完整性报告"""
        directory = Path(report['directory'])
        manifest = report['manifest']
        algorithm = report['algorithm']
        
        return await self.file_checker.verify_manifest(
            directory, manifest=manifest, algorithm=algorithm
        )