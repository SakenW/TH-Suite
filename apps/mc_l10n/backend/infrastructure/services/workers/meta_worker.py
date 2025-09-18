"""
META Worker - MOD元数据解析
负责深度解析MOD的详细元数据信息，包括依赖关系、版本信息、作者信息等
"""

import json
import re
import structlog
from pathlib import Path
from typing import Dict, List, Any, Optional
from zipfile import ZipFile, BadZipFile

from ..worker_manager import BaseWorker, WorkTask, WorkerResult, WorkerType
from ..event_applier import ScanEvent, EventType, create_field_patch_event

logger = structlog.get_logger(__name__)


class MetaWorker(BaseWorker):
    """MOD元数据解析Worker"""
    
    def __init__(self, db_path: str):
        super().__init__(WorkerType.META, db_path)
    
    async def process_task(self, task: WorkTask) -> WorkerResult:
        """处理MOD元数据解析任务"""
        try:
            payload = task.payload
            file_path = payload.get('file_path')
            snapshot_id = payload.get('snapshot_id')
            
            if not file_path:
                return WorkerResult(
                    task_id=task.task_id,
                    success=False,
                    events=[],
                    error_message="缺少file_path参数"
                )
            
            logger.info("🔧 开始MOD元数据解析", file_path=file_path, session_id=task.session_id)
            
            # 解析MOD元数据
            meta_data = await self._parse_mod_metadata(Path(file_path))
            
            if not meta_data:
                logger.warning("无法解析MOD元数据", file_path=file_path)
                return WorkerResult(
                    task_id=task.task_id,
                    success=True,  # 不算失败，只是没有元数据
                    events=[],
                    metrics={'metadata_found': False}
                )
            
            # 生成事件
            events = []
            
            # 1. MOD基础信息更新事件
            mod_info_event = create_field_patch_event(
                task.session_id,
                file_path,
                'core_mods',
                {
                    'name': meta_data.get('name', ''),
                    'modid': meta_data.get('modid', ''),
                    'homepage': meta_data.get('homepage', ''),
                    'meta_json': json.dumps(meta_data, ensure_ascii=False)
                }
            )
            events.append(mod_info_event)
            
            # 2. MOD版本信息事件
            if 'version_info' in meta_data:
                version_info = meta_data['version_info']
                mod_version_event = create_field_patch_event(
                    task.session_id,
                    f"{file_path}_version",
                    'core_mod_versions',
                    {
                        'version': version_info.get('version', ''),
                        'mc_version': version_info.get('mc_version', ''),
                        'loader': version_info.get('loader', ''),
                        'meta_json': json.dumps(version_info, ensure_ascii=False)
                    }
                )
                events.append(mod_version_event)
            
            # 3. 依赖关系事件
            if 'dependencies' in meta_data:
                deps_event = create_field_patch_event(
                    task.session_id,
                    f"{file_path}_deps",
                    'dependencies',
                    {
                        'dependencies_json': json.dumps(meta_data['dependencies'], ensure_ascii=False)
                    }
                )
                events.append(deps_event)
            
            logger.info("✅ MOD元数据解析完成",
                       modid=meta_data.get('modid', 'unknown'),
                       version=meta_data.get('version_info', {}).get('version', 'unknown'),
                       events_count=len(events))
            
            return WorkerResult(
                task_id=task.task_id,
                success=True,
                events=events,
                metrics={
                    'metadata_found': True,
                    'modid': meta_data.get('modid'),
                    'loader': meta_data.get('version_info', {}).get('loader'),
                    'dependencies_count': len(meta_data.get('dependencies', []))
                }
            )
            
        except Exception as e:
            logger.error("❌ MOD元数据解析失败", error=str(e))
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                events=[],
                error_message=str(e)
            )
    
    async def _parse_mod_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """解析MOD元数据"""
        if not file_path.exists() or file_path.suffix.lower() not in {'.jar', '.zip'}:
            return None
        
        try:
            with ZipFile(file_path, 'r') as zip_file:
                metadata = {}
                
                # 1. 解析Forge MOD (mods.toml)
                forge_meta = await self._parse_forge_metadata(zip_file)
                if forge_meta:
                    metadata.update(forge_meta)
                    return metadata
                
                # 2. 解析Fabric MOD (fabric.mod.json)
                fabric_meta = await self._parse_fabric_metadata(zip_file)
                if fabric_meta:
                    metadata.update(fabric_meta)
                    return metadata
                
                # 3. 解析Quilt MOD (quilt.mod.json)
                quilt_meta = await self._parse_quilt_metadata(zip_file)
                if quilt_meta:
                    metadata.update(quilt_meta)
                    return metadata
                
                # 4. 解析Legacy MOD (mcmod.info)
                legacy_meta = await self._parse_legacy_metadata(zip_file)
                if legacy_meta:
                    metadata.update(legacy_meta)
                    return metadata
                
                return None
                
        except (BadZipFile, Exception) as e:
            logger.debug(f"无法读取MOD文件", file=str(file_path), error=str(e))
            return None
    
    async def _parse_forge_metadata(self, zip_file: ZipFile) -> Optional[Dict[str, Any]]:
        """解析Forge MOD的mods.toml"""
        if 'META-INF/mods.toml' not in zip_file.namelist():
            return None
        
        try:
            mods_toml_content = zip_file.read('META-INF/mods.toml').decode('utf-8')
            
            # 简单的TOML解析（避免引入额外依赖）
            metadata = {'loader': 'forge'}
            
            # 解析基础信息
            modid_match = re.search(r'modId\s*=\s*["\']([^"\']+)["\']', mods_toml_content)
            if modid_match:
                metadata['modid'] = modid_match.group(1)
            
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', mods_toml_content)
            if version_match:
                metadata['version_info'] = {'version': version_match.group(1), 'loader': 'forge'}
            
            display_name_match = re.search(r'displayName\s*=\s*["\']([^"\']+)["\']', mods_toml_content)
            if display_name_match:
                metadata['name'] = display_name_match.group(1)
            
            description_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', mods_toml_content)
            if description_match:
                metadata['description'] = description_match.group(1)
            
            # 解析作者信息
            authors_match = re.search(r'authors\s*=\s*["\']([^"\']+)["\']', mods_toml_content)
            if authors_match:
                metadata['authors'] = authors_match.group(1).split(',')
            
            # 解析依赖关系
            dependencies = []
            # 简化的依赖解析
            dep_blocks = re.findall(r'\[\[dependencies\..*?\]\].*?(?=\[\[|$)', mods_toml_content, re.DOTALL)
            for dep_block in dep_blocks:
                dep_modid_match = re.search(r'modId\s*=\s*["\']([^"\']+)["\']', dep_block)
                dep_mandatory_match = re.search(r'mandatory\s*=\s*(true|false)', dep_block)
                dep_version_match = re.search(r'versionRange\s*=\s*["\']([^"\']+)["\']', dep_block)
                
                if dep_modid_match:
                    dependencies.append({
                        'modid': dep_modid_match.group(1),
                        'mandatory': dep_mandatory_match.group(1) == 'true' if dep_mandatory_match else False,
                        'version_range': dep_version_match.group(1) if dep_version_match else '*'
                    })
            
            if dependencies:
                metadata['dependencies'] = dependencies
            
            return metadata
            
        except Exception as e:
            logger.debug("解析Forge mods.toml失败", error=str(e))
            return None
    
    async def _parse_fabric_metadata(self, zip_file: ZipFile) -> Optional[Dict[str, Any]]:
        """解析Fabric MOD的fabric.mod.json"""
        if 'fabric.mod.json' not in zip_file.namelist():
            return None
        
        try:
            fabric_json_content = zip_file.read('fabric.mod.json').decode('utf-8')
            fabric_data = json.loads(fabric_json_content)
            
            metadata = {'loader': 'fabric'}
            
            # 基础信息
            metadata['modid'] = fabric_data.get('id', '')
            metadata['name'] = fabric_data.get('name', '')
            metadata['description'] = fabric_data.get('description', '')
            
            # 版本信息
            if fabric_data.get('version'):
                metadata['version_info'] = {
                    'version': fabric_data['version'],
                    'loader': 'fabric'
                }
            
            # 作者信息
            if 'authors' in fabric_data:
                authors = fabric_data['authors']
                if isinstance(authors, list):
                    metadata['authors'] = [str(author) for author in authors]
                else:
                    metadata['authors'] = [str(authors)]
            
            # 联系信息
            if 'contact' in fabric_data:
                contact = fabric_data['contact']
                if 'homepage' in contact:
                    metadata['homepage'] = contact['homepage']
                if 'sources' in contact:
                    metadata['sources'] = contact['sources']
            
            # 依赖关系
            if 'depends' in fabric_data:
                dependencies = []
                for dep_id, dep_version in fabric_data['depends'].items():
                    dependencies.append({
                        'modid': dep_id,
                        'mandatory': True,
                        'version_range': dep_version
                    })
                metadata['dependencies'] = dependencies
            
            return metadata
            
        except Exception as e:
            logger.debug("解析Fabric fabric.mod.json失败", error=str(e))
            return None
    
    async def _parse_quilt_metadata(self, zip_file: ZipFile) -> Optional[Dict[str, Any]]:
        """解析Quilt MOD的quilt.mod.json"""
        if 'quilt.mod.json' not in zip_file.namelist():
            return None
        
        try:
            quilt_json_content = zip_file.read('quilt.mod.json').decode('utf-8')
            quilt_data = json.loads(quilt_json_content)
            
            metadata = {'loader': 'quilt'}
            
            # Quilt的JSON结构类似Fabric但可能有所不同
            if 'quilt_loader' in quilt_data:
                loader_data = quilt_data['quilt_loader']
                metadata['modid'] = loader_data.get('id', '')
                
                if 'metadata' in loader_data:
                    meta = loader_data['metadata']
                    metadata['name'] = meta.get('name', '')
                    metadata['description'] = meta.get('description', '')
                    
                    if 'contributors' in meta:
                        metadata['authors'] = list(meta['contributors'].keys())
            
            # 版本信息
            metadata['version_info'] = {
                'version': quilt_data.get('version', ''),
                'loader': 'quilt'
            }
            
            return metadata
            
        except Exception as e:
            logger.debug("解析Quilt quilt.mod.json失败", error=str(e))
            return None
    
    async def _parse_legacy_metadata(self, zip_file: ZipFile) -> Optional[Dict[str, Any]]:
        """解析Legacy MOD的mcmod.info"""
        if 'mcmod.info' not in zip_file.namelist():
            return None
        
        try:
            mcmod_info_content = zip_file.read('mcmod.info').decode('utf-8')
            mcmod_data = json.loads(mcmod_info_content)
            
            # mcmod.info可能是数组或对象
            if isinstance(mcmod_data, list) and mcmod_data:
                mod_info = mcmod_data[0]
            elif isinstance(mcmod_data, dict):
                mod_info = mcmod_data
            else:
                return None
            
            metadata = {'loader': 'legacy'}
            
            # 基础信息
            metadata['modid'] = mod_info.get('modid', '')
            metadata['name'] = mod_info.get('name', '')
            metadata['description'] = mod_info.get('description', '')
            
            # 版本信息
            if mod_info.get('version'):
                metadata['version_info'] = {
                    'version': mod_info['version'],
                    'loader': 'legacy'
                }
            
            # 作者信息
            if 'authorList' in mod_info:
                metadata['authors'] = mod_info['authorList']
            elif 'authors' in mod_info:
                authors = mod_info['authors']
                if isinstance(authors, list):
                    metadata['authors'] = authors
                else:
                    metadata['authors'] = [authors]
            
            # 主页
            if mod_info.get('url'):
                metadata['homepage'] = mod_info['url']
            
            # 依赖关系
            if 'dependencies' in mod_info:
                dependencies = []
                for dep in mod_info['dependencies']:
                    dependencies.append({
                        'modid': dep,
                        'mandatory': True,
                        'version_range': '*'
                    })
                metadata['dependencies'] = dependencies
            
            return metadata
            
        except Exception as e:
            logger.debug("解析Legacy mcmod.info失败", error=str(e))
            return None