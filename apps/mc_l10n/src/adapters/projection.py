"""
Minecraft投影适配器
基于升级方案的投影规范系统，实现Minecraft数据与Trans-Hub Core的双向转换
"""

import yaml
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class UIDA:
    """统一标识符和地址"""
    namespace: str
    project_id: str
    keys: Tuple[str, ...]
    
    def identity_hash(self) -> str:
        """生成身份哈希"""
        import hashlib
        content = f"{self.namespace}:{self.project_id}:{':'.join(self.keys)}"
        return hashlib.blake2b(content.encode(), digest_size=32).hexdigest()
    
    def to_uri(self) -> str:
        """转换为UIDA URI格式"""
        keys_str = '/'.join(self.keys)
        return f"uida://{self.namespace}/{self.project_id}/{keys_str}"
    
    def __str__(self) -> str:
        return self.to_uri()


@dataclass
class ProjectionSpec:
    """投影规范配置"""
    version: int
    app: str
    namespace: str
    project_id_expr: str
    key_exprs: List[str]
    context_exprs: Dict[str, str]
    stabilizers: List[str]
    reverse: Dict[str, Any]
    
    @classmethod
    def load_from_yaml(cls, file_path: str) -> 'ProjectionSpec':
        """从YAML文件加载投影规范"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            return cls(
                version=data['version'],
                app=data['app'],
                namespace=data['namespace'],
                project_id_expr=data['project_id_expr'],
                key_exprs=data['key_exprs'],
                context_exprs=data['context_exprs'],
                stabilizers=data['stabilizers'],
                reverse=data['reverse']
            )
        except Exception as e:
            logger.error("投影规范加载失败", file_path=file_path, error=str(e))
            raise
    
    def make_uida(self, source_data: Dict[str, Any]) -> Tuple[UIDA, Dict[str, Any]]:
        """根据源数据生成UIDA和上下文"""
        # 生成project_id
        project_id = self._evaluate_expression(self.project_id_expr, source_data)
        
        # 生成keys
        keys = []
        for key_expr in self.key_exprs:
            key_value = self._evaluate_expression(key_expr, source_data)
            keys.append(key_value)
        
        # 生成context
        context = {}
        for ctx_key, ctx_expr in self.context_exprs.items():
            context[ctx_key] = self._evaluate_expression(ctx_expr, source_data)
        
        uida = UIDA(
            namespace=self.namespace,
            project_id=project_id,
            keys=tuple(keys)
        )
        
        return uida, context
    
    def from_uida(self, uida: UIDA, context: Dict[str, Any]) -> Dict[str, Any]:
        """从UIDA和上下文反向生成应用数据"""
        if not self.reverse or 'object_map' not in self.reverse:
            raise ValueError("投影规范缺少reverse.object_map配置")
        
        object_map = self.reverse['object_map']
        result = {}
        
        for field_name, expr in object_map.items():
            try:
                if expr.startswith('{project_id'):
                    # 处理project_id表达式
                    value = self._reverse_project_id_expr(expr, uida.project_id)
                elif expr.startswith('{keys['):
                    # 处理keys表达式
                    value = self._reverse_keys_expr(expr, uida.keys)
                elif expr.startswith('{ctx['):
                    # 处理context表达式
                    value = self._reverse_context_expr(expr, context)
                else:
                    # 静态值
                    value = expr
                
                result[field_name] = value
            except Exception as e:
                logger.warning("反向表达式求值失败",
                             field=field_name,
                             expression=expr,
                             error=str(e))
                result[field_name] = None
        
        return result
    
    def _evaluate_expression(self, expr: str, data: Dict[str, Any]) -> str:
        """求值表达式"""
        # 简化的表达式求值器，支持基本的字段访问
        if expr.startswith('{') and expr.endswith('}'):
            field_path = expr[1:-1]
            return str(self._get_nested_value(data, field_path))
        else:
            # 静态值
            return expr
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """获取嵌套字段值"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return ""
        return value
    
    def _reverse_project_id_expr(self, expr: str, project_id: str) -> str:
        """反向处理project_id表达式"""
        if '|strip_prefix:' in expr:
            prefix = expr.split('|strip_prefix:')[1].rstrip('}')
            if project_id.startswith(prefix):
                return project_id[len(prefix):]
        return project_id
    
    def _reverse_keys_expr(self, expr: str, keys: Tuple[str, ...]) -> str:
        """反向处理keys表达式"""
        # 提取索引
        match = re.search(r'keys\[(\d+)\]', expr)
        if match:
            index = int(match.group(1))
            if 0 <= index < len(keys):
                key_value = keys[index]
                
                # 处理管道操作
                if '|strip_prefix:' in expr:
                    prefix = expr.split('|strip_prefix:')[1].rstrip('}')
                    if key_value.startswith(prefix):
                        return key_value[len(prefix):]
                
                return key_value
        
        return ""
    
    def _reverse_context_expr(self, expr: str, context: Dict[str, Any]) -> Any:
        """反向处理context表达式"""
        # 提取字段名
        match = re.search(r'ctx\[([^\]]+)\]', expr)
        if match:
            field_name = match.group(1)
            return context.get(field_name, "")
        return ""


class TextStabilizer:
    """文本稳定器 - 规范化文本以确保一致性"""
    
    def __init__(self, stabilizers: List[str]):
        self.stabilizers = stabilizers
    
    def stabilize(self, text: str) -> str:
        """应用稳定化规则"""
        result = text
        
        for stabilizer in self.stabilizers:
            if stabilizer == "canon":
                result = self._canonicalize(result)
            elif stabilizer == "lower":
                result = result.lower()
            elif stabilizer == "trim":
                result = result.strip()
            elif stabilizer == "normalize_space":
                result = re.sub(r'\s+', ' ', result)
        
        return result
    
    def _canonicalize(self, text: str) -> str:
        """规范化文本"""
        # 移除多余空白，统一换行符
        text = re.sub(r'\r\n|\r', '\n', text)
        text = re.sub(r'\n+', '\n', text)
        text = text.strip()
        return text


@dataclass
class MinecraftLanguageData:
    """Minecraft语言数据结构"""
    pack_id: str
    pack_format: int
    minecraft_version: str
    mod_loader: str
    language_files: List['MinecraftLanguageFile']
    
    def add_language_file(self, lang_file: 'MinecraftLanguageFile'):
        """添加语言文件"""
        self.language_files.append(lang_file)


@dataclass
class MinecraftLanguageFile:
    """Minecraft语言文件"""
    mod_id: str
    language: str
    file_path: str
    translations: Dict[str, str]
    mod_version: Optional[str] = None
    
    def __init__(self, mod_id: str, language: str, file_path: str):
        self.mod_id = mod_id
        self.language = language
        self.file_path = file_path
        self.translations = {}
        self.mod_version = None
    
    def add_translation(self, key: str, value: str):
        """添加翻译条目"""
        self.translations[key] = value


@dataclass
class TranslationItem:
    """翻译项目"""
    uida_hash: str
    source_text: str
    target_text: Optional[str]
    minecraft_context: Dict[str, Any]
    
    def get_mod_id(self) -> str:
        """获取MOD ID"""
        return self.minecraft_context.get('mod_id', '')


class MinecraftProjectionAdapter:
    """Minecraft投影适配器"""
    
    def __init__(self, projection_spec_path: Optional[str] = None):
        self.spec = None
        self.stabilizer = None
        
        if projection_spec_path:
            self.load_projection_spec(projection_spec_path)
    
    def load_projection_spec(self, spec_path: str):
        """加载投影规范"""
        try:
            self.spec = ProjectionSpec.load_from_yaml(spec_path)
            self.stabilizer = TextStabilizer(self.spec.stabilizers)
            logger.info("Minecraft投影规范加载成功", spec_path=spec_path)
        except Exception as e:
            logger.error("投影规范加载失败", spec_path=spec_path, error=str(e))
            raise
    
    async def minecraft_to_core(
        self, 
        minecraft_data: MinecraftLanguageData
    ) -> List[Dict[str, Any]]:
        """将Minecraft数据转换为核心格式"""
        if not self.spec:
            raise ValueError("投影规范未加载")
        
        core_items = []
        
        for lang_file in minecraft_data.language_files:
            for key, translation in lang_file.translations.items():
                # 构建源数据
                source_data = {
                    "pack_id": minecraft_data.pack_id,
                    "mod_id": lang_file.mod_id,
                    "lang_key": key,
                    "lang": lang_file.language,
                    "src_text": translation,
                    "dst_text": translation,  # 在实际场景中可能有不同的目标文本
                    "resource_path": lang_file.file_path,
                    "mod_version": lang_file.mod_version or "unknown",
                    "pack_format": minecraft_data.pack_format
                }
                
                # 生成UIDA和上下文
                uida, context = self.spec.make_uida(source_data)
                
                # 应用文本稳定化
                stabilized_text = self.stabilizer.stabilize(translation)
                
                # 创建核心内容项
                core_item = {
                    "uida_hash": uida.identity_hash(),
                    "uida_uri": uida.to_uri(),
                    "namespace": uida.namespace,
                    "project_id": uida.project_id,
                    "keys": list(uida.keys),
                    "context": context,
                    "source_text": stabilized_text,
                    "target_text": stabilized_text,
                    "metadata": {
                        "content_type": "minecraft_translation",
                        "mod_loader": minecraft_data.mod_loader,
                        "minecraft_version": minecraft_data.minecraft_version,
                        "pack_format": minecraft_data.pack_format
                    }
                }
                
                core_items.append(core_item)
        
        logger.debug("Minecraft数据转换完成",
                    pack_id=minecraft_data.pack_id,
                    items_count=len(core_items))
        
        return core_items
    
    async def core_to_minecraft(
        self,
        core_items: List[Dict[str, Any]],
        pack_id: str
    ) -> MinecraftLanguageData:
        """将核心数据转换为Minecraft格式"""
        if not self.spec:
            raise ValueError("投影规范未加载")
        
        minecraft_data = MinecraftLanguageData(
            pack_id=pack_id,
            pack_format=0,  # 将从数据中推断
            minecraft_version="unknown",  # 将从数据中推断
            mod_loader="unknown",  # 将从数据中推断
            language_files=[]
        )
        
        # 按MOD和语言分组
        grouped_items = self._group_by_mod_and_language(core_items)
        
        for (mod_id, language), items in grouped_items.items():
            lang_file = MinecraftLanguageFile(
                mod_id=mod_id,
                language=language,
                file_path=f"assets/{mod_id}/lang/{language}.json"
            )
            
            for item in items:
                try:
                    # 使用投影规范反向转换
                    uida = UIDA(
                        namespace=item["namespace"],
                        project_id=item["project_id"],
                        keys=tuple(item["keys"])
                    )
                    
                    app_data = self.spec.from_uida(uida, item["context"])
                    
                    lang_file.add_translation(
                        key=app_data["lang_key"],
                        value=item.get("target_text", item.get("source_text", ""))
                    )
                    
                    # 更新文件元信息
                    if app_data.get("mod_version"):
                        lang_file.mod_version = app_data["mod_version"]
                    
                    # 更新包元信息
                    metadata = item.get("metadata", {})
                    if metadata.get("pack_format"):
                        minecraft_data.pack_format = metadata["pack_format"]
                    if metadata.get("minecraft_version"):
                        minecraft_data.minecraft_version = metadata["minecraft_version"]
                    if metadata.get("mod_loader"):
                        minecraft_data.mod_loader = metadata["mod_loader"]
                
                except Exception as e:
                    logger.warning("核心数据转换失败",
                                 uida_hash=item.get("uida_hash", "unknown")[:16],
                                 error=str(e))
                    continue
            
            if lang_file.translations:  # 只添加有内容的文件
                minecraft_data.add_language_file(lang_file)
        
        logger.debug("核心数据转换完成",
                    pack_id=pack_id,
                    files_count=len(minecraft_data.language_files))
        
        return minecraft_data
    
    def _group_by_mod_and_language(
        self, 
        core_items: List[Dict[str, Any]]
    ) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
        """按MOD和语言分组"""
        groups = {}
        
        for item in core_items:
            try:
                uida = UIDA(
                    namespace=item["namespace"],
                    project_id=item["project_id"],
                    keys=tuple(item["keys"])
                )
                
                app_data = self.spec.from_uida(uida, item["context"])
                mod_id = app_data.get("mod_id", "unknown")
                language = app_data.get("lang", "en_us")
                
                key = (mod_id, language)
                if key not in groups:
                    groups[key] = []
                
                groups[key].append(item)
            
            except Exception as e:
                logger.warning("分组处理失败", 
                             uida_hash=item.get("uida_hash", "unknown")[:16],
                             error=str(e))
                continue
        
        return groups
    
    def validate_minecraft_data(self, minecraft_data: MinecraftLanguageData) -> List[str]:
        """验证Minecraft数据"""
        issues = []
        
        if not minecraft_data.pack_id:
            issues.append("缺少pack_id")
        
        if not minecraft_data.language_files:
            issues.append("没有语言文件")
        
        for lang_file in minecraft_data.language_files:
            if not lang_file.mod_id:
                issues.append(f"语言文件缺少mod_id: {lang_file.file_path}")
            
            if not lang_file.language:
                issues.append(f"语言文件缺少language: {lang_file.file_path}")
            
            if not lang_file.translations:
                issues.append(f"语言文件没有翻译内容: {lang_file.file_path}")
        
        return issues
    
    def get_projection_stats(self, minecraft_data: MinecraftLanguageData) -> Dict[str, Any]:
        """获取投影统计信息"""
        stats = {
            "pack_id": minecraft_data.pack_id,
            "total_language_files": len(minecraft_data.language_files),
            "total_translations": sum(len(lf.translations) for lf in minecraft_data.language_files),
            "mods_count": len(set(lf.mod_id for lf in minecraft_data.language_files)),
            "languages": list(set(lf.language for lf in minecraft_data.language_files)),
            "languages_count": len(set(lf.language for lf in minecraft_data.language_files))
        }
        
        return stats


# ==================== 工厂函数和便捷函数 ====================

def create_minecraft_projection_adapter(spec_path: Optional[str] = None) -> MinecraftProjectionAdapter:
    """创建Minecraft投影适配器"""
    return MinecraftProjectionAdapter(spec_path)


def load_projection_spec_from_config(config_dir: str) -> ProjectionSpec:
    """从配置目录加载投影规范"""
    spec_path = Path(config_dir) / "mc-projection.yaml"
    return ProjectionSpec.load_from_yaml(str(spec_path))


async def convert_minecraft_to_core(
    minecraft_data: MinecraftLanguageData,
    spec_path: str
) -> List[Dict[str, Any]]:
    """便捷函数：转换Minecraft数据到核心格式"""
    adapter = MinecraftProjectionAdapter(spec_path)
    return await adapter.minecraft_to_core(minecraft_data)


async def convert_core_to_minecraft(
    core_items: List[Dict[str, Any]],
    pack_id: str,
    spec_path: str
) -> MinecraftLanguageData:
    """便捷函数：转换核心数据到Minecraft格式"""
    adapter = MinecraftProjectionAdapter(spec_path)
    return await adapter.core_to_minecraft(core_items, pack_id)


# ==================== 投影规范模板生成器 ====================

def generate_default_projection_spec(output_path: str):
    """生成默认的Minecraft投影规范模板"""
    spec_template = {
        "version": 1,
        "app": "mc-l10n",
        "namespace": "mc",
        "project_id_expr": "pack:{pack_id}",
        "key_exprs": [
            "mod:{mod_id}",
            "key:{lang_key}",
            "lang:{lang}"
        ],
        "context_exprs": {
            "resource_path": "{resource_path}",
            "mod_version": "{mod_version}",
            "pack_format": "{pack_format}"
        },
        "stabilizers": ["canon", "lower"],
        "reverse": {
            "object_map": {
                "pack_id": "{project_id|strip_prefix:pack:}",
                "mod_id": "{keys[0]|strip_prefix:mod:}",
                "lang_key": "{keys[1]|strip_prefix:key:}",
                "lang": "{keys[2]|strip_prefix:lang:}",
                "resource_path": "{ctx[resource_path]}",
                "mod_version": "{ctx[mod_version]}",
                "pack_format": "{ctx[pack_format]}"
            }
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(spec_template, f, default_flow_style=False, allow_unicode=True)
    
    logger.info("默认投影规范已生成", output_path=output_path)