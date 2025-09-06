"""
扫描应用服务
处理模组扫描相关的用例
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ...domain.models.mod import Mod, ModId, ModMetadata, ModVersion
from ...domain.repositories import ModRepository, ScanResultRepository
from ...domain.events import ModScannedEvent
from ..commands import ScanCommand, RescanCommand
from ..dto import ScanResultDTO, ModDTO

logger = logging.getLogger(__name__)


class ScanService:
    """扫描应用服务"""
    
    def __init__(
        self,
        mod_repository: ModRepository,
        scan_result_repository: ScanResultRepository,
        scanner: Any  # 扫描器接口（将在infrastructure层实现）
    ):
        self.mod_repository = mod_repository
        self.scan_result_repository = scan_result_repository
        self.scanner = scanner
    
    def scan_directory(self, command: ScanCommand) -> ScanResultDTO:
        """扫描目录
        
        用例：用户选择一个目录进行扫描
        """
        logger.info(f"Starting directory scan: {command.directory_path}")
        
        results = ScanResultDTO(
            directory=command.directory_path,
            total_files=0,
            scanned_files=0,
            new_mods=0,
            updated_mods=0,
            failed_files=0,
            errors=[]
        )
        
        try:
            # 获取所有文件
            files = self._get_scannable_files(
                command.directory_path,
                command.include_patterns,
                command.exclude_patterns
            )
            results.total_files = len(files)
            
            # 扫描每个文件
            for file_path in files:
                try:
                    self._scan_file(file_path, command.force_rescan, results)
                    results.scanned_files += 1
                except Exception as e:
                    logger.error(f"Failed to scan {file_path}: {e}")
                    results.failed_files += 1
                    results.errors.append(f"Failed to scan {file_path}: {str(e)}")
            
            results.success = results.failed_files == 0
            results.completed_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Directory scan failed: {e}")
            results.success = False
            results.errors.append(str(e))
        
        return results
    
    def scan_file(self, file_path: str, force: bool = False) -> ModDTO:
        """扫描单个文件
        
        用例：扫描或重新扫描单个模组文件
        """
        logger.info(f"Scanning file: {file_path}")
        
        # 计算文件哈希
        content_hash = self._calculate_file_hash(file_path)
        
        # 检查是否已存在
        existing_mod = self.mod_repository.find_by_file_path(file_path)
        
        if existing_mod and not force:
            if not existing_mod.needs_rescan(content_hash):
                logger.info(f"File {file_path} unchanged, skipping scan")
                return ModDTO.from_domain(existing_mod)
        
        # 执行扫描
        scan_result = self.scanner.scan(file_path)
        
        if existing_mod:
            # 更新现有模组
            existing_mod.scan_completed(content_hash, len(scan_result.translations))
            self.mod_repository.update(existing_mod)
            mod = existing_mod
        else:
            # 创建新模组
            mod = Mod.create(
                mod_id=scan_result.mod_id,
                name=scan_result.name,
                version=scan_result.version,
                file_path=file_path
            )
            mod.scan_completed(content_hash, len(scan_result.translations))
            self.mod_repository.save(mod)
        
        # 保存扫描结果
        self.scan_result_repository.save_scan_result(
            mod.mod_id,
            scan_result.to_dict()
        )
        
        return ModDTO.from_domain(mod)
    
    def rescan_all(self, command: RescanCommand) -> ScanResultDTO:
        """重新扫描所有模组
        
        用例：批量重新扫描所有已知模组
        """
        logger.info("Starting rescan of all mods")
        
        results = ScanResultDTO(
            directory="all",
            total_files=0,
            scanned_files=0,
            new_mods=0,
            updated_mods=0,
            failed_files=0,
            errors=[]
        )
        
        # 获取需要重新扫描的模组
        if command.only_changed:
            mods = self.mod_repository.find_needs_rescan()
        else:
            mods = self.mod_repository.find_all()
        
        results.total_files = len(mods)
        
        for mod in mods:
            try:
                # 检查文件是否存在
                if not os.path.exists(mod.file_path):
                    if command.remove_missing:
                        self.mod_repository.delete(mod.mod_id)
                        logger.info(f"Removed missing mod: {mod.mod_id}")
                    continue
                
                # 重新扫描
                self.scan_file(mod.file_path, force=True)
                results.updated_mods += 1
                results.scanned_files += 1
                
            except Exception as e:
                logger.error(f"Failed to rescan {mod.mod_id}: {e}")
                results.failed_files += 1
                results.errors.append(f"Failed to rescan {mod.mod_id}: {str(e)}")
        
        results.success = results.failed_files == 0
        results.completed_at = datetime.now()
        
        return results
    
    def get_scan_progress(self, scan_id: str) -> Dict[str, Any]:
        """获取扫描进度
        
        用例：实时查看扫描进度
        """
        # 这里应该从某个进度存储中获取
        # 简化实现
        return {
            'scan_id': scan_id,
            'status': 'in_progress',
            'progress': 50,
            'current_file': 'example.jar',
            'processed': 10,
            'total': 20
        }
    
    def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描
        
        用例：用户取消正在进行的扫描
        """
        logger.info(f"Cancelling scan: {scan_id}")
        # 实现取消逻辑
        return True
    
    def _get_scannable_files(
        self,
        directory: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """获取可扫描的文件列表"""
        include_patterns = include_patterns or ['*.jar', '*.zip']
        exclude_patterns = exclude_patterns or []
        
        files = []
        path = Path(directory)
        
        for pattern in include_patterns:
            for file_path in path.rglob(pattern):
                if file_path.is_file():
                    # 检查排除模式
                    excluded = False
                    for exclude_pattern in exclude_patterns:
                        if file_path.match(exclude_pattern):
                            excluded = True
                            break
                    
                    if not excluded:
                        files.append(str(file_path))
        
        return files
    
    def _scan_file(self, file_path: str, force: bool, results: ScanResultDTO):
        """扫描单个文件并更新结果"""
        # 计算文件哈希
        content_hash = self._calculate_file_hash(file_path)
        
        # 检查是否已存在
        existing_mod = self.mod_repository.find_by_file_path(file_path)
        
        if existing_mod and not force:
            if not existing_mod.needs_rescan(content_hash):
                logger.debug(f"File {file_path} unchanged, skipping")
                return
        
        # 执行扫描
        scan_result = self.scanner.scan(file_path)
        
        if existing_mod:
            # 更新现有模组
            existing_mod.scan_completed(content_hash, len(scan_result.translations))
            self.mod_repository.update(existing_mod)
            results.updated_mods += 1
        else:
            # 创建新模组
            mod = Mod.create(
                mod_id=scan_result.mod_id,
                name=scan_result.name,
                version=scan_result.version,
                file_path=file_path
            )
            mod.scan_completed(content_hash, len(scan_result.translations))
            self.mod_repository.save(mod)
            results.new_mods += 1
        
        # 保存扫描结果
        self.scan_result_repository.save_scan_result(
            ModId(scan_result.mod_id),
            scan_result.to_dict()
        )
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        import hashlib
        
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()