"""
组合包构建器
基于升级方案的多策略本地化包构建系统
"""

import json
import shutil
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

from ..adapters.projection import MinecraftLanguageData, MinecraftLanguageFile
from ..domain.jar_processor import (
    AdvancedJarProcessor, JarModification, ModificationType, 
    BackupPolicy, JarModificationResult
)

logger = structlog.get_logger(__name__)


class PackFormat(Enum):
    """包格式版本"""
    FORMAT_6 = 6    # 1.16.2-1.16.5
    FORMAT_7 = 7    # 1.17-1.17.1
    FORMAT_8 = 8    # 1.18-1.18.2
    FORMAT_9 = 9    # 1.19-1.19.2
    FORMAT_12 = 12  # 1.19.3
    FORMAT_13 = 13  # 1.19.4-1.20.1
    FORMAT_15 = 15  # 1.20.2-1.20.4
    FORMAT_18 = 18  # 1.20.5+


@dataclass
class BuildOptions:
    """构建选项"""
    build_strategy: str = "resource_pack"
    pack_format: int = 15
    pack_description: str = "TH-Suite生成的本地化包"
    preserve_original: bool = True
    create_backup: bool = True
    compress_output: bool = True
    validate_output: bool = True
    
    # 资源包选项
    include_pack_icon: bool = True
    merge_existing_lang: bool = True
    
    # JAR修改选项
    backup_policy: BackupPolicy = BackupPolicy.ALWAYS
    verify_integrity: bool = True
    
    # 覆盖包选项
    create_install_script: bool = True
    generate_readme: bool = True


@dataclass
class BuildResult:
    """构建结果"""
    success: bool
    build_strategy: str
    output_path: str
    created_files: List[str]
    modified_files: List[str]
    errors: List[str]
    warnings: List[str]
    build_time: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)
    
    def add_created_file(self, file_path: str):
        """添加创建的文件"""
        self.created_files.append(file_path)
    
    def add_modified_file(self, file_path: str):
        """添加修改的文件"""
        self.modified_files.append(file_path)


class ResourcePackBuilder:
    """资源包构建器"""
    
    def __init__(self):
        self.pack_formats = {
            "1.16": PackFormat.FORMAT_6,
            "1.17": PackFormat.FORMAT_7,
            "1.18": PackFormat.FORMAT_8,
            "1.19": PackFormat.FORMAT_9,
            "1.20": PackFormat.FORMAT_15
        }
        
        logger.info("资源包构建器已初始化")
    
    async def build_language_pack(
        self,
        minecraft_data: MinecraftLanguageData,
        output_path: str,
        build_options: BuildOptions
    ) -> BuildResult:
        """构建语言资源包"""
        import time
        start_time = time.time()
        
        result = BuildResult(
            success=True,
            build_strategy="resource_pack",
            output_path=output_path,
            created_files=[],
            modified_files=[],
            errors=[],
            warnings=[],
            build_time=0.0,
            metadata={}
        )
        
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 1. 创建pack.mcmeta文件
            await self._create_pack_mcmeta(output_dir, build_options, result)
            
            # 2. 创建语言文件结构
            await self._create_language_files(output_dir, minecraft_data, build_options, result)
            
            # 3. 可选：添加包图标
            if build_options.include_pack_icon:
                await self._add_pack_icon(output_dir, result)
            
            # 4. 可选：压缩为ZIP文件
            if build_options.compress_output:
                await self._compress_resource_pack(output_dir, result)
            
            # 5. 可选：验证输出
            if build_options.validate_output:
                await self._validate_resource_pack(output_dir, result)
            
            # 更新元数据
            result.metadata.update({
                "pack_format": build_options.pack_format,
                "languages": list(set(lf.language for lf in minecraft_data.language_files)),
                "mods": list(set(lf.mod_id for lf in minecraft_data.language_files)),
                "total_translations": sum(len(lf.translations) for lf in minecraft_data.language_files)
            })
            
            logger.info("资源包构建完成",
                       output_path=output_path,
                       files_created=len(result.created_files))
            
        except Exception as e:
            logger.error("资源包构建失败", error=str(e))
            result.add_error(str(e))
        
        finally:
            result.build_time = time.time() - start_time
        
        return result
    
    async def _create_pack_mcmeta(
        self, 
        output_dir: Path, 
        build_options: BuildOptions,
        result: BuildResult
    ):
        """创建pack.mcmeta文件"""
        pack_mcmeta = {
            "pack": {
                "pack_format": build_options.pack_format,
                "description": build_options.pack_description
            }
        }
        
        mcmeta_path = output_dir / "pack.mcmeta"
        with open(mcmeta_path, 'w', encoding='utf-8') as f:
            json.dump(pack_mcmeta, f, ensure_ascii=False, indent=2)
        
        result.add_created_file(str(mcmeta_path))
        logger.debug("创建pack.mcmeta", path=str(mcmeta_path))
    
    async def _create_language_files(
        self,
        output_dir: Path,
        minecraft_data: MinecraftLanguageData,
        build_options: BuildOptions,
        result: BuildResult
    ):
        """创建语言文件"""
        for lang_file in minecraft_data.language_files:
            # 构建输出路径: assets/{mod_id}/lang/{language}.json
            lang_dir = output_dir / "assets" / lang_file.mod_id / "lang"
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            lang_file_path = lang_dir / f"{lang_file.language}.json"
            
            # 如果需要合并现有语言文件
            existing_translations = {}
            if build_options.merge_existing_lang and lang_file_path.exists():
                try:
                    with open(lang_file_path, 'r', encoding='utf-8') as f:
                        existing_translations = json.load(f)
                except Exception as e:
                    result.add_warning(f"无法读取现有语言文件 {lang_file_path}: {e}")
            
            # 合并翻译
            merged_translations = {**existing_translations, **lang_file.translations}
            
            # 写入文件
            with open(lang_file_path, 'w', encoding='utf-8') as f:
                json.dump(merged_translations, f, ensure_ascii=False, indent=2)
            
            if lang_file_path.exists() and str(lang_file_path) in result.created_files:
                result.add_modified_file(str(lang_file_path))
            else:
                result.add_created_file(str(lang_file_path))
            
            logger.debug("创建语言文件",
                        path=str(lang_file_path),
                        mod_id=lang_file.mod_id,
                        language=lang_file.language,
                        translations=len(merged_translations))
    
    async def _add_pack_icon(self, output_dir: Path, result: BuildResult):
        """添加包图标"""
        # 寻找默认图标或创建简单图标
        icon_path = output_dir / "pack.png"
        
        # 这里可以添加默认图标创建逻辑
        # 暂时跳过
        logger.debug("跳过包图标创建")
    
    async def _compress_resource_pack(self, output_dir: Path, result: BuildResult):
        """压缩资源包为ZIP文件"""
        zip_path = output_dir.with_suffix('.zip')
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in output_dir.rglob('*'):
                    if file_path.is_file():
                        arc_name = file_path.relative_to(output_dir)
                        zipf.write(file_path, arc_name)
            
            result.add_created_file(str(zip_path))
            result.metadata["compressed_file"] = str(zip_path)
            
            logger.debug("资源包已压缩", zip_path=str(zip_path))
            
        except Exception as e:
            result.add_warning(f"压缩失败: {e}")
    
    async def _validate_resource_pack(self, output_dir: Path, result: BuildResult):
        """验证资源包"""
        validation_issues = []
        
        # 检查必要文件
        pack_mcmeta = output_dir / "pack.mcmeta"
        if not pack_mcmeta.exists():
            validation_issues.append("缺少pack.mcmeta文件")
        
        # 检查语言文件格式
        for lang_file in output_dir.glob("assets/*/lang/*.json"):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                validation_issues.append(f"语言文件JSON格式错误 {lang_file}: {e}")
        
        if validation_issues:
            for issue in validation_issues:
                result.add_warning(issue)
        
        result.metadata["validation_issues"] = len(validation_issues)
        logger.debug("资源包验证完成", issues=len(validation_issues))


class JarModificationBuilder:
    """JAR修改构建器"""
    
    def __init__(self):
        self.jar_processor = AdvancedJarProcessor()
        logger.info("JAR修改构建器已初始化")
    
    async def build_via_jar_modification(
        self,
        minecraft_data: MinecraftLanguageData,
        original_pack_path: str,
        output_path: str,
        build_options: BuildOptions
    ) -> BuildResult:
        """通过直接修改JAR文件构建"""
        import time
        start_time = time.time()
        
        result = BuildResult(
            success=True,
            build_strategy="jar_modification",
            output_path=output_path,
            created_files=[],
            modified_files=[],
            errors=[],
            warnings=[],
            build_time=0.0,
            metadata={}
        )
        
        try:
            # 1. 复制原始包到输出目录
            if build_options.preserve_original:
                await self._copy_original_pack(original_pack_path, output_path, result)
            
            # 2. 按MOD分组语言文件
            mod_language_files = self._group_language_files_by_mod(minecraft_data)
            
            # 3. 修改每个MOD的JAR文件
            for mod_id, lang_files in mod_language_files.items():
                await self._modify_mod_jar(
                    mod_id, lang_files, output_path, build_options, result
                )
            
            # 4. 生成修改报告
            await self._generate_modification_report(result)
            
            result.metadata.update({
                "modified_mods": len(mod_language_files),
                "languages": list(set(lf.language for lf in minecraft_data.language_files)),
                "total_modifications": len(result.modified_files)
            })
            
            logger.info("JAR修改构建完成",
                       output_path=output_path,
                       modified_jars=len(mod_language_files))
            
        except Exception as e:
            logger.error("JAR修改构建失败", error=str(e))
            result.add_error(str(e))
        
        finally:
            result.build_time = time.time() - start_time
        
        return result
    
    async def _copy_original_pack(
        self, 
        original_path: str, 
        output_path: str,
        result: BuildResult
    ):
        """复制原始包"""
        source_dir = Path(original_path)
        dest_dir = Path(output_path)
        
        if source_dir.exists():
            shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
            logger.debug("原始包已复制", source=str(source_dir), dest=str(dest_dir))
        
    def _group_language_files_by_mod(
        self, 
        minecraft_data: MinecraftLanguageData
    ) -> Dict[str, List[MinecraftLanguageFile]]:
        """按MOD分组语言文件"""
        mod_files = {}
        for lang_file in minecraft_data.language_files:
            if lang_file.mod_id not in mod_files:
                mod_files[lang_file.mod_id] = []
            mod_files[lang_file.mod_id].append(lang_file)
        
        return mod_files
    
    async def _modify_mod_jar(
        self,
        mod_id: str,
        lang_files: List[MinecraftLanguageFile],
        output_path: str,
        build_options: BuildOptions,
        result: BuildResult
    ):
        """修改MOD的JAR文件"""
        # 寻找MOD的JAR文件
        jar_files = list(Path(output_path).glob(f"**/*{mod_id}*.jar"))
        
        if not jar_files:
            result.add_warning(f"未找到MOD {mod_id} 的JAR文件")
            return
        
        jar_path = str(jar_files[0])  # 使用第一个匹配的JAR
        
        # 准备修改列表
        modifications = []
        for lang_file in lang_files:
            modification = JarModification(
                type=ModificationType.UPDATE_FILE,
                path=f"assets/{mod_id}/lang/{lang_file.language}.json",
                content=json.dumps(
                    lang_file.translations, 
                    ensure_ascii=False, 
                    indent=2
                ).encode('utf-8'),
                metadata={
                    "language": lang_file.language,
                    "mod_id": mod_id,
                    "translation_count": len(lang_file.translations)
                }
            )
            modifications.append(modification)
        
        # 执行修改
        try:
            jar_result = await self.jar_processor.safe_jar_modification(
                jar_path,
                modifications,
                build_options.backup_policy
            )
            
            if jar_result.success:
                result.add_modified_file(jar_path)
                logger.debug("MOD JAR修改成功",
                           mod_id=mod_id,
                           jar_path=jar_path,
                           modifications=len(modifications))
            else:
                error_msg = f"MOD {mod_id} JAR修改失败: {'; '.join(jar_result.errors)}"
                result.add_error(error_msg)
            
        except Exception as e:
            result.add_error(f"修改MOD {mod_id} JAR时异常: {str(e)}")
    
    async def _generate_modification_report(self, result: BuildResult):
        """生成修改报告"""
        if not result.output_path:
            return
        
        report_path = Path(result.output_path) / "modification_report.json"
        
        report = {
            "build_strategy": result.build_strategy,
            "build_time": result.build_time,
            "success": result.success,
            "modified_files": result.modified_files,
            "created_files": result.created_files,
            "errors": result.errors,
            "warnings": result.warnings,
            "metadata": result.metadata
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        result.add_created_file(str(report_path))


class OverlayManager:
    """覆盖包管理器"""
    
    def __init__(self):
        logger.info("覆盖包管理器已初始化")
    
    async def create_overlay(
        self,
        minecraft_data: MinecraftLanguageData,
        output_path: str,
        build_options: BuildOptions
    ) -> BuildResult:
        """创建覆盖包"""
        import time
        start_time = time.time()
        
        result = BuildResult(
            success=True,
            build_strategy="overlay",
            output_path=output_path,
            created_files=[],
            modified_files=[],
            errors=[],
            warnings=[],
            build_time=0.0,
            metadata={}
        )
        
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 1. 创建覆盖文件结构
            await self._create_overlay_structure(output_dir, minecraft_data, result)
            
            # 2. 可选：创建安装脚本
            if build_options.create_install_script:
                await self._create_install_script(output_dir, result)
            
            # 3. 可选：生成README
            if build_options.generate_readme:
                await self._generate_readme(output_dir, minecraft_data, result)
            
            result.metadata.update({
                "languages": list(set(lf.language for lf in minecraft_data.language_files)),
                "mods": list(set(lf.mod_id for lf in minecraft_data.language_files)),
                "overlay_files": len(result.created_files)
            })
            
            logger.info("覆盖包创建完成",
                       output_path=output_path,
                       files_created=len(result.created_files))
            
        except Exception as e:
            logger.error("覆盖包创建失败", error=str(e))
            result.add_error(str(e))
        
        finally:
            result.build_time = time.time() - start_time
        
        return result
    
    async def _create_overlay_structure(
        self,
        output_dir: Path,
        minecraft_data: MinecraftLanguageData,
        result: BuildResult
    ):
        """创建覆盖文件结构"""
        for lang_file in minecraft_data.language_files:
            # 创建相对于原始位置的覆盖文件
            overlay_path = output_dir / "overlays" / lang_file.mod_id / f"{lang_file.language}.json"
            overlay_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(overlay_path, 'w', encoding='utf-8') as f:
                json.dump(lang_file.translations, f, ensure_ascii=False, indent=2)
            
            result.add_created_file(str(overlay_path))
    
    async def _create_install_script(self, output_dir: Path, result: BuildResult):
        """创建安装脚本"""
        # Windows批处理脚本
        bat_script = """@echo off
echo Installing TH-Suite Language Overlay...
echo This script will copy language files to your modpack.
echo.
echo Please make sure to backup your modpack before proceeding!
pause
echo.
echo Installation completed!
pause
"""
        
        script_path = output_dir / "install.bat"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(bat_script)
        
        result.add_created_file(str(script_path))
    
    async def _generate_readme(
        self,
        output_dir: Path,
        minecraft_data: MinecraftLanguageData,
        result: BuildResult
    ):
        """生成README文件"""
        languages = list(set(lf.language for lf in minecraft_data.language_files))
        mods = list(set(lf.mod_id for lf in minecraft_data.language_files))
        
        readme_content = f"""# TH-Suite 本地化覆盖包

这是由TH-Suite生成的Minecraft模组本地化覆盖包。

## 包含的语言
{chr(10).join(f'- {lang}' for lang in languages)}

## 支持的模组
{chr(10).join(f'- {mod}' for mod in mods)}

## 安装方法
1. 备份你的整合包
2. 运行install.bat脚本（Windows）
3. 或者手动复制overlays目录中的文件到对应的模组JAR中

## 注意事项
- 请在安装前备份原始文件
- 某些模组可能需要特定的安装方法
- 如果遇到问题，请恢复备份

---
由TH-Suite v2.0自动生成
"""
        
        readme_path = output_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        result.add_created_file(str(readme_path))


class PackBuilder:
    """统一的包构建器"""
    
    def __init__(self):
        self.resource_pack_builder = ResourcePackBuilder()
        self.jar_modification_builder = JarModificationBuilder()
        self.overlay_manager = OverlayManager()
        
        logger.info("包构建器已初始化")
    
    async def build_localized_pack(
        self,
        minecraft_data: MinecraftLanguageData,
        original_pack_path: str,
        output_path: str,
        build_options: BuildOptions
    ) -> BuildResult:
        """构建本地化包"""
        
        if build_options.build_strategy == "resource_pack":
            return await self.resource_pack_builder.build_language_pack(
                minecraft_data, output_path, build_options
            )
        
        elif build_options.build_strategy == "jar_modification":
            return await self.jar_modification_builder.build_via_jar_modification(
                minecraft_data, original_pack_path, output_path, build_options
            )
        
        elif build_options.build_strategy == "overlay":
            return await self.overlay_manager.create_overlay(
                minecraft_data, output_path, build_options
            )
        
        else:
            raise ValueError(f"不支持的构建策略: {build_options.build_strategy}")


# ==================== 工厂函数和便捷接口 ====================

def create_pack_builder() -> PackBuilder:
    """创建包构建器"""
    return PackBuilder()


async def quick_resource_pack_build(
    minecraft_data: MinecraftLanguageData,
    output_path: str,
    pack_format: int = 15,
    pack_description: str = "TH-Suite生成的本地化包"
) -> BuildResult:
    """快速构建资源包"""
    builder = PackBuilder()
    
    build_options = BuildOptions(
        build_strategy="resource_pack",
        pack_format=pack_format,
        pack_description=pack_description
    )
    
    return await builder.build_localized_pack(
        minecraft_data, "", output_path, build_options
    )