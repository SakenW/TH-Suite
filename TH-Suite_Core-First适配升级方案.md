# TH-Suite 直接重构为专业适配器方案

> **基于**: TH-Core-First-Pack_v1.0 + V6架构问题分析  
> **目标**: 直接重构为Trans-Hub专业应用适配器  
> **版本**: TH-Suite v2.0.0 (Pure-Adapter)  
> **前提**: 无生产环境，完全废弃V6问题架构

---

## 🎯 专业适配器定位

### 架构重新定义
```
TH-Suite = 专业游戏本地化适配器集合
专注: 游戏文件解析 + 工作流优化 + UI体验
依赖: 仅通过SDK访问Trans-Hub Core
```

**核心价值**:
- **游戏专业化**: 深度理解Minecraft/RimWorld文件格式和工作流
- **用户体验**: 游戏玩家和翻译者友好的操作界面
- **无基础设施负担**: 所有通用功能由Trans-Hub Core提供
- **高度集成**: 通过投影适配与核心无缝协作

---

## 🗑️ V6架构完全废弃 - 无生产环境，直接重构

### 文件重命名和重构策略

**前提**: 无生产环境，无迁移负担，直接最优化重构

**重命名映射**:
```bash
# 重构现有文件，避免冗余：
apps/mc_l10n/backend/database/ → 完全删除
apps/mc_l10n/backend/api/v6/ → 完全删除  
apps/mc_l10n/backend/services/content_addressing.py → src/adapters/core_client.py
apps/mc_l10n/backend/services/uida_service.py → src/adapters/projection.py
apps/mc_l10n/backend/services/performance_optimizer.py → 删除(Core提供)
apps/mc_l10n/backend/processors/jar_processor.py → src/domain/jar_processor.py
apps/mc_l10n/backend/processors/mod_scanner.py → src/domain/mod_scanner.py
apps/mc_l10n/backend/workflows/ → src/services/ (重命名整个目录)
```

**新的Core适配架构**:
class MinecraftCoreAdapter:
    """Minecraft核心适配器"""
    
    def __init__(self):
        # 仅依赖Trans-Hub SDK
        self.core_client = TransHubClient(
            api_key=config.TRANSHUB_API_KEY,
            base_url=config.TRANSHUB_BASE_URL,
            app_name="mc-l10n"
        )
        self.projection_spec = self._load_projection_spec()
        self.file_processor = MinecraftFileProcessor()
    
    async def initialize(self):
        """初始化适配器"""
        
        # 注册投影规范到核心
        await self.core_client.register_projection_spec(
            self.projection_spec.to_dict()
        )
        
        logger.info("Minecraft适配器初始化完成")
    
    async def scan_and_ingest_pack(
        self, 
        pack_path: str,
        pack_id: str
    ) -> PackIngestionResult:
        """扫描并摄入组合包"""
        
        # 1. 扫描Minecraft文件结构
        scan_result = await self.file_processor.scan_pack(pack_path)
        
        # 2. 转换为标准格式
        content_items = []
        for mod_file in scan_result.language_files:
            for key, translation in mod_file.translations.items():
                content_items.append({
                    "pack_id": pack_id,
                    "mod_id": mod_file.mod_id,
                    "lang_key": key,
                    "lang": mod_file.language,
                    "src_text": translation.source,
                    "dst_text": translation.target,
                    "resource_path": mod_file.file_path
                })
        
        # 3. 通过SDK摄入到核心
        ingestion_result = await self.core_client.ingest_content(
            project_id=pack_id,
            content_items=content_items
        )
        
        return PackIngestionResult.from_core_result(ingestion_result)
```

### 直接重构: 同步协议

**重构方案**: 直接替换为Trans-Hub Core的标准同步机制，重用现有代码结构

```python
class MinecraftSyncService:
    """Minecraft同步服务(基于Core)"""
    
    def __init__(self, core_adapter: MinecraftCoreAdapter):
        self.core_adapter = core_adapter
        self.local_cache = LocalPackCache()
        self.conflict_resolver = MinecraftConflictResolver()
    
    async def sync_pack_translations(
        self,
        pack_id: str,
        target_languages: List[str]
    ) -> SyncResult:
        """同步组合包翻译"""
        
        result = SyncResult()
        
        for lang in target_languages:
            try:
                # 从核心导出最新翻译
                export_filters = {
                    "target_language": lang,
                    "status": ["completed", "reviewed"]
                }
                
                translations = []
                async for item in self.core_adapter.core_client.export_content(
                    pack_id, export_filters
                ):
                    translations.append(item)
                
                # 转换为Minecraft格式
                minecraft_files = await self._convert_to_minecraft_format(
                    translations, lang
                )
                
                # 检查本地冲突
                conflicts = await self._detect_local_conflicts(
                    pack_id, minecraft_files
                )
                
                if conflicts:
                    # 解决冲突
                    resolved_files = await self.conflict_resolver.resolve_conflicts(
                        minecraft_files, conflicts
                    )
                    result.add_conflicts(lang, conflicts)
                else:
                    resolved_files = minecraft_files
                
                # 写回本地文件
                write_result = await self._write_minecraft_files(
                    pack_id, resolved_files
                )
                
                result.add_language_result(lang, write_result)
                
            except Exception as e:
                logger.error("语言同步失败", 
                           pack_id=pack_id,
                           language=lang,
                           error=str(e))
                result.add_error(lang, str(e))
        
        return result
    
    async def _convert_to_minecraft_format(
        self,
        translations: List[Dict[str, Any]],
        language: str
    ) -> List[MinecraftLanguageFile]:
        """转换为Minecraft语言文件格式"""
        
        # 按MOD分组
        mod_groups = defaultdict(list)
        for item in translations:
            mod_groups[item["mod_id"]].append(item)
        
        minecraft_files = []
        
        for mod_id, mod_translations in mod_groups.items():
            # 构建语言文件
            lang_file = MinecraftLanguageFile(
                mod_id=mod_id,
                language=language,
                file_path=f"assets/{mod_id}/lang/{language}.json"
            )
            
            for item in mod_translations:
                lang_file.add_translation(
                    key=item["lang_key"],
                    value=item["dst_text"] or item["src_text"]
                )
            
            minecraft_files.append(lang_file)
        
        return minecraft_files
```

---

## 📋 直接重构路线图 (无迁移负担)

### 🟢 Phase 1: 文件重命名与架构重构 (2-3周)

#### 1.1 文件重命名和代码重构

**目标**: 重命名现有文件，避免新建冗余文件，直接最优化

**具体重构行动**:
```bash
# 文件重命名操作(避免新建):
mv apps/mc_l10n/backend/services/content_addressing.py apps/mc_l10n/src/adapters/core_client.py
mv apps/mc_l10n/backend/services/uida_service.py apps/mc_l10n/src/adapters/projection.py  
mv apps/mc_l10n/backend/processors/jar_processor.py apps/mc_l10n/src/domain/jar_processor.py
mv apps/mc_l10n/backend/processors/mod_scanner.py apps/mc_l10n/src/domain/mod_scanner.py
mv apps/mc_l10n/backend/workflows/ apps/mc_l10n/src/services/

# 直接删除冗余组件:
rm -rf apps/mc_l10n/backend/database/
rm -rf apps/mc_l10n/backend/api/v6/
rm -rf apps/mc_l10n/backend/services/performance_optimizer.py

# 保留并重构的专业化组件:
# - jar_processor.py → 增强JAR处理能力
# - mod_scanner.py → 多加载器支持  
# - workflows/ → 重构为services/
```

**新的目录结构**:
```
th-suite/
├── apps/
│   ├── mc-l10n/                    # Minecraft应用
│   │   ├── src/
│   │   │   ├── adapters/           # 适配器层
│   │   │   │   ├── core_client.py  # Trans-Hub核心客户端
│   │   │   │   └── projection.py   # 投影适配器
│   │   │   ├── domain/            # Minecraft特定领域
│   │   │   │   ├── mod_scanner.py  # MOD扫描器
│   │   │   │   ├── jar_processor.py # JAR处理器
│   │   │   │   └── pack_builder.py # 组合包构建器
│   │   │   └── services/          # 业务服务
│   │   │       ├── sync_service.py # 同步服务
│   │   │       └── validation.py  # MC特定验证
│   │   ├── configs/
│   │   │   └── mc-projection.yaml # 投影规范
│   │   └── tests/
│   └── rw-l10n/                   # RimWorld应用(未来)
├── shared/                        # 共享工具
│   ├── file_processors/           # 通用文件处理器
│   ├── validation/               # 通用验证工具
│   └── ui_components/            # 共享UI组件
└── sdk/                          # Trans-Hub SDK封装
    ├── python/
    └── typescript/
```

#### 1.2 投影规范实现

**目标**: 实现Minecraft特定的投影适配器

**实施方案**:
```yaml
# configs/mc-projection.yaml
version: 1
app: mc-l10n
namespace: mc
project_id_expr: "pack:{pack_id}"
key_exprs:
  - "mod:{mod_id}"
  - "key:{lang_key}"  
  - "lang:{lang}"
context_exprs:
  resource_path: "{resource_path}"
  mod_version: "{mod_version}"
  pack_format: "{pack_format}"
stabilizers: ["canon", "lower"]
reverse:
  object_map:
    pack_id: "{project_id|strip_prefix:pack:}"
    mod_id: "{keys[0]|strip_prefix:mod:}"
    lang_key: "{keys[1]|strip_prefix:key:}"
    lang: "{keys[2]|strip_prefix:lang:}"
    resource_path: "{ctx[resource_path]}"
    mod_version: "{ctx[mod_version]}"
    pack_format: "{ctx[pack_format]}"
```

```python
class MinecraftProjectionAdapter:
    """Minecraft投影适配器"""
    
    def __init__(self):
        # 加载投影规范
        self.spec = ProjectionSpec.load_from_yaml("configs/mc-projection.yaml")
        self.stabilizer = TextStabilizer(self.spec.stabilizers)
    
    async def minecraft_to_core(
        self, 
        minecraft_data: MinecraftLanguageData
    ) -> List[CoreContentItem]:
        """将Minecraft数据转换为核心格式"""
        
        core_items = []
        
        for mod_file in minecraft_data.language_files:
            for key, translation in mod_file.translations.items():
                # 构建源数据
                source_data = {
                    "pack_id": minecraft_data.pack_id,
                    "mod_id": mod_file.mod_id,
                    "lang_key": key,
                    "lang": mod_file.language,
                    "src_text": translation.source,
                    "dst_text": translation.target,
                    "resource_path": mod_file.file_path,
                    "mod_version": mod_file.mod_version,
                    "pack_format": minecraft_data.pack_format
                }
                
                # 生成UIDA和上下文
                uida, context = self.spec.make_uida(source_data)
                
                # 创建核心内容项
                core_item = CoreContentItem(
                    uida_hash=uida.identity_hash(),
                    uida_uri=uida.to_uri(),
                    namespace=uida.namespace,
                    project_id=uida.project_id,
                    keys=list(uida.keys),
                    context=context,
                    source_text=translation.source,
                    target_text=translation.target,
                    metadata={
                        "content_type": "minecraft_translation",
                        "mod_loader": minecraft_data.mod_loader,
                        "minecraft_version": minecraft_data.minecraft_version
                    }
                )
                
                core_items.append(core_item)
        
        return core_items
    
    async def core_to_minecraft(
        self,
        core_items: List[Dict[str, Any]],
        pack_id: str
    ) -> MinecraftLanguageData:
        """将核心数据转换为Minecraft格式"""
        
        minecraft_data = MinecraftLanguageData(pack_id=pack_id)
        
        # 按MOD和语言分组
        grouped_items = self._group_by_mod_and_language(core_items)
        
        for (mod_id, language), items in grouped_items.items():
            lang_file = MinecraftLanguageFile(
                mod_id=mod_id,
                language=language,
                file_path=f"assets/{mod_id}/lang/{language}.json"
            )
            
            for item in items:
                # 使用投影规范反向转换
                app_data = self.spec.from_uida(
                    UIDA(
                        namespace=item["namespace"],
                        project_id=item["project_id"], 
                        keys=tuple(item["keys"])
                    ),
                    context=item["context"]
                )
                
                lang_file.add_translation(
                    key=app_data["lang_key"],
                    value=item.get("target_text", item.get("source_text", ""))
                )
            
            minecraft_data.add_language_file(lang_file)
        
        return minecraft_data
```

### 🟡 Phase 2: 专业化功能重构 (4-5周)

#### 2.1 Minecraft特定工作流优化

**目标**: 重构Minecraft特有的扫描、验证、构建流程

**实施方案**:
```python
class MinecraftWorkflowEngine:
    """Minecraft工作流引擎"""
    
    def __init__(self, core_adapter: MinecraftCoreAdapter):
        self.core_adapter = core_adapter
        self.pack_scanner = MinecraftPackScanner()
        self.jar_processor = JarProcessor()
        self.pack_builder = PackBuilder()
        self.validator = MinecraftTranslationValidator()
    
    async def execute_full_localization_workflow(
        self,
        pack_path: str,
        target_languages: List[str],
        output_path: str
    ) -> WorkflowResult:
        """执行完整的本地化工作流"""
        
        workflow = LocalizationWorkflow(
            pack_path=pack_path,
            target_languages=target_languages,
            output_path=output_path
        )
        
        try:
            # 1. 扫描阶段
            logger.info("开始扫描组合包", pack_path=pack_path)
            scan_result = await self.pack_scanner.scan_pack(pack_path)
            workflow.add_stage_result("scan", scan_result)
            
            # 2. 摄入阶段 - 上传到Trans-Hub Core
            logger.info("摄入内容到核心", entries_count=len(scan_result.entries))
            ingestion_result = await self.core_adapter.ingest_content(
                project_id=scan_result.pack_id,
                content_items=scan_result.entries
            )
            workflow.add_stage_result("ingestion", ingestion_result)
            
            # 3. 等待翻译完成 (外部流程)
            logger.info("等待翻译完成...")
            await self._wait_for_translation_completion(
                scan_result.pack_id, target_languages
            )
            
            # 4. 同步翻译结果
            logger.info("同步翻译结果", languages=target_languages)
            sync_result = await self._sync_translations(
                scan_result.pack_id, target_languages
            )
            workflow.add_stage_result("sync", sync_result)
            
            # 5. 验证翻译质量
            logger.info("验证翻译质量")
            validation_result = await self.validator.validate_translations(
                sync_result.translations
            )
            workflow.add_stage_result("validation", validation_result)
            
            # 6. 构建本地化包
            logger.info("构建本地化包", output_path=output_path)
            build_result = await self.pack_builder.build_localized_pack(
                original_pack=scan_result,
                translations=sync_result.translations,
                output_path=output_path,
                validation_result=validation_result
            )
            workflow.add_stage_result("build", build_result)
            
            workflow.mark_completed()
            
        except Exception as e:
            logger.error("工作流执行失败", error=str(e))
            workflow.mark_failed(str(e))
        
        return workflow.get_result()

class MinecraftTranslationValidator:
    """Minecraft翻译验证器"""
    
    def __init__(self):
        self.placeholder_validator = PlaceholderValidator()
        self.formatting_validator = MinecraftFormattingValidator()
        self.context_validator = MinecraftContextValidator()
    
    async def validate_translations(
        self,
        translations: List[TranslationItem]
    ) -> ValidationResult:
        """验证Minecraft翻译"""
        
        result = ValidationResult()
        
        for translation in translations:
            # Minecraft特定验证
            validation_issues = []
            
            # 1. 占位符验证 (%s, %d, {0}, 等)
            placeholder_issues = await self.placeholder_validator.validate(
                translation.source_text, translation.target_text
            )
            validation_issues.extend(placeholder_issues)
            
            # 2. Minecraft格式化验证 (§颜色码, JSON文本组件)
            formatting_issues = await self.formatting_validator.validate(
                translation.target_text, translation.context
            )
            validation_issues.extend(formatting_issues)
            
            # 3. 上下文适配性验证 (GUI文本长度, 命令帮助格式等)
            context_issues = await self.context_validator.validate(
                translation, translation.minecraft_context
            )
            validation_issues.extend(context_issues)
            
            # 4. MOD特定规则验证
            mod_specific_issues = await self._validate_mod_specific_rules(
                translation
            )
            validation_issues.extend(mod_specific_issues)
            
            if validation_issues:
                result.add_translation_issues(translation.uida_hash, validation_issues)
            else:
                result.add_valid_translation(translation.uida_hash)
        
        return result
    
    async def _validate_mod_specific_rules(
        self,
        translation: TranslationItem
    ) -> List[ValidationIssue]:
        """验证MOD特定规则"""
        
        issues = []
        mod_id = translation.get_mod_id()
        
        # 获取MOD特定验证规则
        mod_rules = await self._get_mod_validation_rules(mod_id)
        
        for rule in mod_rules:
            try:
                rule_result = await rule.validate(translation)
                if not rule_result.passed:
                    issues.append(ValidationIssue(
                        type="mod_specific_rule",
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=rule_result.message,
                        suggestion=rule_result.suggestion
                    ))
            except Exception as e:
                logger.warning("MOD规则验证失败",
                             mod_id=mod_id,
                             rule=rule.name,
                             error=str(e))
        
        return issues
```

#### 2.2 高级JAR处理能力

**目标**: 优化JAR文件的安全修改和回写能力

**实施方案**:
```python
class AdvancedJarProcessor:
    """高级JAR处理器"""
    
    def __init__(self):
        self.backup_manager = JarBackupManager()
        self.signature_verifier = JarSignatureVerifier()
        self.integrity_checker = JarIntegrityChecker()
        
    async def safe_jar_modification(
        self,
        jar_path: str,
        modifications: List[JarModification],
        backup_policy: BackupPolicy = BackupPolicy.ALWAYS
    ) -> JarModificationResult:
        """安全的JAR文件修改"""
        
        result = JarModificationResult(jar_path=jar_path)
        
        try:
            # 1. 预检查
            pre_check = await self._pre_modification_check(jar_path, modifications)
            if not pre_check.safe:
                return result.fail(pre_check.reasons)
            
            # 2. 创建备份
            if backup_policy != BackupPolicy.NEVER:
                backup_path = await self.backup_manager.create_backup(jar_path)
                result.backup_path = backup_path
            
            # 3. 验证JAR签名(如果有)
            signature_info = await self.signature_verifier.check_signature(jar_path)
            if signature_info.signed:
                logger.warning("JAR文件已签名，修改将破坏签名", 
                             jar_path=jar_path,
                             signer=signature_info.signer)
                result.add_warning("signature_will_be_broken")
            
            # 4. 执行修改
            with JarFile(jar_path, "a") as jar:
                for modification in modifications:
                    try:
                        await self._apply_modification(jar, modification)
                        result.add_successful_modification(modification)
                    except Exception as e:
                        result.add_failed_modification(modification, str(e))
            
            # 5. 完整性验证
            integrity_check = await self.integrity_checker.verify_jar(jar_path)
            if not integrity_check.valid:
                # 回滚修改
                if result.backup_path:
                    await self._restore_from_backup(jar_path, result.backup_path)
                return result.fail("完整性验证失败")
            
            # 6. 计算修改后的哈希
            result.final_hash = await self._calculate_jar_hash(jar_path)
            result.mark_successful()
            
        except Exception as e:
            logger.error("JAR修改失败", jar_path=jar_path, error=str(e))
            
            # 尝试恢复
            if result.backup_path:
                try:
                    await self._restore_from_backup(jar_path, result.backup_path)
                    result.add_info("已从备份恢复")
                except Exception as restore_error:
                    result.add_error(f"恢复失败: {restore_error}")
            
            result.fail(str(e))
        
        return result
    
    async def _apply_modification(
        self,
        jar: JarFile,
        modification: JarModification
    ):
        """应用单个JAR修改"""
        
        if modification.type == ModificationType.ADD_FILE:
            # 添加新文件
            jar.writestr(modification.path, modification.content)
            
        elif modification.type == ModificationType.UPDATE_FILE:
            # 更新现有文件
            # 先检查文件是否存在
            if modification.path not in jar.namelist():
                raise FileNotFoundError(f"要更新的文件不存在: {modification.path}")
            
            # 读取原始内容用于备份
            original_content = jar.read(modification.path)
            modification.original_content = original_content
            
            # 写入新内容
            jar.writestr(modification.path, modification.content)
            
        elif modification.type == ModificationType.DELETE_FILE:
            # JAR不支持删除文件，只能重新打包
            raise NotSupportedError("JAR文件不支持删除操作，需要重新打包")
            
        else:
            raise ValueError(f"不支持的修改类型: {modification.type}")

class PackBuilder:
    """组合包构建器"""
    
    def __init__(self):
        self.jar_processor = AdvancedJarProcessor()
        self.resource_pack_builder = ResourcePackBuilder()
        self.overlay_manager = OverlayManager()
    
    async def build_localized_pack(
        self,
        original_pack: PackScanResult,
        translations: Dict[str, List[TranslationItem]],
        output_path: str,
        validation_result: ValidationResult,
        build_options: BuildOptions = None
    ) -> BuildResult:
        """构建本地化组合包"""
        
        build_options = build_options or BuildOptions()
        result = BuildResult(output_path=output_path)
        
        try:
            # 1. 创建输出目录
            os.makedirs(output_path, exist_ok=True)
            
            # 2. 复制原始组合包结构
            await self._copy_original_structure(original_pack.pack_path, output_path)
            
            for language, lang_translations in translations.items():
                try:
                    # 3. 构建语言特定的资源包 (推荐方式)
                    if build_options.prefer_resource_pack:
                        resourcepack_result = await self.resource_pack_builder.build_language_pack(
                            translations=lang_translations,
                            language=language,
                            output_path=os.path.join(output_path, "resourcepacks", f"lang_{language}")
                        )
                        result.add_language_result(language, resourcepack_result)
                    
                    # 4. 或者直接修改JAR文件 (高风险选项)
                    elif build_options.modify_jars_directly:
                        jar_modifications = await self._prepare_jar_modifications(
                            lang_translations, original_pack
                        )
                        
                        for jar_path, modifications in jar_modifications.items():
                            jar_result = await self.jar_processor.safe_jar_modification(
                                jar_path=os.path.join(output_path, jar_path),
                                modifications=modifications,
                                backup_policy=BackupPolicy.ALWAYS
                            )
                            result.add_jar_result(jar_path, jar_result)
                    
                    # 5. 创建Overlay包 (灵活选项)
                    else:
                        overlay_result = await self.overlay_manager.create_overlay(
                            translations=lang_translations,
                            language=language,
                            base_pack=original_pack,
                            output_path=os.path.join(output_path, "overlays", language)
                        )
                        result.add_language_result(language, overlay_result)
                
                except Exception as e:
                    logger.error("语言构建失败", language=language, error=str(e))
                    result.add_language_error(language, str(e))
            
            # 6. 生成构建报告
            build_report = await self._generate_build_report(
                original_pack, translations, validation_result, result
            )
            
            await self._write_build_report(
                build_report, 
                os.path.join(output_path, "build_report.json")
            )
            
            result.mark_successful()
            
        except Exception as e:
            logger.error("构建失败", error=str(e))
            result.fail(str(e))
        
        return result
```

### 🔵 Phase 3: 生态集成优化 (3-4周)

#### 3.1 多MOD加载器支持

**目标**: 支持Forge, Fabric, Quilt等多种MOD加载器

**实施方案**:
```python
class ModLoaderRegistry:
    """MOD加载器注册表"""
    
    def __init__(self):
        self.loaders = {}
        self._register_builtin_loaders()
    
    def _register_builtin_loaders(self):
        """注册内置加载器支持"""
        
        self.register_loader("forge", ForgeModLoader())
        self.register_loader("fabric", FabricModLoader())
        self.register_loader("quilt", QuiltModLoader())
        self.register_loader("neoforge", NeoForgeModLoader())
    
    def register_loader(self, name: str, loader: ModLoaderAdapter):
        """注册MOD加载器适配器"""
        self.loaders[name] = loader
        logger.info("MOD加载器已注册", name=name, loader_class=loader.__class__.__name__)
    
    async def detect_loader(self, pack_path: str) -> Optional[ModLoaderInfo]:
        """自动检测MOD加载器类型"""
        
        for loader_name, loader in self.loaders.items():
            try:
                if await loader.can_handle_pack(pack_path):
                    loader_info = await loader.get_loader_info(pack_path)
                    return ModLoaderInfo(
                        name=loader_name,
                        version=loader_info.version,
                        adapter=loader
                    )
            except Exception as e:
                logger.debug("加载器检测失败", 
                           loader=loader_name,
                           pack_path=pack_path,
                           error=str(e))
        
        return None

class FabricModLoader(ModLoaderAdapter):
    """Fabric MOD加载器适配器"""
    
    async def can_handle_pack(self, pack_path: str) -> bool:
        """检查是否可以处理此组合包"""
        
        # 检查Fabric标识文件
        fabric_marker_files = [
            "fabric.mod.json",
            "quilt.mod.json", 
            "mods/fabric-api-*.jar"
        ]
        
        for marker in fabric_marker_files:
            if await self._file_exists(pack_path, marker):
                return True
        
        return False
    
    async def scan_mods(self, pack_path: str) -> List[ModInfo]:
        """扫描Fabric MOD"""
        
        mods = []
        mods_dir = os.path.join(pack_path, "mods")
        
        if not os.path.exists(mods_dir):
            return mods
        
        for file_name in os.listdir(mods_dir):
            if file_name.endswith('.jar'):
                jar_path = os.path.join(mods_dir, file_name)
                
                try:
                    mod_info = await self._extract_fabric_mod_info(jar_path)
                    if mod_info:
                        mods.append(mod_info)
                except Exception as e:
                    logger.warning("Fabric MOD信息提取失败", 
                                 jar_path=jar_path,
                                 error=str(e))
        
        return mods
    
    async def _extract_fabric_mod_info(self, jar_path: str) -> Optional[ModInfo]:
        """从Fabric MOD JAR提取信息"""
        
        with ZipFile(jar_path, 'r') as jar:
            # 检查fabric.mod.json
            if "fabric.mod.json" in jar.namelist():
                metadata_content = jar.read("fabric.mod.json").decode('utf-8')
                metadata = json.loads(metadata_content)
                
                return ModInfo(
                    id=metadata["id"],
                    name=metadata.get("name", metadata["id"]),
                    version=metadata.get("version", "unknown"),
                    loader_type="fabric",
                    jar_path=jar_path,
                    metadata=metadata
                )
            
            # 检查quilt.mod.json (Quilt兼容)
            elif "quilt.mod.json" in jar.namelist():
                metadata_content = jar.read("quilt.mod.json").decode('utf-8')
                metadata = json.loads(metadata_content)
                
                quilt_loader = metadata.get("quilt_loader", {})
                return ModInfo(
                    id=quilt_loader.get("id", "unknown"),
                    name=quilt_loader.get("metadata", {}).get("name", "unknown"),
                    version=quilt_loader.get("version", "unknown"),
                    loader_type="quilt",
                    jar_path=jar_path,
                    metadata=metadata
                )
        
        return None

class ForgeModLoader(ModLoaderAdapter):
    """Forge MOD加载器适配器"""
    
    async def can_handle_pack(self, pack_path: str) -> bool:
        """检查是否为Forge组合包"""
        
        forge_markers = [
            "mods.toml",
            "META-INF/mods.toml",
            "mods/forge-*.jar",
            "mods/minecraftforge-*.jar"
        ]
        
        for marker in forge_markers:
            if await self._file_exists(pack_path, marker):
                return True
        
        return False
    
    async def scan_mods(self, pack_path: str) -> List[ModInfo]:
        """扫描Forge MOD"""
        
        mods = []
        mods_dir = os.path.join(pack_path, "mods")
        
        if not os.path.exists(mods_dir):
            return mods
        
        for file_name in os.listdir(mods_dir):
            if file_name.endswith('.jar'):
                jar_path = os.path.join(mods_dir, file_name)
                
                try:
                    mod_info = await self._extract_forge_mod_info(jar_path)
                    if mod_info:
                        mods.append(mod_info)
                except Exception as e:
                    logger.warning("Forge MOD信息提取失败",
                                 jar_path=jar_path,
                                 error=str(e))
        
        return mods
    
    async def _extract_forge_mod_info(self, jar_path: str) -> Optional[ModInfo]:
        """从Forge MOD JAR提取信息"""
        
        with ZipFile(jar_path, 'r') as jar:
            # 现代Forge (1.13+) 使用mods.toml
            if "META-INF/mods.toml" in jar.namelist():
                import toml
                toml_content = jar.read("META-INF/mods.toml").decode('utf-8')
                metadata = toml.loads(toml_content)
                
                # Forge mods.toml通常包含多个mod定义
                mods_array = metadata.get("mods", [])
                if mods_array:
                    first_mod = mods_array[0]
                    return ModInfo(
                        id=first_mod["modId"],
                        name=first_mod.get("displayName", first_mod["modId"]),
                        version=first_mod.get("version", "unknown"),
                        loader_type="forge",
                        jar_path=jar_path,
                        metadata=metadata
                    )
            
            # 传统Forge (1.12.2及更早) 使用mcmod.info
            elif "mcmod.info" in jar.namelist():
                info_content = jar.read("mcmod.info").decode('utf-8')
                info_data = json.loads(info_content)
                
                if isinstance(info_data, list) and info_data:
                    first_mod = info_data[0]
                    return ModInfo(
                        id=first_mod["modid"],
                        name=first_mod.get("name", first_mod["modid"]),
                        version=first_mod.get("version", "unknown"),
                        loader_type="forge_legacy",
                        jar_path=jar_path,
                        metadata={"mcmod_info": info_data}
                    )
        
        return None
```

#### 3.2 高级用户界面

**目标**: 提供直观的Minecraft本地化工作流界面

**实施方案**:
```typescript
// TH-Suite前端重构
class MinecraftLocalizationWorkspace {
    private coreClient: TransHubClient;
    private minecraftAdapter: MinecraftCoreAdapter;
    
    constructor() {
        this.coreClient = new TransHubClient({
            apiKey: config.TRANSHUB_API_KEY,
            baseUrl: config.TRANSHUB_BASE_URL,
            appName: 'mc-l10n'
        });
        
        this.minecraftAdapter = new MinecraftCoreAdapter(this.coreClient);
    }
    
    async initializeProject(packPath: string): Promise<ProjectInfo> {
        // 1. 扫描组合包
        const scanResult = await this.minecraftAdapter.scanPack(packPath);
        
        // 2. 检测MOD加载器
        const loaderInfo = await this.detectModLoader(packPath);
        
        // 3. 创建项目在Trans-Hub Core
        const projectInfo = await this.coreClient.createProject({
            name: scanResult.packName,
            type: 'minecraft_modpack',
            metadata: {
                modLoader: loaderInfo.name,
                modLoaderVersion: loaderInfo.version,
                minecraftVersion: scanResult.minecraftVersion,
                modCount: scanResult.mods.length,
                totalTranslations: scanResult.totalTranslations
            }
        });
        
        // 4. 摄入内容
        await this.minecraftAdapter.ingestContent(
            projectInfo.id,
            scanResult.entries
        );
        
        return projectInfo;
    }
    
    async buildLocalizedPack(
        projectId: string,
        targetLanguages: string[],
        outputPath: string,
        buildOptions: BuildOptions
    ): Promise<BuildResult> {
        
        const buildProgress = new BuildProgress();
        
        try {
            // 1. 同步最新翻译
            buildProgress.setStage('syncing_translations');
            const syncResult = await this.minecraftAdapter.syncTranslations(
                projectId, targetLanguages
            );
            
            // 2. 验证翻译质量  
            buildProgress.setStage('validating_translations');
            const validationResult = await this.validateTranslations(
                syncResult.translations
            );
            
            // 3. 构建本地化包
            buildProgress.setStage('building_pack');
            const buildResult = await this.buildPack(
                projectId, syncResult.translations, outputPath, buildOptions
            );
            
            buildProgress.setStage('completed');
            return buildResult;
            
        } catch (error) {
            buildProgress.setStage('failed');
            throw error;
        }
    }
}

// React组件示例
const MinecraftProjectDashboard: React.FC<{projectId: string}> = ({ projectId }) => {
    const [project, setProject] = useState<ProjectInfo>();
    const [translations, setTranslations] = useState<TranslationStats>();
    const [buildOptions, setBuildOptions] = useState<BuildOptions>();
    
    return (
        <div className="minecraft-project-dashboard">
            <ProjectHeader project={project} />
            
            <Tabs>
                <TabPane tab="项目概览" key="overview">
                    <ProjectOverview 
                        project={project}
                        stats={translations}
                    />
                </TabPane>
                
                <TabPane tab="翻译进度" key="translations">
                    <TranslationProgress
                        projectId={projectId}
                        onTranslationUpdate={(stats) => setTranslations(stats)}
                    />
                </TabPane>
                
                <TabPane tab="质量检查" key="quality">
                    <QualityAssurance
                        projectId={projectId}
                        validationRules={minecraftValidationRules}
                    />
                </TabPane>
                
                <TabPane tab="构建部署" key="build">
                    <PackBuilder
                        projectId={projectId}
                        buildOptions={buildOptions}
                        onBuildOptionsChange={setBuildOptions}
                        onBuild={(options) => handleBuildPack(options)}
                    />
                </TabPane>
            </Tabs>
        </div>
    );
};
```

---

## 📊 预期效果

### 架构收益
- **去除重复**: 删除15,000+行重复基础设施代码
- **维护简化**: 仅需维护Minecraft特定逻辑，核心功能由Trans-Hub提供
- **一致性保证**: 通过投影适配确保数据一致性，解决V6的严重问题

### 功能增强
- **多加载器支持**: Forge/Fabric/Quilt全支持
- **智能验证**: Minecraft特定的翻译质量检查
- **安全回写**: JAR修改支持备份和回滚

### 开发效率
- **快速接入**: 新游戏支持仅需实现投影适配器
- **统一工作流**: 与Trans-Hub生态无缝集成
- **专业化**: 专注游戏特定的用户体验优化

---

## ⚠️ 风险与缓解

### 主要风险

1. **依赖风险**: 完全依赖Trans-Hub Core
   - **缓解**: SDK内置缓存，离线工作模式支持

2. **性能风险**: 网络调用可能影响响应时间
   - **缓解**: 智能缓存策略，批量操作优化

**无迁移风险**: 由于无生产环境，可直接重构，无数据迁移负担

**结论**: TH-Suite v2.0直接重构将彻底解决V6架构问题，通过文件重命名避免冗余，转型为专业的Trans-Hub生态应用。专注Minecraft特定功能优化，无迁移负担，通过Core-First架构实现更高的可靠性和可维护性。

### 📁 最终文件结构映射

**重构前 → 重构后**:
```
apps/mc_l10n/backend/services/content_addressing.py → apps/mc_l10n/src/adapters/core_client.py
apps/mc_l10n/backend/services/uida_service.py → apps/mc_l10n/src/adapters/projection.py
apps/mc_l10n/backend/processors/jar_processor.py → apps/mc_l10n/src/domain/jar_processor.py
apps/mc_l10n/backend/processors/mod_scanner.py → apps/mc_l10n/src/domain/mod_scanner.py
apps/mc_l10n/backend/workflows/ → apps/mc_l10n/src/services/
apps/mc_l10n/backend/database/ → 删除
apps/mc_l10n/backend/api/v6/ → 删除
```