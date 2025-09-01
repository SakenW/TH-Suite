"""
回写策略 - 将补丁应用到文件系统

根据白皮书定义的策略：
1. Overlay（默认）- 生成资源包
2. JAR 就地修改 - 直接修改 JAR 文件
3. 任务包/数据包 - 写入配置文件
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
import json
import zipfile
import tempfile
import shutil
import logging
from datetime import datetime

from ..models import PatchItem, PatchPolicy

logger = logging.getLogger(__name__)


@dataclass
class WritebackResult:
    """回写结果"""
    success: bool
    patch_item_id: str
    strategy: str
    target_path: str
    before_hash: Optional[str] = None
    after_hash: Optional[str] = None
    error_message: Optional[str] = None
    backup_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WritebackStrategy(ABC):
    """回写策略基类"""
    
    @abstractmethod
    def apply(
        self,
        patch_item: PatchItem,
        target_path: Path,
        **kwargs
    ) -> WritebackResult:
        """
        应用补丁
        
        Args:
            patch_item: 补丁项
            target_path: 目标路径
            **kwargs: 额外参数
            
        Returns:
            回写结果
        """
        pass
    
    @abstractmethod
    def rollback(self, result: WritebackResult) -> bool:
        """
        回滚操作
        
        Args:
            result: 回写结果
            
        Returns:
            是否成功回滚
        """
        pass
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        import hashlib
        
        if not file_path.exists():
            return ""
        
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()


class OverlayStrategy(WritebackStrategy):
    """
    Overlay 策略 - 生成资源包
    
    优点：
    - 安全，不修改原文件
    - 易于切换和回滚
    - 符合 Minecraft 标准
    """
    
    def __init__(self, resource_pack_dir: Path):
        """
        初始化 Overlay 策略
        
        Args:
            resource_pack_dir: 资源包输出目录
        """
        self.resource_pack_dir = resource_pack_dir
        self.resource_pack_dir.mkdir(parents=True, exist_ok=True)
    
    def apply(
        self,
        patch_item: PatchItem,
        target_path: Path,
        pack_name: str = "localization_overlay",
        pack_format: int = 15,  # MC 1.20.x
        **kwargs
    ) -> WritebackResult:
        """应用 Overlay 补丁"""
        
        result = WritebackResult(
            success=False,
            patch_item_id=patch_item.patch_item_id,
            strategy="overlay",
            target_path=str(target_path)
        )
        
        try:
            # 创建资源包目录结构
            pack_dir = self.resource_pack_dir / pack_name
            pack_dir.mkdir(exist_ok=True)
            
            # 创建 pack.mcmeta
            pack_meta = {
                "pack": {
                    "pack_format": pack_format,
                    "description": f"Localization overlay for {patch_item.namespace}"
                }
            }
            
            meta_path = pack_dir / "pack.mcmeta"
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(pack_meta, f, indent=2, ensure_ascii=False)
            
            # 创建语言文件路径
            lang_dir = pack_dir / "assets" / patch_item.namespace / "lang"
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            lang_file = lang_dir / f"{patch_item.locale}.json"
            
            # 记录原始哈希
            if lang_file.exists():
                result.before_hash = self.calculate_file_hash(lang_file)
            
            # 处理内容
            if patch_item.policy == PatchPolicy.MERGE and lang_file.exists():
                # 合并模式：与现有内容合并
                with open(lang_file, 'r', encoding='utf-8') as f:
                    existing_content = json.load(f)
                
                merged_content = {**existing_content, **patch_item.content}
                final_content = merged_content
            else:
                # 覆盖或创建
                final_content = patch_item.content
            
            # 写入文件
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(final_content, f, indent=2, ensure_ascii=False)
            
            # 计算新哈希
            result.after_hash = self.calculate_file_hash(lang_file)
            
            # 验证哈希（如果有期望值）
            if patch_item.expected_blob_hash:
                # 计算内容哈希
                import hashlib
                canonical_json = json.dumps(final_content, sort_keys=True, ensure_ascii=False)
                content_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
                
                if content_hash != patch_item.expected_blob_hash:
                    logger.warning(
                        f"哈希不匹配: 期望 {patch_item.expected_blob_hash[:8]}..., "
                        f"实际 {content_hash[:8]}..."
                    )
            
            result.success = True
            result.target_path = str(lang_file)
            result.metadata['pack_dir'] = str(pack_dir)
            
            logger.info(f"Overlay 补丁已应用: {lang_file}")
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Overlay 补丁应用失败: {e}")
        
        return result
    
    def rollback(self, result: WritebackResult) -> bool:
        """回滚 Overlay 操作"""
        try:
            # Overlay 的回滚很简单：删除生成的文件
            target_file = Path(result.target_path)
            if target_file.exists():
                target_file.unlink()
                logger.info(f"Overlay 已回滚: {target_file}")
            
            # 如果目录为空，删除目录
            lang_dir = target_file.parent
            if lang_dir.exists() and not any(lang_dir.iterdir()):
                lang_dir.rmdir()
            
            return True
            
        except Exception as e:
            logger.error(f"Overlay 回滚失败: {e}")
            return False


class JarModifyStrategy(WritebackStrategy):
    """
    JAR 修改策略 - 直接修改 JAR 文件
    
    注意：
    - 需要备份原始文件
    - 可能影响 MOD 签名
    - 需要谨慎使用
    """
    
    def __init__(self, backup_dir: Path):
        """
        初始化 JAR 修改策略
        
        Args:
            backup_dir: 备份目录
        """
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def apply(
        self,
        patch_item: PatchItem,
        target_path: Path,
        **kwargs
    ) -> WritebackResult:
        """应用 JAR 修改补丁"""
        
        result = WritebackResult(
            success=False,
            patch_item_id=patch_item.patch_item_id,
            strategy="jar_modify",
            target_path=str(target_path)
        )
        
        if not target_path.exists() or not zipfile.is_zipfile(target_path):
            result.error_message = "目标不是有效的 JAR 文件"
            return result
        
        try:
            # 创建备份
            backup_name = f"{target_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jar"
            backup_path = self.backup_dir / backup_name
            shutil.copy2(target_path, backup_path)
            result.backup_path = str(backup_path)
            
            # 计算原始哈希
            result.before_hash = self.calculate_file_hash(target_path)
            
            # 确定 JAR 内的目标路径
            member_path = patch_item.get_target_path()
            
            # 读取现有内容（如果需要合并）
            existing_content = {}
            with zipfile.ZipFile(target_path, 'r') as jar:
                if member_path in jar.namelist():
                    with jar.open(member_path) as f:
                        try:
                            existing_content = json.load(f)
                        except json.JSONDecodeError:
                            pass
            
            # 处理内容
            if patch_item.policy == PatchPolicy.MERGE and existing_content:
                final_content = {**existing_content, **patch_item.content}
            else:
                final_content = patch_item.content
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jar') as tmp_file:
                tmp_path = Path(tmp_file.name)
            
            # 复制 JAR 内容，替换或添加目标文件
            with zipfile.ZipFile(target_path, 'r') as src_jar:
                with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as dst_jar:
                    # 复制所有文件，除了要更新的文件
                    for item in src_jar.namelist():
                        if item != member_path:
                            dst_jar.writestr(item, src_jar.read(item))
                    
                    # 添加或更新语言文件
                    json_content = json.dumps(final_content, indent=2, ensure_ascii=False)
                    dst_jar.writestr(member_path, json_content.encode('utf-8'))
            
            # 替换原文件
            shutil.move(str(tmp_path), str(target_path))
            
            # 计算新哈希
            result.after_hash = self.calculate_file_hash(target_path)
            
            result.success = True
            result.metadata['member_path'] = member_path
            result.metadata['entry_count'] = len(final_content)
            
            logger.info(f"JAR 补丁已应用: {target_path} -> {member_path}")
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"JAR 补丁应用失败: {e}")
            
            # 尝试恢复备份
            if result.backup_path and Path(result.backup_path).exists():
                try:
                    shutil.copy2(result.backup_path, target_path)
                    logger.info("已从备份恢复")
                except Exception as restore_error:
                    logger.error(f"恢复备份失败: {restore_error}")
        
        return result
    
    def rollback(self, result: WritebackResult) -> bool:
        """回滚 JAR 修改"""
        try:
            if not result.backup_path:
                logger.error("没有备份文件，无法回滚")
                return False
            
            backup_path = Path(result.backup_path)
            target_path = Path(result.target_path)
            
            if not backup_path.exists():
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 恢复备份
            shutil.copy2(backup_path, target_path)
            
            logger.info(f"JAR 修改已回滚: {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"JAR 回滚失败: {e}")
            return False


class DirectoryWriteStrategy(WritebackStrategy):
    """
    目录写入策略 - 直接写入目录中的文件
    
    用于：
    - 解压的模组
    - 开发环境
    - 数据包/任务包
    """
    
    def apply(
        self,
        patch_item: PatchItem,
        target_path: Path,
        **kwargs
    ) -> WritebackResult:
        """应用目录写入补丁"""
        
        result = WritebackResult(
            success=False,
            patch_item_id=patch_item.patch_item_id,
            strategy="directory_write",
            target_path=str(target_path)
        )
        
        if not target_path.is_dir():
            result.error_message = "目标不是目录"
            return result
        
        try:
            # 确定目标文件路径
            relative_path = patch_item.get_target_path()
            target_file = target_path / relative_path
            
            # 创建目录
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 记录原始哈希
            if target_file.exists():
                result.before_hash = self.calculate_file_hash(target_file)
                
                # 创建备份
                backup_file = target_file.with_suffix(target_file.suffix + '.bak')
                shutil.copy2(target_file, backup_file)
                result.backup_path = str(backup_file)
            
            # 处理内容
            if patch_item.policy == PatchPolicy.MERGE and target_file.exists():
                with open(target_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_content = json.load(f)
                    except json.JSONDecodeError:
                        existing_content = {}
                
                final_content = {**existing_content, **patch_item.content}
            else:
                final_content = patch_item.content
            
            # 写入文件
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(final_content, f, indent=2, ensure_ascii=False)
            
            # 计算新哈希
            result.after_hash = self.calculate_file_hash(target_file)
            
            result.success = True
            result.target_path = str(target_file)
            
            logger.info(f"目录补丁已应用: {target_file}")
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"目录补丁应用失败: {e}")
        
        return result
    
    def rollback(self, result: WritebackResult) -> bool:
        """回滚目录写入"""
        try:
            target_file = Path(result.target_path)
            
            if result.backup_path:
                # 从备份恢复
                backup_file = Path(result.backup_path)
                if backup_file.exists():
                    shutil.copy2(backup_file, target_file)
                    backup_file.unlink()  # 删除备份
                    logger.info(f"目录写入已回滚: {target_file}")
                    return True
            else:
                # 没有备份，删除文件
                if target_file.exists():
                    target_file.unlink()
                    logger.info(f"文件已删除: {target_file}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"目录回滚失败: {e}")
            return False