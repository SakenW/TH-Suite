"""
LANG Worker - 语言文件解析
负责解析各种格式的语言文件（JSON、Properties、Lang等），提取翻译条目
"""

import json
import re
import structlog
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from zipfile import ZipFile, BadZipFile

from ..worker_manager import BaseWorker, WorkTask, WorkerResult, WorkerType
from ..event_applier import ScanEvent, EventType, create_lang_upsert_event
from ..jar_extraction_helper import AsyncJarReader

logger = structlog.get_logger(__name__)


class LangWorker(BaseWorker):
    """语言文件解析Worker"""
    
    def __init__(self, db_path: str):
        super().__init__(WorkerType.LANG, db_path)
        
        # 支持的语言文件格式
        self.lang_file_patterns = {
            'json': r'assets/.+/lang/[a-z]{2}_[a-z]{2}\.json$',
            'properties': r'assets/.+/lang/[a-z]{2}_[a-z]{2}\.properties$',  
            'lang': r'assets/.+/lang/[a-z]{2}_[a-z]{2}\.lang$'
        }
        
        # JAR文件读取器，使用数据库目录内的专用临时目录
        from pathlib import Path
        data_dir = Path(db_path).parent
        temp_extract_dir = data_dir / "temp_extracts"
        temp_extract_dir.mkdir(parents=True, exist_ok=True)
        
        self.jar_reader = AsyncJarReader(str(temp_extract_dir))
    
    async def process_task(self, task: WorkTask) -> WorkerResult:
        """处理语言文件解析任务"""
        try:
            payload = task.payload
            file_path = payload.get('file_path')
            target_languages = payload.get('target_languages', ['zh_cn', 'en_us'])
            snapshot_id = payload.get('snapshot_id')
            
            if not file_path:
                return WorkerResult(
                    task_id=task.task_id,
                    success=False,
                    events=[],
                    error_message="缺少file_path参数"
                )
            
            # 扫描前清理工作区
            logger.info("🧹 语言文件解析前清理工作区", session_id=task.session_id)
            await self.jar_reader.helper.cleanup_workspace()
            
            logger.info("🌐 开始语言文件解析", file_path=file_path, session_id=task.session_id)
            
            # 获取根路径并构造完整路径
            root_path = payload.get('root_path')
            if not Path(file_path).is_absolute():
                full_file_path = Path(root_path) / file_path
            else:
                full_file_path = Path(file_path)
                
            logger.info("解析路径调试", 
                        original_path=file_path,
                        root_path=root_path, 
                        full_path=str(full_file_path),
                        exists=full_file_path.exists())
            
            # 解析语言文件
            lang_files = await self._parse_language_files(full_file_path, target_languages)
            
            if not lang_files:
                logger.info("未找到语言文件", file_path=file_path)
                
                # 即使没有找到语言文件也要清理工作区
                await self.jar_reader.helper.cleanup_workspace()
                
                return WorkerResult(
                    task_id=task.task_id,
                    success=True,  # 不算失败，只是没有语言文件
                    events=[],
                    metrics={'language_files_found': 0}
                )
            
            # 生成事件
            events = []
            total_entries = 0
            
            for lang_file_info in lang_files:
                # 1. 语言文件信息事件
                lang_file_event = create_lang_upsert_event(
                    task.session_id,
                    lang_file_info['file_uid'],
                    {
                        'uid': lang_file_info['file_uid'],  # 确保包含UID
                        'carrier_type': 'mod',  # 假设是MOD文件
                        'carrier_uid': file_path,
                        'locale': lang_file_info['locale'],
                        'rel_path': lang_file_info['rel_path'],
                        'format': lang_file_info['format'],
                        'size': lang_file_info['size'],
                        'entries_count': len(lang_file_info['entries'])
                    },
                    lang_file_info['entries']
                )
                events.append(lang_file_event)
                total_entries += len(lang_file_info['entries'])
            
            logger.info("✅ 语言文件解析完成",
                       files_count=len(lang_files),
                       total_entries=total_entries,
                       events_count=len(events))
            
            # 解析完成后清理工作区
            logger.info("🧹 语言文件解析完成后清理工作区", session_id=task.session_id)
            await self.jar_reader.helper.cleanup_workspace()
            
            return WorkerResult(
                task_id=task.task_id,
                success=True,
                events=events,
                metrics={
                    'language_files_found': len(lang_files),
                    'total_translation_entries': total_entries,
                    'locales_found': list(set(lf['locale'] for lf in lang_files))
                }
            )
            
        except Exception as e:
            logger.error("❌ 语言文件解析失败", error=str(e))
            
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
    
    async def _parse_language_files(self, file_path: Path, target_languages: List[str]) -> List[Dict[str, Any]]:
        """解析语言文件"""
        lang_files = []
        
        if not file_path.exists():
            return lang_files
        
        if file_path.is_file() and file_path.suffix.lower() in {'.jar', '.zip'}:
            # 从ZIP/JAR文件中解析
            lang_files = await self._parse_zip_language_files(file_path, target_languages)
        elif file_path.is_file() and file_path.suffix.lower() in {'.json', '.properties', '.lang'}:
            # 处理单个语言文件
            lang_files = await self._parse_single_language_file(file_path, target_languages)
        elif file_path.is_dir():
            # 从目录中解析
            lang_files = await self._parse_directory_language_files(file_path, target_languages)
        
        return lang_files
    
    async def _parse_single_language_file(self, file_path: Path, target_languages: List[str]) -> List[Dict[str, Any]]:
        """解析单个语言文件"""
        lang_files = []
        
        # 识别语言文件类型和locale
        format_type, locale = self._identify_language_file(str(file_path))
        if not format_type or (target_languages and locale not in target_languages):
            logger.info("语言文件过滤", file_path=str(file_path), format_type=format_type, locale=locale)
            return lang_files
        
        # 读取并解析文件内容
        try:
            file_content = file_path.read_text(encoding='utf-8')
            entries = await self._parse_language_content(file_content, format_type)
            
            if entries:
                lang_file_uid = str(file_path.name)  # 使用文件名作为UID
                lang_files.append({
                    'file_uid': lang_file_uid,
                    'locale': locale,
                    'rel_path': str(file_path),  # 使用完整路径
                    'format': format_type,
                    'size': file_path.stat().st_size,
                    'entries': entries
                })
                
                logger.info("成功解析单个语言文件", 
                           file=str(file_path),
                           locale=locale,
                           entries_count=len(entries))
                
        except Exception as e:
            logger.warning(f"无法解析语言文件", file=str(file_path), error=str(e))
        
        return lang_files
    
    async def _parse_zip_language_files(self, zip_path: Path, target_languages: List[str]) -> List[Dict[str, Any]]:
        """从ZIP/JAR文件中解析语言文件 - 使用解压到硬盘的方式"""
        lang_files = []
        
        try:
            # 使用新的JAR解压助手
            jar_language_files = await self.jar_reader.find_language_files(
                zip_path, 
                self.lang_file_patterns
            )
            
            for lang_file_info in jar_language_files:
                # 检查语言和目标语言过滤
                format_type, locale = self._identify_language_file(lang_file_info['rel_path'])
                if not format_type or (target_languages and locale not in target_languages):
                    continue
                
                # 解析语言文件内容
                try:
                    entries = await self._parse_language_content(
                        lang_file_info['content'], 
                        lang_file_info['format']
                    )
                    
                    if entries:
                        lang_file_uid = f"{zip_path.name}:{lang_file_info['rel_path']}"
                        lang_files.append({
                            'file_uid': lang_file_uid,
                            'locale': locale,
                            'rel_path': lang_file_info['rel_path'],
                            'format': lang_file_info['format'],
                            'size': lang_file_info['size'],
                            'entries': entries
                        })
                        
                        logger.debug("成功解析语言文件", 
                                   file=lang_file_info['rel_path'],
                                   locale=locale,
                                   entries_count=len(entries))
                        
                except Exception as e:
                    logger.debug("无法解析语言文件内容", 
                               file=lang_file_info['rel_path'], 
                               error=str(e))
                    continue
                        
        except Exception as e:
            logger.debug("JAR文件解析失败", file=str(zip_path), error=str(e))
        
        return lang_files
    
    async def _parse_directory_language_files(self, dir_path: Path, target_languages: List[str]) -> List[Dict[str, Any]]:
        """从目录中解析语言文件"""
        logger.info("🗂️ 开始目录语言文件解析", 
                   dir_path=str(dir_path),
                   target_languages=target_languages,
                   exists=dir_path.exists(),
                   is_dir=dir_path.is_dir())
        lang_files = []
        
        # 递归查找语言文件
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            rel_path = file_path.relative_to(dir_path)
            
            # 检查是否是语言文件
            format_type, locale = self._identify_language_file(str(rel_path))
            if not format_type or (target_languages and locale not in target_languages):
                continue
            
            # 读取并解析文件内容
            try:
                file_content = file_path.read_text(encoding='utf-8')
                entries = await self._parse_language_content(file_content, format_type)
                
                if entries:
                    lang_file_uid = str(rel_path)
                    lang_files.append({
                        'file_uid': lang_file_uid,
                        'locale': locale,
                        'rel_path': str(rel_path),
                        'format': format_type,
                        'size': file_path.stat().st_size,
                        'entries': entries
                    })
                    
            except Exception as e:
                logger.debug(f"无法解析语言文件", file=str(file_path), error=str(e))
                continue
        
        return lang_files
    
    def _identify_language_file(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """识别语言文件类型和locale"""
        logger.info("语言文件识别调试", 
                   file_path=file_path,
                   patterns=self.lang_file_patterns)
        
        for format_type, pattern in self.lang_file_patterns.items():
            matches = re.search(pattern, file_path, re.IGNORECASE)
            logger.info("模式匹配测试", 
                       format_type=format_type,
                       pattern=pattern,
                       file_path=file_path,
                       matches=bool(matches))
            
            if matches:
                # 提取locale
                locale_match = re.search(r'([a-z]{2}_[a-z]{2})\.' + format_type + r'$', file_path, re.IGNORECASE)
                if locale_match:
                    locale = locale_match.group(1).lower()
                    logger.info("语言文件识别成功", 
                               file_path=file_path,
                               format_type=format_type,
                               locale=locale)
                    return format_type, locale
        
        logger.info("语言文件识别失败", file_path=file_path)
        return None, None
    
    async def _parse_language_content(self, content: str, format_type: str) -> List[Dict[str, Any]]:
        """解析语言文件内容"""
        entries = []
        
        try:
            if format_type == 'json':
                entries = await self._parse_json_language(content)
            elif format_type == 'properties':
                entries = await self._parse_properties_language(content)
            elif format_type == 'lang':
                entries = await self._parse_lang_language(content)
                
        except Exception as e:
            logger.debug(f"解析{format_type}格式失败", error=str(e))
        
        return entries
    
    async def _parse_json_language(self, content: str) -> List[Dict[str, Any]]:
        """解析JSON格式语言文件"""
        entries = []
        
        try:
            lang_data = json.loads(content)
            
            # 递归解析JSON对象（支持嵌套）
            def extract_entries(obj, prefix=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        full_key = f"{prefix}.{key}" if prefix else key
                        if isinstance(value, str):
                            entries.append({
                                'key': full_key,
                                'src_text': value,
                                'dst_text': '',  # 初始为空
                                'status': 'new'
                            })
                        elif isinstance(value, dict):
                            extract_entries(value, full_key)
            
            extract_entries(lang_data)
            
        except json.JSONDecodeError as e:
            logger.debug("JSON解析失败", error=str(e))
        
        return entries
    
    async def _parse_properties_language(self, content: str) -> List[Dict[str, Any]]:
        """解析Properties格式语言文件"""
        entries = []
        
        for line_no, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('#') or line.startswith('!'):
                continue
            
            # 解析key=value格式
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key and value:
                    entries.append({
                        'key': key,
                        'src_text': value,
                        'dst_text': '',
                        'status': 'new'
                    })
        
        return entries
    
    async def _parse_lang_language(self, content: str) -> List[Dict[str, Any]]:
        """解析Lang格式语言文件（类似Properties但可能有不同的格式）"""
        # Lang格式通常类似Properties，但可能有细微差别
        return await self._parse_properties_language(content)