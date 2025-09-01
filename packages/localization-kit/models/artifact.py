"""
Artifact 数据模型 - 物理载体

根据白皮书定义：
- Artifact 是物理载体（JAR文件、目录、资源包、数据包）
- 一个 Artifact 可以包含多个 Container
- 支持的类型：mod_jar, modpack_dir, resource_pack, data_pack
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import hashlib


class ArtifactType(Enum):
    """Artifact 类型枚举"""
    MOD_JAR = "mod_jar"           # 单独的 MOD JAR 文件
    MODPACK_DIR = "modpack_dir"   # 组合包目录
    RESOURCE_PACK = "resource_pack" # 资源包
    DATA_PACK = "data_pack"       # 数据包
    
    @classmethod
    def from_path(cls, path: Path) -> Optional['ArtifactType']:
        """从路径推断 Artifact 类型"""
        if path.is_file():
            if path.suffix.lower() == '.jar':
                return cls.MOD_JAR
            elif path.suffix.lower() == '.zip':
                # 需要进一步检查是资源包还是数据包
                return cls.RESOURCE_PACK
        elif path.is_dir():
            # 检查是否为组合包目录
            modpack_indicators = [
                "manifest.json",      # CurseForge
                "modrinth.index.json", # Modrinth
                "instance.cfg",       # MultiMC
                "mmc-pack.json"       # MultiMC新格式
            ]
            for indicator in modpack_indicators:
                if (path / indicator).exists():
                    return cls.MODPACK_DIR
            
            # 检查是否为资源包
            if (path / "pack.mcmeta").exists():
                return cls.RESOURCE_PACK
                
        return None


@dataclass
class Artifact:
    """
    Artifact 实体 - 物理载体
    
    对应数据库表: artifacts
    """
    artifact_id: str
    artifact_type: ArtifactType
    path: Path
    content_hash: str
    size: int
    first_seen: datetime
    last_seen: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时属性
    containers: List['Container'] = field(default_factory=list)
    
    def __post_init__(self):
        """确保路径为 Path 对象"""
        if isinstance(self.path, str):
            self.path = Path(self.path)
    
    @classmethod
    def from_path(cls, path: Path, artifact_id: Optional[str] = None) -> 'Artifact':
        """从文件路径创建 Artifact"""
        import uuid
        
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        # 推断类型
        artifact_type = ArtifactType.from_path(path)
        if not artifact_type:
            raise ValueError(f"Cannot determine artifact type for: {path}")
        
        # 计算内容哈希
        if path.is_file():
            content_hash = cls._calculate_file_hash(path)
            size = path.stat().st_size
        else:
            content_hash = cls._calculate_dir_hash(path)
            size = cls._calculate_dir_size(path)
        
        now = datetime.now()
        
        return cls(
            artifact_id=artifact_id or str(uuid.uuid4()),
            artifact_type=artifact_type,
            path=path,
            content_hash=content_hash,
            size=size,
            first_seen=now,
            last_seen=now
        )
    
    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """计算文件的 SHA256 哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    @staticmethod
    def _calculate_dir_hash(dir_path: Path) -> str:
        """计算目录的内容哈希（基于目录结构和文件列表）"""
        sha256 = hashlib.sha256()
        
        # 收集所有文件路径并排序
        files = []
        for item in dir_path.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(dir_path)
                files.append(str(relative_path).replace('\\', '/'))
        
        # 基于排序后的文件列表计算哈希
        files.sort()
        for file_path in files:
            sha256.update(file_path.encode('utf-8'))
            
        return sha256.hexdigest()
    
    @staticmethod
    def _calculate_dir_size(dir_path: Path) -> int:
        """计算目录总大小"""
        total_size = 0
        for item in dir_path.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
        return total_size
    
    def update_metadata(self, key: str, value: Any) -> None:
        """更新元数据"""
        self.metadata[key] = value
        self.last_seen = datetime.now()
    
    def add_container(self, container: 'Container') -> None:
        """添加 Container"""
        if container not in self.containers:
            self.containers.append(container)
            container.artifact = self
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'artifact_id': self.artifact_id,
            'artifact_type': self.artifact_type.value,
            'path': str(self.path),
            'content_hash': self.content_hash,
            'size': self.size,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'metadata': self.metadata,
            'container_count': len(self.containers)
        }