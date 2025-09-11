"""
高级JAR处理器
基于升级方案的安全JAR修改和回写能力，专注于Minecraft MOD文件处理
"""

import json
import zipfile
import shutil
import hashlib
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class ModificationType(Enum):
    """修改类型"""
    ADD_FILE = "add_file"
    UPDATE_FILE = "update_file"
    DELETE_FILE = "delete_file"


class BackupPolicy(Enum):
    """备份策略"""
    ALWAYS = "always"
    NEVER = "never"
    ON_FAILURE = "on_failure"


class ModLoaderType(Enum):
    """MOD加载器类型"""
    FABRIC = "fabric"
    FORGE = "forge"
    QUILT = "quilt"
    NEOFORGE = "neoforge"
    UNKNOWN = "unknown"


@dataclass
class JarModification:
    """JAR修改描述"""
    type: ModificationType
    path: str
    content: Optional[bytes] = None
    original_content: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "path": self.path,
            "has_content": self.content is not None,
            "has_original": self.original_content is not None,
            "metadata": self.metadata or {}
        }


@dataclass
class ModInfo:
    """MOD信息"""
    id: str
    name: str
    version: str
    description: str = ""
    loader_type: ModLoaderType = ModLoaderType.UNKNOWN
    jar_path: str = ""
    authors: List[str] = None
    minecraft_version: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LanguageFile:
    """语言文件信息"""
    mod_id: str
    language: str
    file_path: str
    format: str  # "json" or "lang"
    translations: Dict[str, str] = None
    
    def __post_init__(self):
        if self.translations is None:
            self.translations = {}


@dataclass
class JarSignatureInfo:
    """JAR签名信息"""
    signed: bool
    signer: Optional[str] = None
    algorithm: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class JarIntegrityCheck:
    """JAR完整性检查结果"""
    valid: bool
    file_count: int
    total_size: int
    errors: List[str]
    warnings: List[str]


@dataclass
class JarModificationResult:
    """JAR修改结果"""
    jar_path: str
    success: bool
    backup_path: Optional[str] = None
    final_hash: Optional[str] = None
    successful_modifications: List[JarModification] = None
    failed_modifications: List[tuple[JarModification, str]] = None
    warnings: List[str] = None
    errors: List[str] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        """初始化列表字段"""
        if self.successful_modifications is None:
            self.successful_modifications = []
        if self.failed_modifications is None:
            self.failed_modifications = []
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
    
    def mark_successful(self):
        """标记为成功"""
        self.success = True
    
    def fail(self, reason: str) -> 'JarModificationResult':
        """标记为失败"""
        self.success = False
        self.errors.append(reason)
        return self
    
    def add_successful_modification(self, modification: JarModification):
        """添加成功的修改"""
        self.successful_modifications.append(modification)
    
    def add_failed_modification(self, modification: JarModification, error: str):
        """添加失败的修改"""
        self.failed_modifications.append((modification, error))
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)


class JarBackupManager:
    """JAR备份管理器"""
    
    def __init__(self, backup_dir: Optional[str] = None):
        self.backup_dir = Path(backup_dir) if backup_dir else Path.cwd() / "jar_backups"
        self.backup_dir.mkdir(exist_ok=True, parents=True)
    
    async def create_backup(self, jar_path: str) -> str:
        """创建备份"""
        jar_file = Path(jar_path)
        if not jar_file.exists():
            raise FileNotFoundError(f"JAR文件不存在: {jar_path}")
        
        # 生成备份文件名
        timestamp = int(time.time())
        backup_name = f"{jar_file.stem}_{timestamp}.backup{jar_file.suffix}"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(jar_path, backup_path)
            logger.info("JAR备份创建成功",
                       original=jar_path,
                       backup=str(backup_path))
            return str(backup_path)
        except Exception as e:
            logger.error("JAR备份创建失败",
                        original=jar_path,
                        error=str(e))
            raise
    
    async def restore_from_backup(self, jar_path: str, backup_path: str):
        """从备份恢复"""
        if not Path(backup_path).exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        try:
            shutil.copy2(backup_path, jar_path)
            logger.info("JAR已从备份恢复",
                       jar_path=jar_path,
                       backup_path=backup_path)
        except Exception as e:
            logger.error("JAR备份恢复失败",
                        jar_path=jar_path,
                        backup_path=backup_path,
                        error=str(e))
            raise


class JarSignatureVerifier:
    """JAR签名验证器"""
    
    async def check_signature(self, jar_path: str) -> JarSignatureInfo:
        """检查JAR签名"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # 检查META-INF目录中的签名文件
                signature_files = [
                    f for f in file_list 
                    if f.startswith('META-INF/') and (
                        f.endswith('.SF') or 
                        f.endswith('.DSA') or 
                        f.endswith('.RSA')
                    )
                ]
                
                if not signature_files:
                    return JarSignatureInfo(signed=False)
                
                # 提取签名信息
                signer = None
                algorithm = None
                
                for sig_file in signature_files:
                    if sig_file.endswith('.SF'):
                        base_name = Path(sig_file).stem
                        if base_name != 'MANIFEST':
                            signer = base_name
                    elif sig_file.endswith('.RSA'):
                        algorithm = 'RSA'
                    elif sig_file.endswith('.DSA'):
                        algorithm = 'DSA'
                
                return JarSignatureInfo(
                    signed=True,
                    signer=signer,
                    algorithm=algorithm,
                    timestamp=Path(jar_path).stat().st_mtime
                )
                
        except Exception as e:
            logger.error("JAR签名检查失败", jar_path=jar_path, error=str(e))
            return JarSignatureInfo(signed=False)


class JarIntegrityChecker:
    """JAR完整性检查器"""
    
    async def verify_jar(self, jar_path: str) -> JarIntegrityCheck:
        """验证JAR完整性"""
        errors = []
        warnings = []
        file_count = 0
        total_size = 0
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                # 测试ZIP完整性
                try:
                    bad_file = jar.testzip()
                    if bad_file:
                        errors.append(f"损坏的文件: {bad_file}")
                except Exception as e:
                    errors.append(f"ZIP完整性测试失败: {str(e)}")
                
                # 统计文件信息
                for info in jar.infolist():
                    if not info.is_dir():
                        file_count += 1
                        total_size += info.file_size
                        
                        # 检查文件路径
                        if '../' in info.filename or info.filename.startswith('/'):
                            warnings.append(f"可疑文件路径: {info.filename}")
                
                # 检查必要的文件
                file_list = jar.namelist()
                if 'META-INF/MANIFEST.MF' not in file_list:
                    warnings.append("缺少MANIFEST.MF文件")
                
                # 检查MOD元数据文件
                has_mod_metadata = any(
                    f in file_list for f in [
                        'META-INF/mods.toml',
                        'fabric.mod.json',
                        'quilt.mod.json'
                    ]
                )
                
                if not has_mod_metadata:
                    warnings.append("未找到MOD元数据文件")
                
        except zipfile.BadZipFile:
            errors.append("无效的ZIP文件")
        except Exception as e:
            errors.append(f"完整性检查异常: {str(e)}")
        
        return JarIntegrityCheck(
            valid=len(errors) == 0,
            file_count=file_count,
            total_size=total_size,
            errors=errors,
            warnings=warnings
        )


class AdvancedJarProcessor:
    """高级JAR处理器 - 专注于Minecraft MOD的安全处理"""
    
    def __init__(self):
        self.backup_manager = JarBackupManager()
        self.signature_verifier = JarSignatureVerifier()
        self.integrity_checker = JarIntegrityChecker()
        self.supported_extensions = {'.jar'}
        
        logger.info("高级JAR处理器初始化完成")
    
    def is_jar_file(self, file_path: Path) -> bool:
        """检查文件是否为JAR文件"""
        return file_path.suffix.lower() in self.supported_extensions
    
    async def extract_mod_info(self, jar_path: Path) -> Optional[ModInfo]:
        """从JAR文件中提取MOD信息"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                file_list = jar.namelist()
                
                # Fabric/Quilt
                if "fabric.mod.json" in file_list:
                    return await self._extract_fabric_info(jar, jar_path)
                elif "quilt.mod.json" in file_list:
                    return await self._extract_quilt_info(jar, jar_path)
                
                # Forge (现代)
                elif "META-INF/mods.toml" in file_list:
                    return await self._extract_forge_info(jar, jar_path)
                
                # Forge (传统)
                elif "mcmod.info" in file_list:
                    return await self._extract_legacy_forge_info(jar, jar_path)
                
                # 未知类型，使用文件名推测
                else:
                    return self._extract_fallback_info(jar_path)
                    
        except Exception as e:
            logger.error("提取MOD信息失败", jar_path=str(jar_path), error=str(e))
            return None
    
    async def extract_language_files(
        self, 
        jar_path: Path, 
        mod_info: Optional[ModInfo] = None
    ) -> List[LanguageFile]:
        """从JAR文件中提取语言文件"""
        language_files = []
        
        if mod_info is None:
            mod_info = await self.extract_mod_info(jar_path)
        
        if mod_info is None:
            logger.warning("无法获取MOD信息，跳过语言文件提取", jar_path=str(jar_path))
            return language_files
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as jar:
                for file_info in jar.filelist:
                    file_path = file_info.filename
                    
                    # 检查是否为语言文件
                    if self._is_language_file(file_path):
                        lang_file = await self._extract_language_file(
                            jar, file_info, mod_info.id
                        )
                        if lang_file:
                            language_files.append(lang_file)
                            
        except Exception as e:
            logger.error("提取语言文件失败", jar_path=str(jar_path), error=str(e))
        
        return language_files
    
    async def safe_jar_modification(
        self,
        jar_path: str,
        modifications: List[JarModification],
        backup_policy: BackupPolicy = BackupPolicy.ALWAYS
    ) -> JarModificationResult:
        """安全的JAR文件修改"""
        start_time = time.time()
        result = JarModificationResult(jar_path=jar_path, success=False)
        
        try:
            # 1. 预检查
            if not await self._pre_modification_check(jar_path, modifications):
                return result.fail("预检查失败")
            
            # 2. 创建备份
            if backup_policy != BackupPolicy.NEVER:
                try:
                    backup_path = await self.backup_manager.create_backup(jar_path)
                    result.backup_path = backup_path
                except Exception as e:
                    if backup_policy == BackupPolicy.ALWAYS:
                        return result.fail(f"备份创建失败: {str(e)}")
                    else:
                        result.add_warning(f"备份创建失败: {str(e)}")
            
            # 3. 验证JAR签名(如果有)
            signature_info = await self.signature_verifier.check_signature(jar_path)
            if signature_info.signed:
                logger.warning("JAR文件已签名，修改将破坏签名", 
                             jar_path=jar_path,
                             signer=signature_info.signer)
                result.add_warning("signature_will_be_broken")
            
            # 4. 执行修改
            temp_jar_path = f"{jar_path}.tmp"
            await self._apply_modifications_to_new_jar(
                jar_path, temp_jar_path, modifications, result
            )
            
            # 5. 完整性验证
            integrity_check = await self.integrity_checker.verify_jar(temp_jar_path)
            if not integrity_check.valid:
                # 清理临时文件
                Path(temp_jar_path).unlink(missing_ok=True)
                
                # 回滚修改
                if result.backup_path:
                    await self.backup_manager.restore_from_backup(jar_path, result.backup_path)
                
                return result.fail(f"完整性验证失败: {'; '.join(integrity_check.errors)}")
            
            # 添加完整性警告
            for warning in integrity_check.warnings:
                result.add_warning(warning)
            
            # 6. 替换原文件
            shutil.move(temp_jar_path, jar_path)
            
            # 7. 计算修改后的哈希
            result.final_hash = await self._calculate_jar_hash(jar_path)
            result.mark_successful()
            
            logger.info("JAR修改完成",
                       jar_path=jar_path,
                       successful_modifications=len(result.successful_modifications),
                       failed_modifications=len(result.failed_modifications))
            
        except Exception as e:
            logger.error("JAR修改失败", jar_path=jar_path, error=str(e))
            
            # 清理临时文件
            temp_jar_path = f"{jar_path}.tmp"
            Path(temp_jar_path).unlink(missing_ok=True)
            
            # 尝试恢复
            if result.backup_path:
                try:
                    await self.backup_manager.restore_from_backup(jar_path, result.backup_path)
                except Exception:
                    pass  # 恢复失败，但不影响主要错误
            
            result.fail(str(e))
        
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    async def update_language_file(
        self,
        jar_path: str,
        language: str,
        mod_id: str,
        translations: Dict[str, str],
        backup_policy: BackupPolicy = BackupPolicy.ALWAYS
    ) -> JarModificationResult:
        """更新JAR中的语言文件"""
        # 构建语言文件路径
        lang_file_path = f"assets/{mod_id}/lang/{language}.json"
        
        # 创建修改
        modification = JarModification(
            type=ModificationType.UPDATE_FILE,
            path=lang_file_path,
            content=json.dumps(translations, ensure_ascii=False, indent=2).encode('utf-8'),
            metadata={
                "language": language,
                "mod_id": mod_id,
                "translation_count": len(translations)
            }
        )
        
        return await self.safe_jar_modification(
            jar_path,
            [modification],
            backup_policy
        )
    
    # 私有方法实现
    async def _extract_fabric_info(self, jar: zipfile.ZipFile, jar_path: Path) -> ModInfo:
        """提取Fabric MOD信息"""
        try:
            with jar.open("fabric.mod.json") as f:
                data = json.load(f)
                
                authors = data.get("authors", [])
                if isinstance(authors, list):
                    authors = [str(a) if not isinstance(a, dict) else a.get("name", str(a)) for a in authors]
                
                return ModInfo(
                    id=data.get("id", jar_path.stem),
                    name=data.get("name", data.get("id", jar_path.stem)),
                    version=data.get("version", "unknown"),
                    description=data.get("description", ""),
                    loader_type=ModLoaderType.FABRIC,
                    jar_path=str(jar_path),
                    authors=authors,
                    minecraft_version=self._extract_fabric_mc_version(data),
                    metadata=data
                )
        except Exception as e:
            logger.error("解析fabric.mod.json失败", error=str(e))
            return self._extract_fallback_info(jar_path)
    
    async def _extract_quilt_info(self, jar: zipfile.ZipFile, jar_path: Path) -> ModInfo:
        """提取Quilt MOD信息"""
        try:
            with jar.open("quilt.mod.json") as f:
                data = json.load(f)
                
                quilt_loader = data.get("quilt_loader", {})
                metadata = quilt_loader.get("metadata", {})
                
                return ModInfo(
                    id=quilt_loader.get("id", jar_path.stem),
                    name=metadata.get("name", jar_path.stem),
                    version=quilt_loader.get("version", "unknown"),
                    description=metadata.get("description", ""),
                    loader_type=ModLoaderType.QUILT,
                    jar_path=str(jar_path),
                    authors=list(metadata.get("contributors", {}).keys()),
                    minecraft_version=self._extract_quilt_mc_version(data),
                    metadata=data
                )
        except Exception as e:
            logger.error("解析quilt.mod.json失败", error=str(e))
            return self._extract_fallback_info(jar_path)
    
    async def _extract_forge_info(self, jar: zipfile.ZipFile, jar_path: Path) -> ModInfo:
        """提取Forge MOD信息（现代版本）"""
        try:
            with jar.open("META-INF/mods.toml") as f:
                content = f.read().decode('utf-8')
                
            mod_info = self._parse_simple_toml(content)
            
            return ModInfo(
                id=mod_info.get("modId", jar_path.stem),
                name=mod_info.get("displayName", jar_path.stem),
                version=self._resolve_template_variables(
                    mod_info.get("version", "unknown"), str(jar_path)
                ),
                description=mod_info.get("description", ""),
                loader_type=ModLoaderType.FORGE,
                jar_path=str(jar_path),
                authors=[mod_info.get("authors", "")],
                metadata=mod_info
            )
        except Exception as e:
            logger.error("解析mods.toml失败", error=str(e))
            return self._extract_fallback_info(jar_path)
    
    async def _extract_legacy_forge_info(self, jar: zipfile.ZipFile, jar_path: Path) -> ModInfo:
        """提取Forge MOD信息（传统版本）"""
        try:
            with jar.open("mcmod.info") as f:
                data = json.load(f)
                
            if isinstance(data, list) and data:
                mod_data = data[0]
                
                authors = mod_data.get("authorList", [])
                if not authors:
                    authors = [mod_data.get("authors", "")]
                
                return ModInfo(
                    id=mod_data.get("modid", jar_path.stem),
                    name=mod_data.get("name", jar_path.stem),
                    version=mod_data.get("version", "unknown"),
                    description=mod_data.get("description", ""),
                    loader_type=ModLoaderType.FORGE,
                    jar_path=str(jar_path),
                    authors=authors,
                    minecraft_version=mod_data.get("mcversion"),
                    metadata=mod_data
                )
        except Exception as e:
            logger.error("解析mcmod.info失败", error=str(e))
            
        return self._extract_fallback_info(jar_path)
    
    def _extract_fallback_info(self, jar_path: Path) -> ModInfo:
        """从文件名提取MOD信息（回退方案）"""
        filename = jar_path.stem
        
        # 尝试分离名称和版本
        parts = filename.split('-')
        if len(parts) >= 2:
            name = parts[0]
            version = '-'.join(parts[1:])
        else:
            name = filename
            version = "unknown"
        
        return ModInfo(
            id=name.lower().replace(' ', '_'),
            name=name,
            version=version,
            loader_type=ModLoaderType.UNKNOWN,
            jar_path=str(jar_path)
        )
    
    async def _pre_modification_check(
        self, 
        jar_path: str, 
        modifications: List[JarModification]
    ) -> bool:
        """预修改检查"""
        jar_file = Path(jar_path)
        
        if not jar_file.exists():
            logger.error("JAR文件不存在", jar_path=jar_path)
            return False
        
        if not os.access(jar_path, os.R_OK | os.W_OK):
            logger.error("JAR文件权限不足", jar_path=jar_path)
            return False
        
        if not modifications:
            logger.warning("没有要执行的修改", jar_path=jar_path)
            return False
        
        return True
    
    async def _apply_modifications_to_new_jar(
        self,
        source_jar: str,
        dest_jar: str,
        modifications: List[JarModification],
        result: JarModificationResult
    ):
        """将修改应用到新JAR文件"""
        modification_map = {mod.path: mod for mod in modifications}
        
        with zipfile.ZipFile(source_jar, 'r') as source:
            with zipfile.ZipFile(dest_jar, 'w', zipfile.ZIP_DEFLATED) as dest:
                # 复制现有文件（可能包含修改）
                for item in source.infolist():
                    if item.filename in modification_map:
                        mod = modification_map[item.filename]
                        
                        if mod.type == ModificationType.UPDATE_FILE:
                            try:
                                mod.original_content = source.read(item.filename)
                                dest.writestr(item, mod.content)
                                result.add_successful_modification(mod)
                                logger.debug("文件已更新", path=mod.path)
                                
                            except Exception as e:
                                result.add_failed_modification(mod, str(e))
                                dest.writestr(item, source.read(item.filename))
                        
                        elif mod.type == ModificationType.DELETE_FILE:
                            # 跳过此文件（即删除）
                            result.add_successful_modification(mod)
                            logger.debug("文件已删除", path=mod.path)
                    else:
                        # 复制原文件
                        dest.writestr(item, source.read(item.filename))
                
                # 添加新文件
                for mod in modifications:
                    if mod.type == ModificationType.ADD_FILE:
                        try:
                            dest.writestr(mod.path, mod.content)
                            result.add_successful_modification(mod)
                            logger.debug("文件已添加", path=mod.path)
                        except Exception as e:
                            result.add_failed_modification(mod, str(e))
    
    def _is_language_file(self, file_path: str) -> bool:
        """判断是否为语言文件"""
        return (
            '/lang/' in file_path and 
            (file_path.endswith('.json') or file_path.endswith('.lang'))
        )
    
    async def _extract_language_file(
        self, 
        jar: zipfile.ZipFile, 
        file_info: zipfile.ZipInfo, 
        mod_id: str
    ) -> Optional[LanguageFile]:
        """提取单个语言文件"""
        try:
            file_path = file_info.filename
            language = self._extract_language_code(file_path)
            
            if not language:
                return None
            
            content = jar.read(file_info).decode('utf-8')
            translations = {}
            format_type = "json" if file_path.endswith('.json') else "lang"
            
            if format_type == "json":
                try:
                    translations = json.loads(content)
                    if not isinstance(translations, dict):
                        logger.warning("JSON语言文件格式错误", file_path=file_path)
                        return None
                except json.JSONDecodeError as e:
                    logger.warning("JSON解析失败", file_path=file_path, error=str(e))
                    return None
            
            elif format_type == "lang":
                for line in content.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        translations[key.strip()] = value.strip()
            
            return LanguageFile(
                mod_id=mod_id,
                language=language,
                file_path=file_path,
                format=format_type,
                translations=translations
            )
            
        except Exception as e:
            logger.error("提取语言文件失败", file_path=file_info.filename, error=str(e))
            return None
    
    async def _calculate_jar_hash(self, jar_path: str) -> str:
        """计算JAR文件哈希"""
        hasher = hashlib.blake2b()
        
        try:
            with open(jar_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    hasher.update(chunk)
            
            return hasher.hexdigest()
        except Exception as e:
            logger.error("哈希计算失败", jar_path=jar_path, error=str(e))
            return ""
    
    # 辅助方法
    def _extract_language_code(self, file_path: str) -> Optional[str]:
        """从文件路径提取语言代码"""
        import re
        match = re.search(r'/lang/([^/]+)\.(json|lang)$', file_path)
        return match.group(1) if match else None
    
    def _extract_fabric_mc_version(self, data: dict) -> Optional[str]:
        """提取Fabric的Minecraft版本"""
        depends = data.get("depends", {})
        minecraft = depends.get("minecraft", "")
        
        if minecraft:
            # 清理版本号
            minecraft = minecraft.replace(">=", "").replace("~", "").replace("^", "")
        
        return minecraft if minecraft else None
    
    def _extract_quilt_mc_version(self, data: dict) -> Optional[str]:
        """提取Quilt的Minecraft版本"""
        quilt_loader = data.get("quilt_loader", {})
        depends = quilt_loader.get("depends", [])
        
        for dep in depends:
            if dep.get("id") == "minecraft":
                versions = dep.get("versions", "")
                if isinstance(versions, str):
                    return versions.replace(">=", "").replace("~", "")
        
        return None
    
    def _parse_simple_toml(self, content: str) -> Dict[str, str]:
        """简单的TOML解析器"""
        result = {}
        in_mods_section = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            if line == '[[mods]]':
                in_mods_section = True
                continue
            
            if line.startswith('[') and line != '[[mods]]':
                in_mods_section = False
                continue
            
            if in_mods_section and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                result[key] = value
        
        return result
    
    def _resolve_template_variables(self, template_str: str, file_path: str) -> str:
        """解析模板变量"""
        if not isinstance(template_str, str):
            return str(template_str)
        
        result = template_str
        
        # 解析 ${file.jarVersion}
        if "${file.jarVersion}" in result:
            version = self._extract_version_from_filename(file_path)
            result = result.replace("${file.jarVersion}", version)
        
        return result
    
    def _extract_version_from_filename(self, filename: str) -> str:
        """从文件名中提取版本号"""
        import re
        name = Path(filename).stem
        
        version_patterns = [
            r"-mc\d+(?:\.\d+)*-(\d+(?:\.\d+)*)",
            r"-\d+(?:\.\d+)*-(\d+(?:\.\d+)*)",
            r"[_-]v(\d+(?:\.\d+)*(?:[.-](?:alpha|beta|rc|snapshot|SNAPSHOT)\d*)?)",
            r"-(\d+(?:\.\d+)*(?:[.-](?:alpha|beta|rc|snapshot|SNAPSHOT)\d*)?)$",
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "unknown"


# ==================== 工厂函数和便捷函数 ====================

def create_jar_processor() -> AdvancedJarProcessor:
    """创建JAR处理器"""
    return AdvancedJarProcessor()


async def quick_language_update(
    jar_path: str,
    language: str,
    mod_id: str,
    translations: Dict[str, str]
) -> JarModificationResult:
    """快速更新语言文件"""
    processor = create_jar_processor()
    return await processor.update_language_file(
        jar_path, language, mod_id, translations
    )


async def extract_all_languages(jar_path: str) -> Dict[str, Dict[str, str]]:
    """提取所有语言文件"""
    processor = create_jar_processor()
    jar_path_obj = Path(jar_path)
    
    language_files = await processor.extract_language_files(jar_path_obj)
    
    result = {}
    for lang_file in language_files:
        if lang_file.language not in result:
            result[lang_file.language] = {}
        result[lang_file.language].update(lang_file.translations)
    
    return result


# ==================== 全局处理器实例 ====================

_jar_processor: Optional[AdvancedJarProcessor] = None


def get_jar_processor() -> AdvancedJarProcessor:
    """获取JAR处理器实例（单例模式）"""
    global _jar_processor
    if _jar_processor is None:
        _jar_processor = AdvancedJarProcessor()
    return _jar_processor