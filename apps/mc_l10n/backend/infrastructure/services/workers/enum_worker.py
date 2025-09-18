"""
ENUM Worker - 目录枚举和manifest解析
负责扫描目录结构，识别MOD文件、资源包等，解析基础manifest信息
"""

import json
import structlog
from pathlib import Path
from typing import Dict, List, Any, Optional
from zipfile import ZipFile, BadZipFile

from ..worker_manager import BaseWorker, WorkTask, WorkerResult, WorkerType
from ..event_applier import ScanEvent, EventType, create_list_upsert_event
from ..jar_extraction_helper import AsyncJarReader

logger = structlog.get_logger(__name__)


class EnumWorker(BaseWorker):
    """目录枚举Worker"""
    
    def __init__(self, db_path: str):
        super().__init__(WorkerType.ENUM, db_path)
        
        # 支持的文件类型
        self.mod_extensions = {'.jar', '.zip', '.disabled'}
        self.resource_pack_extensions = {'.zip', '.disabled'}
        self.config_extensions = {'.toml', '.json', '.txt', '.cfg', '.properties'}
        
        # JAR文件读取器，使用数据库目录内的专用临时目录
        from pathlib import Path
        data_dir = Path(db_path).parent
        temp_extract_dir = data_dir / "temp_extracts"
        temp_extract_dir.mkdir(parents=True, exist_ok=True)
        
        self.jar_reader = AsyncJarReader(str(temp_extract_dir))
    
    async def process_task(self, task: WorkTask) -> WorkerResult:
        """处理目录枚举任务"""
        try:
            payload = task.payload
            root_path = payload.get('root_path')
            snapshot_id = payload.get('snapshot_id')
            
            if not root_path:
                return WorkerResult(
                    task_id=task.task_id,
                    success=False,
                    events=[],
                    error_message="缺少root_path参数"
                )
            
            # 扫描前清理工作区
            logger.info("🧹 扫描前清理工作区", session_id=task.session_id)
            await self.jar_reader.helper.cleanup_workspace()
            
            logger.info("🔍 开始目录枚举", root_path=root_path, session_id=task.session_id)
            
            # 执行目录枚举
            enum_result = await self._enumerate_directory(Path(root_path))
            
            # 生成事件
            events = []
            
            # 1. MOD文件事件
            for mod_info in enum_result['mods']:
                event = create_list_upsert_event(
                    task.session_id,
                    mod_info['file_path'],
                    {
                        'type': 'mod_file',
                        'file_path': mod_info['file_path'],
                        'file_size': mod_info['file_size'],
                        'file_type': mod_info['file_type'],
                        'manifest_info': mod_info.get('manifest_info', {}),
                        'snapshot_id': snapshot_id
                    }
                )
                events.append(event)
            
            # 2. 资源包事件
            for rp_info in enum_result['resource_packs']:
                event = create_list_upsert_event(
                    task.session_id,
                    rp_info['file_path'],
                    {
                        'type': 'resource_pack',
                        'file_path': rp_info['file_path'],
                        'file_size': rp_info['file_size'],
                        'pack_meta': rp_info.get('pack_meta', {}),
                        'snapshot_id': snapshot_id
                    }
                )
                events.append(event)
            
            # 3. 配置文件事件
            for config_info in enum_result['configs']:
                event = create_list_upsert_event(
                    task.session_id,
                    config_info['file_path'],
                    {
                        'type': 'config_file',
                        'file_path': config_info['file_path'],
                        'file_size': config_info['file_size'],
                        'config_type': config_info['config_type'],
                        'snapshot_id': snapshot_id
                    }
                )
                events.append(event)
            
            logger.info("✅ 目录枚举完成",
                       mods_count=len(enum_result['mods']),
                       resource_packs_count=len(enum_result['resource_packs']),
                       configs_count=len(enum_result['configs']),
                       events_count=len(events))
            
            # 扫描完成后再次清理工作区
            logger.info("🧹 扫描完成后清理工作区", session_id=task.session_id)
            await self.jar_reader.helper.cleanup_workspace()
            
            return WorkerResult(
                task_id=task.task_id,
                success=True,
                events=events,
                metrics={
                    'mods_found': len(enum_result['mods']),
                    'resource_packs_found': len(enum_result['resource_packs']),
                    'configs_found': len(enum_result['configs'])
                }
            )
            
        except Exception as e:
            logger.error("❌ 目录枚举失败", error=str(e))
            
            # 异常时也要清理工作区
            try:
                await self.jar_reader.helper.cleanup_workspace()
            except Exception as cleanup_error:
                logger.warning("异常清理工作区失败", error=str(cleanup_error))
            
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                events=[],
                error_message=str(e)
            )
    
    async def _enumerate_directory(self, root_path: Path) -> Dict[str, List[Dict]]:
        """枚举目录结构"""
        result = {
            'mods': [],
            'resource_packs': [],
            'configs': []
        }
        
        if not root_path.exists():
            logger.warning("目录不存在", path=str(root_path))
            return result
        
        # 1. 扫描mods目录
        mods_dir = root_path / "mods"
        if mods_dir.exists():
            result['mods'] = await self._scan_mods_directory(mods_dir)
        
        # 2. 扫描resourcepacks目录
        resourcepacks_dir = root_path / "resourcepacks"
        if resourcepacks_dir.exists():
            result['resource_packs'] = await self._scan_resourcepacks_directory(resourcepacks_dir)
        
        # 3. 扫描config目录
        config_dir = root_path / "config"
        if config_dir.exists():
            result['configs'] = await self._scan_config_directory(config_dir)
        
        return result
    
    async def _scan_mods_directory(self, mods_dir: Path) -> List[Dict]:
        """扫描mods目录"""
        mods = []
        
        for file_path in mods_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.mod_extensions:
                mod_info = {
                    'file_path': str(file_path.relative_to(mods_dir.parent)),
                    'file_size': file_path.stat().st_size,
                    'file_type': self._determine_mod_type(file_path),
                    'last_modified': file_path.stat().st_mtime
                }
                
                # 尝试解析manifest信息
                manifest_info = await self._extract_mod_manifest(file_path)
                if manifest_info:
                    mod_info['manifest_info'] = manifest_info
                
                mods.append(mod_info)
        
        return mods
    
    async def _scan_resourcepacks_directory(self, rp_dir: Path) -> List[Dict]:
        """扫描resourcepacks目录"""
        resource_packs = []
        
        for file_path in rp_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.resource_pack_extensions:
                rp_info = {
                    'file_path': str(file_path.relative_to(rp_dir.parent)),
                    'file_size': file_path.stat().st_size,
                    'last_modified': file_path.stat().st_mtime
                }
                
                # 尝试解析pack.mcmeta
                pack_meta = await self._extract_pack_meta(file_path)
                if pack_meta:
                    rp_info['pack_meta'] = pack_meta
                
                resource_packs.append(rp_info)
        
        return resource_packs
    
    async def _scan_config_directory(self, config_dir: Path) -> List[Dict]:
        """扫描config目录"""
        configs = []
        
        # 递归扫描config目录
        for file_path in config_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.config_extensions:
                config_info = {
                    'file_path': str(file_path.relative_to(config_dir.parent)),
                    'file_size': file_path.stat().st_size,
                    'config_type': file_path.suffix.lower(),
                    'last_modified': file_path.stat().st_mtime
                }
                configs.append(config_info)
        
        return configs
    
    def _determine_mod_type(self, file_path: Path) -> str:
        """确定MOD类型"""
        if file_path.suffix.lower() == '.jar':
            return 'jar_mod'
        elif file_path.suffix.lower() == '.zip':
            return 'zip_mod'
        elif file_path.suffix.lower() == '.disabled':
            # 检查原始扩展名
            original_name = file_path.stem
            if original_name.endswith('.jar'):
                return 'disabled_jar_mod'
            elif original_name.endswith('.zip'):
                return 'disabled_zip_mod'
        
        return 'unknown_mod'
    
    async def _extract_mod_manifest(self, file_path: Path) -> Optional[Dict]:
        """提取MOD的manifest信息"""
        if not file_path.suffix.lower() in {'.jar', '.zip'}:
            return None
        
        try:
            # 使用新的JAR读取器获取manifest信息
            manifest_files = await self.jar_reader.find_manifest_files(file_path)
            if not manifest_files:
                return None
            
            manifest_info = {}
            
            # 解析各种manifest格式
            if 'mods.toml' in manifest_files:
                manifest_info['mods_toml_raw'] = manifest_files['mods.toml']['content']
                manifest_info['loader'] = 'forge'
            
            if 'fabric.mod.json' in manifest_files:
                try:
                    fabric_data = json.loads(manifest_files['fabric.mod.json']['content'])
                    manifest_info['fabric_mod_json'] = fabric_data
                    manifest_info['loader'] = 'fabric'
                except json.JSONDecodeError:
                    pass
            
            if 'mcmod.info' in manifest_files:
                try:
                    mcmod_data = json.loads(manifest_files['mcmod.info']['content'])
                    manifest_info['mcmod_info'] = mcmod_data
                    manifest_info['loader'] = 'legacy'
                except json.JSONDecodeError:
                    pass
            
            return manifest_info if manifest_info else None
                
        except Exception as e:
            logger.debug(f"无法解析MOD manifest", file=str(file_path), error=str(e))
            return None
    
    async def _extract_pack_meta(self, file_path: Path) -> Optional[Dict]:
        """提取资源包的pack.mcmeta信息"""
        if not file_path.suffix.lower() in {'.zip'}:
            return None
        
        try:
            # 使用新的JAR读取器获取pack.mcmeta
            manifest_files = await self.jar_reader.find_manifest_files(file_path)
            if 'pack.mcmeta' in manifest_files:
                try:
                    pack_data = json.loads(manifest_files['pack.mcmeta']['content'])
                    return pack_data
                except json.JSONDecodeError:
                    pass
                
        except Exception as e:
            logger.debug(f"无法解析资源包meta", file=str(file_path), error=str(e))
            return None
        
        return None