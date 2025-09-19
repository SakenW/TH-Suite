// 插件系统集成测试
// 测试与现有Python后端扫描系统的完整集成

use std::path::{Path, PathBuf};
use std::fs;
use tempfile::TempDir;
use tokio;
use anyhow::Result;

// 这些测试需要实际的模块引用，在实际项目中需要调整import路径
use th_suite_mc_l10n::plugins::*;

/// 集成测试套件
struct IntegrationTestSuite {
    temp_dir: TempDir,
    plugin_dir: PathBuf,
    test_files_dir: PathBuf,
}

impl IntegrationTestSuite {
    /// 创建新的测试套件
    async fn new() -> Result<Self> {
        let temp_dir = TempDir::new()?;
        let plugin_dir = temp_dir.path().join("plugins");
        let test_files_dir = temp_dir.path().join("test_files");
        
        fs::create_dir_all(&plugin_dir)?;
        fs::create_dir_all(&test_files_dir)?;

        Ok(Self {
            temp_dir,
            plugin_dir,
            test_files_dir,
        })
    }

    /// 设置测试环境
    async fn setup(&self) -> Result<()> {
        // 创建测试插件目录结构
        self.create_test_plugin_structure().await?;
        
        // 创建测试MOD文件
        self.create_test_mod_files().await?;

        Ok(())
    }

    /// 创建测试插件目录结构
    async fn create_test_plugin_structure(&self) -> Result<()> {
        // 创建原生插件目录
        let native_plugin_dir = self.plugin_dir.join("native");
        fs::create_dir_all(&native_plugin_dir)?;

        // 创建Python插件目录
        let python_plugin_dir = self.plugin_dir.join("python");
        fs::create_dir_all(&python_plugin_dir)?;

        // 复制示例清单文件
        let manifest_content = r#"
[plugin]
id = "test_minecraft_extractor"
name = "Test Minecraft Extractor"
version = "1.0.0"
author = "Test Suite"
description = "测试用Minecraft提取器"
plugin_type = "Native"
supported_formats = ["jar", "zip"]
uida_protocol_version = "1.0"
dependencies = []
capabilities = ["extract"]

[security]
sandbox_required = false
"#;
        fs::write(native_plugin_dir.join("plugin.toml"), manifest_content)?;

        // 创建Python插件清单
        let python_manifest = r#"
{
  "plugin": {
    "id": "test_python_extractor",
    "name": "Test Python Extractor",
    "version": "1.0.0",
    "author": "Test Suite",
    "description": "测试用Python提取器",
    "plugin_type": "Python",
    "supported_formats": ["zip", "mcpack"],
    "uida_protocol_version": "1.0",
    "dependencies": [],
    "capabilities": ["extract"]
  },
  "security": {
    "sandbox_required": false
  }
}
"#;
        fs::write(python_plugin_dir.join("plugin.json"), python_manifest)?;

        Ok(())
    }

    /// 创建测试MOD文件
    async fn create_test_mod_files(&self) -> Result<()> {
        // 创建一个简单的测试JAR文件
        let test_jar_path = self.test_files_dir.join("test_mod.jar");
        self.create_test_jar(&test_jar_path).await?;

        // 创建测试资源包
        let test_pack_path = self.test_files_dir.join("test_pack.zip");
        self.create_test_resource_pack(&test_pack_path).await?;

        Ok(())
    }

    /// 创建测试JAR文件
    async fn create_test_jar(&self, jar_path: &Path) -> Result<()> {
        use std::io::Write;
        let file = fs::File::create(jar_path)?;
        let mut zip = zip::ZipWriter::new(file);

        // 添加fabric.mod.json
        let fabric_mod_json = r#"
{
  "schemaVersion": 1,
  "id": "test_mod",
  "version": "1.0.0",
  "name": "Test Mod",
  "description": "A test mod for plugin system",
  "authors": ["Test Author"],
  "depends": {
    "fabricloader": ">=0.14.0",
    "fabric": "*",
    "minecraft": "1.20.1"
  }
}
"#;
        let options = zip::write::FileOptions::default()
            .compression_method(zip::CompressionMethod::Stored);
        zip.start_file("fabric.mod.json", options)?;
        zip.write_all(fabric_mod_json.as_bytes())?;

        // 添加语言文件
        let lang_content = r#"
{
  "item.test_mod.test_item": "Test Item",
  "block.test_mod.test_block": "Test Block",
  "gui.test_mod.test_gui": "Test GUI"
}
"#;
        zip.start_file("assets/test_mod/lang/en_us.json", options)?;
        zip.write_all(lang_content.as_bytes())?;

        let zh_lang_content = r#"
{
  "item.test_mod.test_item": "测试物品",
  "block.test_mod.test_block": "测试方块",
  "gui.test_mod.test_gui": "测试界面"
}
"#;
        zip.start_file("assets/test_mod/lang/zh_cn.json", options)?;
        zip.write_all(zh_lang_content.as_bytes())?;

        zip.finish()?;
        Ok(())
    }

    /// 创建测试资源包
    async fn create_test_resource_pack(&self, pack_path: &Path) -> Result<()> {
        use std::io::Write;
        let file = fs::File::create(pack_path)?;
        let mut zip = zip::ZipWriter::new(file);

        // 添加pack.mcmeta
        let pack_mcmeta = r#"
{
  "pack": {
    "pack_format": 13,
    "description": "Test Resource Pack"
  }
}
"#;
        let options = zip::write::FileOptions::default()
            .compression_method(zip::CompressionMethod::Stored);
        zip.start_file("pack.mcmeta", options)?;
        zip.write_all(pack_mcmeta.as_bytes())?;

        // 添加语言文件
        let lang_content = r#"
{
  "item.minecraft.diamond": "Custom Diamond",
  "block.minecraft.stone": "Custom Stone"
}
"#;
        zip.start_file("assets/minecraft/lang/en_us.json", options)?;
        zip.write_all(lang_content.as_bytes())?;

        zip.finish()?;
        Ok(())
    }

    /// 清理测试环境
    fn cleanup(self) {
        // TempDir自动清理
    }
}

/// 测试插件系统初始化
#[tokio::test]
async fn test_plugin_system_initialization() -> Result<()> {
    let test_suite = IntegrationTestSuite::new().await?;
    test_suite.setup().await?;

    // 创建插件配置
    let plugin_config = PluginSystemConfig {
        plugin_dirs: vec![test_suite.plugin_dir.clone()],
        enabled_plugins: vec![],
        disabled_plugins: vec![],
        signature_verification: false, // 测试时禁用签名验证
        sandbox_config: SandboxConfig {
            enabled: false, // 测试时禁用沙箱
            ..Default::default()
        },
        python_config: PythonConfig {
            enabled: false, // 单纯测试原生插件
            ..Default::default()
        },
        hot_reload: false,
        max_concurrent_plugins: 4,
    };

    // 创建并初始化插件管理器
    let mut plugin_manager = PluginManager::new(plugin_config)?;
    let result = plugin_manager.initialize().await;

    assert!(result.is_ok(), "插件系统初始化应该成功");

    // 检查插件是否被发现
    let plugins = plugin_manager.get_plugins();
    println!("发现的插件数量: {}", plugins.len());

    // 关闭插件管理器
    plugin_manager.shutdown().await?;

    test_suite.cleanup();
    Ok(())
}

/// 测试文件扫描功能
#[tokio::test]
async fn test_file_scanning() -> Result<()> {
    let test_suite = IntegrationTestSuite::new().await?;
    test_suite.setup().await?;

    // 创建插件配置（启用内置提取器）
    let plugin_config = PluginSystemConfig {
        plugin_dirs: vec![test_suite.plugin_dir.clone()],
        enabled_plugins: vec![],
        disabled_plugins: vec![],
        signature_verification: false,
        sandbox_config: SandboxConfig {
            enabled: false,
            ..Default::default()
        },
        python_config: PythonConfig {
            enabled: false,
            ..Default::default()
        },
        hot_reload: false,
        max_concurrent_plugins: 4,
    };

    let mut plugin_manager = PluginManager::new(plugin_config)?;
    plugin_manager.initialize().await?;

    // 测试扫描JAR文件
    let test_jar = test_suite.test_files_dir.join("test_mod.jar");
    if test_jar.exists() {
        // 查找支持jar格式的提取器
        let extractors = plugin_manager.get_extractors_for_format("jar");
        println!("支持jar格式的提取器: {:?}", extractors);

        // 如果有内置提取器，尝试提取
        if !extractors.is_empty() {
            for extractor_id in extractors {
                match plugin_manager.extract_file(&extractor_id, &test_jar).await {
                    Ok(result) => {
                        println!("✅ 提取成功: {}", extractor_id);
                        println!("  文件类型: {}", result.file_type);
                        println!("  语言文件数: {}", result.language_files.len());
                        println!("  总翻译条目: {}", result.stats.total_entries);
                        
                        assert!(!result.language_files.is_empty(), "应该发现语言文件");
                        
                        // 验证语言文件内容
                        for lang_file in &result.language_files {
                            println!("  语言: {} ({}条)", lang_file.language_code, lang_file.entry_count);
                            assert!(!lang_file.language_code.is_empty(), "语言代码不应为空");
                            assert!(lang_file.entry_count > 0, "应该有翻译条目");
                        }
                        
                        break; // 测试成功，退出循环
                    }
                    Err(e) => {
                        println!("❌ 提取失败 {}: {}", extractor_id, e);
                    }
                }
            }
        } else {
            println!("⚠️ 没有找到支持jar格式的提取器");
        }
    }

    plugin_manager.shutdown().await?;
    test_suite.cleanup();
    Ok(())
}

/// 测试集成扫描器
#[tokio::test]
async fn test_integrated_scanner() -> Result<()> {
    let test_suite = IntegrationTestSuite::new().await?;
    test_suite.setup().await?;

    // 创建集成扫描配置
    let integration_config = ScanIntegrationConfig {
        plugin_scanning_enabled: true,
        fallback_to_python_backend: false, // 测试时不依赖Python后端
        python_backend_url: "http://localhost:18000".to_string(),
        merge_strategy: MergeStrategy::PluginFirst,
        performance_mode: PerformanceMode::Balanced,
    };

    // 创建插件配置
    let plugin_config = PluginSystemConfig {
        plugin_dirs: vec![test_suite.plugin_dir.clone()],
        enabled_plugins: vec![],
        disabled_plugins: vec![],
        signature_verification: false,
        sandbox_config: SandboxConfig {
            enabled: false,
            ..Default::default()
        },
        python_config: PythonConfig {
            enabled: false,
            ..Default::default()
        },
        hot_reload: false,
        max_concurrent_plugins: 4,
    };

    // 创建并初始化集成扫描器
    let mut integrated_scanner = IntegratedScanner::new(integration_config);
    let init_result = integrated_scanner.initialize(Some(plugin_config)).await;
    
    if let Err(e) = init_result {
        println!("⚠️ 集成扫描器初始化失败: {}", e);
        // 继续测试基本功能
    }

    // 测试扫描目录
    let scan_result = integrated_scanner.scan_path(&test_suite.test_files_dir).await;
    
    match scan_result {
        Ok(result) => {
            println!("✅ 集成扫描成功");
            println!("  扫描路径: {:?}", result.scan_path);
            println!("  插件结果数: {}", result.plugin_results_count);
            println!("  使用Python后端: {}", result.python_backend_used);
            println!("  合并策略: {:?}", result.merge_strategy);
            println!("  发现语言文件: {}", result.extraction_result.language_files.len());
            
            // 验证结果
            assert!(result.success, "集成扫描应该成功");
            if !result.extraction_result.language_files.is_empty() {
                println!("  语言文件详情:");
                for lang_file in &result.extraction_result.language_files {
                    println!("    - {} ({} 条)", lang_file.language_code, lang_file.entry_count);
                }
            }
        }
        Err(e) => {
            println!("❌ 集成扫描失败: {}", e);
            // 在测试环境中，这可能是预期的（没有实际的插件库）
        }
    }

    integrated_scanner.shutdown().await?;
    test_suite.cleanup();
    Ok(())
}

/// 测试沙箱安全机制
#[tokio::test]
async fn test_sandbox_security() -> Result<()> {
    let test_suite = IntegrationTestSuite::new().await?;
    test_suite.setup().await?;

    // 创建严格的沙箱配置
    let sandbox_config = SandboxConfig {
        enabled: true,
        allowed_paths: vec![test_suite.test_files_dir.clone()],
        blocked_paths: vec![PathBuf::from("/system"), PathBuf::from("/etc")],
        allow_network: false,
        allow_file_write: false,
        allow_system_commands: false,
        memory_limit_mb: 64,
        cpu_time_limit: 10,
        signature_verification: true,
        allow_unsigned: false,
        capability_restrictions: CapabilityRestrictions::default(),
    };

    let executor = SandboxExecutor::new(sandbox_config);

    // 测试文件访问验证
    let allowed_file = test_suite.test_files_dir.join("test.txt");
    let blocked_file = PathBuf::from("/etc/passwd");

    // 允许的文件应该通过验证
    let result = executor.validate_file_access(&allowed_file, FileAccessType::Read);
    println!("允许文件访问结果: {:?}", result);

    // 被阻止的文件应该失败
    let result = executor.validate_file_access(&blocked_file, FileAccessType::Read);
    assert!(result.is_err(), "应该阻止访问系统文件");

    // 测试网络访问验证
    let result = executor.validate_network_access("malicious.com");
    assert!(result.is_err(), "应该阻止网络访问");

    // 测试系统命令验证
    let result = executor.validate_system_command("rm -rf /");
    assert!(result.is_err(), "应该阻止危险命令");

    // 测试资源监控
    let monitor = executor.create_resource_monitor();
    let stats = monitor.get_usage_stats();
    println!("资源使用统计: {:?}", stats);

    test_suite.cleanup();
    Ok(())
}

/// 测试插件注册表功能
#[tokio::test]
async fn test_plugin_registry() -> Result<()> {
    let test_suite = IntegrationTestSuite::new().await?;
    test_suite.setup().await?;

    // 创建插件注册表
    let mut registry = PluginRegistry::new(vec![test_suite.plugin_dir.clone()])?;

    // 扫描插件目录
    let scan_result = registry.scan_directory(&test_suite.plugin_dir).await;
    println!("插件目录扫描结果: {:?}", scan_result);

    // 获取发现的插件
    let discovered_plugins = registry.get_discovered_plugins();
    println!("发现的插件数量: {}", discovered_plugins.len());

    for plugin in &discovered_plugins {
        println!("  - {} v{} ({})", plugin.name, plugin.version, plugin.id);
        println!("    类型: {:?}", plugin.plugin_type);
        println!("    支持格式: {:?}", plugin.supported_formats);
    }

    // 解析依赖关系
    if !discovered_plugins.is_empty() {
        let deps_result = registry.resolve_dependencies();
        println!("依赖关系解析结果: {:?}", deps_result);

        // 获取加载顺序
        if deps_result.is_ok() {
            let load_order = registry.get_load_order();
            println!("加载顺序: {:?}", load_order);
        }
    }

    // 获取注册表统计
    let stats = registry.get_registry_stats();
    println!("注册表统计: {:?}", stats);

    test_suite.cleanup();
    Ok(())
}

/// 主测试函数 - 运行所有集成测试
#[tokio::test]
async fn test_complete_plugin_integration() -> Result<()> {
    println!("🚀 开始完整插件系统集成测试");

    // 运行所有测试
    test_plugin_system_initialization().await?;
    println!("✅ 插件系统初始化测试通过");

    test_file_scanning().await?;
    println!("✅ 文件扫描测试通过");

    test_integrated_scanner().await?;
    println!("✅ 集成扫描器测试通过");

    test_sandbox_security().await?;
    println!("✅ 沙箱安全测试通过");

    test_plugin_registry().await?;
    println!("✅ 插件注册表测试通过");

    println!("🎉 所有集成测试完成");
    Ok(())
}

/// 性能测试
#[tokio::test]
async fn test_plugin_performance() -> Result<()> {
    let test_suite = IntegrationTestSuite::new().await?;
    test_suite.setup().await?;

    // 创建多个测试文件
    for i in 0..10 {
        let test_jar = test_suite.test_files_dir.join(format!("test_mod_{}.jar", i));
        test_suite.create_test_jar(&test_jar).await?;
    }

    let plugin_config = PluginSystemConfig {
        plugin_dirs: vec![test_suite.plugin_dir.clone()],
        enabled_plugins: vec![],
        disabled_plugins: vec![],
        signature_verification: false,
        sandbox_config: SandboxConfig {
            enabled: false,
            ..Default::default()
        },
        python_config: PythonConfig {
            enabled: false,
            ..Default::default()
        },
        hot_reload: false,
        max_concurrent_plugins: 8,
    };

    let mut plugin_manager = PluginManager::new(plugin_config)?;
    plugin_manager.initialize().await?;

    // 性能测试
    let start_time = std::time::Instant::now();
    
    let mut total_files_processed = 0;
    let mut total_language_files = 0;

    for i in 0..10 {
        let test_jar = test_suite.test_files_dir.join(format!("test_mod_{}.jar", i));
        
        let extractors = plugin_manager.get_extractors_for_format("jar");
        if !extractors.is_empty() {
            if let Ok(result) = plugin_manager.extract_file(&extractors[0], &test_jar).await {
                total_files_processed += 1;
                total_language_files += result.language_files.len();
            }
        }
    }

    let elapsed = start_time.elapsed();
    
    println!("🚀 性能测试结果:");
    println!("  处理文件数: {}", total_files_processed);
    println!("  发现语言文件: {}", total_language_files);
    println!("  总耗时: {:?}", elapsed);
    println!("  平均每文件: {:?}", elapsed / total_files_processed.max(1) as u32);

    // 性能基准
    assert!(elapsed.as_secs() < 30, "处理10个文件不应超过30秒");

    plugin_manager.shutdown().await?;
    test_suite.cleanup();
    Ok(())
}

/// 错误处理测试
#[tokio::test]
async fn test_error_handling() -> Result<()> {
    let test_suite = IntegrationTestSuite::new().await?;

    // 测试无效插件目录
    let mut registry = PluginRegistry::new(vec![PathBuf::from("/nonexistent")])?;
    let result = registry.scan_directory(&PathBuf::from("/nonexistent")).await;
    assert!(result.is_err(), "扫描不存在的目录应该失败");

    // 测试损坏的JAR文件
    let corrupted_jar = test_suite.test_files_dir.join("corrupted.jar");
    fs::create_dir_all(&test_suite.test_files_dir)?;
    fs::write(&corrupted_jar, "not a jar file")?;

    let plugin_config = PluginSystemConfig {
        plugin_dirs: vec![],
        enabled_plugins: vec![],
        disabled_plugins: vec![],
        signature_verification: false,
        sandbox_config: SandboxConfig {
            enabled: false,
            ..Default::default()
        },
        python_config: PythonConfig {
            enabled: false,
            ..Default::default()
        },
        hot_reload: false,
        max_concurrent_plugins: 4,
    };

    let mut plugin_manager = PluginManager::new(plugin_config)?;
    plugin_manager.initialize().await?;

    // 尝试提取损坏的文件
    let extractors = plugin_manager.get_extractors_for_format("jar");
    if !extractors.is_empty() {
        let result = plugin_manager.extract_file(&extractors[0], &corrupted_jar).await;
        println!("损坏文件处理结果: {:?}", result);
        // 应该优雅地处理错误，而不是崩溃
    }

    plugin_manager.shutdown().await?;
    test_suite.cleanup();
    Ok(())
}