"""
MC L10n UIDA服务层
基于Trans-Hub UIDA包的Minecraft本地化专用标识符服务
"""
import sys
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import structlog

# 添加UIDA包路径
# 从 /home/saken/project/TH-Suite/apps/mc_l10n/backend/services/ 到 /home/saken/project/Trans-Hub/packages/uida/src
uida_package_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../Trans-Hub/packages/uida/src'))
if os.path.exists(uida_package_path):
    sys.path.insert(0, uida_package_path)
else:
    print(f"警告: UIDA包路径不存在: {uida_package_path}")
    # 备选路径
    alt_paths = [
        '/home/saken/project/Trans-Hub/packages/uida/src',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '../packages/uida/src'))
    ]
    for alt_path in alt_paths:
        if os.path.exists(alt_path):
            sys.path.insert(0, alt_path)
            print(f"使用备选UIDA路径: {alt_path}")
            break
    else:
        print("警告: 所有UIDA包路径都不存在")

try:
    from trans_hub_uida import generate_uida, UIDAComponents, CanonicalizationError
except ImportError as e:
    raise ImportError(f"无法导入UIDA包，请确保已正确安装: {e}")

logger = structlog.get_logger(__name__)


@dataclass
class MCUIDANamespace:
    """MC L10n UIDA命名空间定义"""
    
    # MOD相关命名空间
    MOD_ITEM = "mc.mod.item"
    MOD_BLOCK = "mc.mod.block"  
    MOD_ENTITY = "mc.mod.entity"
    MOD_GUI = "mc.mod.gui"
    MOD_RECIPE = "mc.mod.recipe"
    MOD_ADVANCEMENT = "mc.mod.advancement"
    
    # 资源包相关
    RESOURCEPACK_LANG = "mc.resourcepack.lang"
    RESOURCEPACK_TEXTURE = "mc.resourcepack.texture"
    RESOURCEPACK_MODEL = "mc.resourcepack.model"
    
    # 数据包相关
    DATAPACK_RECIPE = "mc.datapack.recipe"
    DATAPACK_ADVANCEMENT = "mc.datapack.advancement"
    DATAPACK_LOOT_TABLE = "mc.datapack.loot_table"
    
    # 原版Minecraft
    VANILLA_LANG = "mc.vanilla.lang"
    VANILLA_ITEM = "mc.vanilla.item"
    VANILLA_BLOCK = "mc.vanilla.block"


# 命名空间模式定义
NAMESPACE_PATTERNS: Dict[str, set] = {
    # MOD相关
    MCUIDANamespace.MOD_ITEM: {"mod_id", "item_id", "variant"},
    MCUIDANamespace.MOD_BLOCK: {"mod_id", "block_id", "variant"},
    MCUIDANamespace.MOD_ENTITY: {"mod_id", "entity_id", "type"},
    MCUIDANamespace.MOD_GUI: {"mod_id", "gui_id", "element"},
    MCUIDANamespace.MOD_RECIPE: {"mod_id", "recipe_id", "type"},
    MCUIDANamespace.MOD_ADVANCEMENT: {"mod_id", "advancement_id"},
    
    # 资源包相关
    MCUIDANamespace.RESOURCEPACK_LANG: {"pack_id", "locale", "key"},
    MCUIDANamespace.RESOURCEPACK_TEXTURE: {"pack_id", "texture_path"},
    MCUIDANamespace.RESOURCEPACK_MODEL: {"pack_id", "model_path"},
    
    # 数据包相关
    MCUIDANamespace.DATAPACK_RECIPE: {"pack_id", "recipe_id"},
    MCUIDANamespace.DATAPACK_ADVANCEMENT: {"pack_id", "advancement_id"},
    MCUIDANamespace.DATAPACK_LOOT_TABLE: {"pack_id", "loot_table_id"},
    
    # 原版Minecraft
    MCUIDANamespace.VANILLA_LANG: {"key", "locale"},
    MCUIDANamespace.VANILLA_ITEM: {"item_id"},
    MCUIDANamespace.VANILLA_BLOCK: {"block_id"},
}


class MCUIDAService:
    """MC L10n UIDA服务"""
    
    def __init__(self):
        self.namespace_patterns = NAMESPACE_PATTERNS
        
    def generate_translation_entry_uida(
        self, 
        mod_id: str,
        translation_key: str, 
        locale: str,
        carrier_type: str = "mod",
        item_type: Optional[str] = None
    ) -> UIDAComponents:
        """
        为翻译条目生成UIDA
        
        Args:
            mod_id: MOD标识符
            translation_key: 翻译键 (如 "item.create.brass_ingot")
            locale: 语言区域 (如 "zh_cn")
            carrier_type: 载体类型 (mod/resource_pack/data_pack)
            item_type: 具体项目类型 (item/block/entity等)
            
        Returns:
            UIDAComponents: UIDA组件
        """
        # 解析翻译键以确定类型和ID
        key_parts = translation_key.split('.')
        
        if len(key_parts) >= 3 and carrier_type == "mod":
            # 标准MOD翻译键格式: type.mod_id.item_id
            detected_type = key_parts[0]  # item, block, entity等
            detected_mod_id = key_parts[1]
            item_id = '.'.join(key_parts[2:])  # 支持复杂的item_id
            
            # 确定命名空间
            if detected_type == "item":
                namespace = MCUIDANamespace.MOD_ITEM
            elif detected_type == "block":
                namespace = MCUIDANamespace.MOD_BLOCK
            elif detected_type in ["entity", "entitytype"]:
                namespace = MCUIDANamespace.MOD_ENTITY
            elif detected_type in ["gui", "screen", "container"]:
                namespace = MCUIDANamespace.MOD_GUI
            else:
                # 默认使用item命名空间
                namespace = MCUIDANamespace.MOD_ITEM
            
            keys = {
                "mod_id": detected_mod_id or mod_id,
                f"{detected_type}_id": item_id,
                "locale": locale
            }
            
            # 添加变体信息（如果提供）
            if item_type:
                keys["variant"] = item_type
        else:
            # 简化处理或自定义格式
            namespace = MCUIDANamespace.MOD_ITEM
            keys = {
                "mod_id": mod_id,
                "item_id": translation_key,
                "locale": locale
            }
        
        return self.generate_uida(namespace, keys)
    
    def generate_language_file_uida(
        self,
        carrier_type: str,
        carrier_uid: str, 
        locale: str,
        file_path: Optional[str] = None
    ) -> UIDAComponents:
        """
        为语言文件生成UIDA
        
        Args:
            carrier_type: 载体类型 (mod/resource_pack/data_pack)
            carrier_uid: 载体唯一标识符
            locale: 语言区域
            file_path: 文件路径（可选）
            
        Returns:
            UIDAComponents: UIDA组件
        """
        if carrier_type == "mod":
            namespace = MCUIDANamespace.RESOURCEPACK_LANG
        elif carrier_type == "resource_pack":
            namespace = MCUIDANamespace.RESOURCEPACK_LANG
        elif carrier_type == "data_pack":
            namespace = MCUIDANamespace.DATAPACK_RECIPE  # 简化处理
        else:
            namespace = MCUIDANamespace.RESOURCEPACK_LANG
        
        keys = {
            "carrier_type": carrier_type,
            "carrier_uid": carrier_uid,
            "locale": locale
        }
        
        if file_path:
            keys["file_path"] = file_path
        
        return self.generate_uida(namespace, keys)
    
    def generate_uida(self, namespace: str, keys: Dict[str, Any]) -> UIDAComponents:
        """
        生成UIDA (通用方法)
        
        Args:
            namespace: 命名空间
            keys: 标识键字典
            
        Returns:
            UIDAComponents: UIDA组件
            
        Raises:
            ValueError: 当命名空间或键不符合规范时
            CanonicalizationError: 当键不符合I-JSON规范时
        """
        # 验证命名空间
        if namespace not in self.namespace_patterns:
            logger.warning(f"未知的命名空间: {namespace}")
        
        # 验证键模式（如果有定义）
        if namespace in self.namespace_patterns:
            required_keys = self.namespace_patterns[namespace]
            provided_keys = set(keys.keys())
            
            # 检查必需键（允许额外键）
            if not required_keys.issubset(provided_keys):
                missing_keys = required_keys - provided_keys
                logger.warning(f"命名空间 {namespace} 缺少必需键: {missing_keys}")
        
        # 添加命名空间到keys中
        full_keys = {
            "namespace": namespace,
            **keys
        }
        
        try:
            uida_components = generate_uida(full_keys)
            
            # 创建扩展的UIDA组件包装器，添加十六进制哈希字段
            class ExtendedUIDAComponents:
                def __init__(self, components: UIDAComponents):
                    # 直接使用底层UIDA包的属性（已迁移到BLAKE3）
                    self.keys_b64 = components.keys_b64
                    self.keys_hash_bytes = components.keys_hash_bytes
                    self.canonical_bytes = components.canonical_bytes
                    # 添加十六进制格式的哈希，用于数据库存储
                    self.hash_hex = components.keys_hash_bytes.hex()
            
            return ExtendedUIDAComponents(uida_components)
            
        except CanonicalizationError as e:
            logger.error(f"UIDA生成失败: {e}")
            raise ValueError(f"无法为给定键生成UIDA: {e}")
    
    def find_similar_entries_by_uida(
        self,
        reference_uida: UIDAComponents,
        similarity_threshold: float = 0.8
    ) -> List[str]:
        """
        基于UIDA查找相似翻译条目
        
        Args:
            reference_uida: 参考UIDA
            similarity_threshold: 相似度阈值
            
        Returns:
            相似条目的UID列表
        """
        # TODO: 实现相似性查询逻辑
        # 这里应该查询数据库中相似的UIDA
        logger.info(f"查找相似条目，参考UIDA: {reference_uida.keys_b64[:16]}...")
        return []
    
    def validate_namespace(self, namespace: str) -> bool:
        """验证命名空间是否有效"""
        return namespace in self.namespace_patterns
    
    def get_namespace_pattern(self, namespace: str) -> Optional[set]:
        """获取命名空间的键模式"""
        return self.namespace_patterns.get(namespace)
    
    def get_all_namespaces(self) -> List[str]:
        """获取所有支持的命名空间"""
        return list(self.namespace_patterns.keys())


# 全局UIDA服务实例
_uida_service: Optional[MCUIDAService] = None


def get_uida_service() -> MCUIDAService:
    """获取UIDA服务实例（单例模式）"""
    global _uida_service
    if _uida_service is None:
        _uida_service = MCUIDAService()
        logger.info("UIDA服务初始化完成")
    return _uida_service


# 便捷函数
def generate_mod_translation_uida(
    mod_id: str, 
    translation_key: str, 
    locale: str
) -> UIDAComponents:
    """快速为MOD翻译生成UIDA"""
    service = get_uida_service()
    return service.generate_translation_entry_uida(mod_id, translation_key, locale)