// 插件沙箱和安全机制
// 提供插件运行时的安全约束和资源限制

use std::path::PathBuf;
use std::collections::HashSet;
use serde::{Deserialize, Serialize};
use anyhow::{Result, anyhow};

/// 沙箱配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SandboxConfig {
    /// 是否启用沙箱
    pub enabled: bool,
    /// 允许访问的路径白名单
    pub allowed_paths: Vec<PathBuf>,
    /// 禁止访问的路径黑名单
    pub blocked_paths: Vec<PathBuf>,
    /// 是否允许网络访问
    pub allow_network: bool,
    /// 允许的网络域名白名单
    pub allowed_domains: Vec<String>,
    /// 是否允许文件系统写入
    pub allow_file_write: bool,
    /// 是否允许执行系统命令
    pub allow_system_commands: bool,
    /// 内存限制 (MB)
    pub memory_limit_mb: usize,
    /// CPU时间限制 (秒)
    pub cpu_time_limit: u64,
    /// 是否启用签名验证
    pub signature_verification: bool,
    /// 是否允许未签名插件
    pub allow_unsigned: bool,
    /// 插件能力限制
    pub capability_restrictions: CapabilityRestrictions,
}

impl Default for SandboxConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            allowed_paths: vec![
                PathBuf::from("plugins"),
                PathBuf::from("data"),
                PathBuf::from("cache"),
                PathBuf::from("temp"),
            ],
            blocked_paths: vec![
                PathBuf::from("/system"),
                PathBuf::from("/etc"),
                PathBuf::from("/root"),
                PathBuf::from("C:\\Windows"),
                PathBuf::from("C:\\System32"),
            ],
            allow_network: false,
            allowed_domains: vec![],
            allow_file_write: false,
            allow_system_commands: false,
            memory_limit_mb: 256,
            cpu_time_limit: 30,
            signature_verification: true,
            allow_unsigned: false,
            capability_restrictions: CapabilityRestrictions::default(),
        }
    }
}

/// 插件能力限制
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityRestrictions {
    /// 允许的文件扩展名
    pub allowed_file_extensions: HashSet<String>,
    /// 最大文件大小 (字节)
    pub max_file_size: u64,
    /// 最大并发提取数量
    pub max_concurrent_extractions: usize,
    /// 是否允许访问注册表 (Windows)
    pub allow_registry_access: bool,
    /// 是否允许加载其他库
    pub allow_dynamic_loading: bool,
    /// 允许的系统调用白名单
    pub allowed_syscalls: Vec<String>,
}

impl Default for CapabilityRestrictions {
    fn default() -> Self {
        let mut allowed_extensions = HashSet::new();
        allowed_extensions.insert("jar".to_string());
        allowed_extensions.insert("zip".to_string());
        allowed_extensions.insert("json".to_string());
        allowed_extensions.insert("lang".to_string());
        allowed_extensions.insert("properties".to_string());

        Self {
            allowed_file_extensions: allowed_extensions,
            max_file_size: 100 * 1024 * 1024, // 100MB
            max_concurrent_extractions: 4,
            allow_registry_access: false,
            allow_dynamic_loading: false,
            allowed_syscalls: vec![
                "read".to_string(),
                "write".to_string(),
                "open".to_string(),
                "close".to_string(),
                "stat".to_string(),
            ],
        }
    }
}

/// 沙箱执行器
pub struct SandboxExecutor {
    config: SandboxConfig,
}

impl SandboxExecutor {
    /// 创建新的沙箱执行器
    pub fn new(config: SandboxConfig) -> Self {
        Self { config }
    }

    /// 验证文件访问权限
    pub fn validate_file_access(&self, file_path: &PathBuf, access_type: FileAccessType) -> Result<()> {
        if !self.config.enabled {
            return Ok(());
        }

        // 检查路径黑名单
        for blocked_path in &self.config.blocked_paths {
            if file_path.starts_with(blocked_path) {
                return Err(anyhow!("访问被禁止的路径: {:?}", file_path));
            }
        }

        // 检查路径白名单
        if !self.config.allowed_paths.is_empty() {
            let allowed = self.config.allowed_paths.iter()
                .any(|allowed_path| file_path.starts_with(allowed_path));
            
            if !allowed {
                return Err(anyhow!("路径不在白名单中: {:?}", file_path));
            }
        }

        // 检查文件扩展名
        if let Some(extension) = file_path.extension().and_then(|ext| ext.to_str()) {
            if !self.config.capability_restrictions.allowed_file_extensions.contains(extension) {
                return Err(anyhow!("不支持的文件扩展名: {}", extension));
            }
        }

        // 检查写入权限
        if matches!(access_type, FileAccessType::Write | FileAccessType::WriteCreate) {
            if !self.config.allow_file_write {
                return Err(anyhow!("文件写入被禁止"));
            }
        }

        // 检查文件大小
        if file_path.exists() {
            let metadata = std::fs::metadata(file_path)?;
            if metadata.len() > self.config.capability_restrictions.max_file_size {
                return Err(anyhow!("文件超过大小限制: {} bytes", metadata.len()));
            }
        }

        Ok(())
    }

    /// 验证网络访问权限
    pub fn validate_network_access(&self, domain: &str) -> Result<()> {
        if !self.config.enabled {
            return Ok(());
        }

        if !self.config.allow_network {
            return Err(anyhow!("网络访问被禁止"));
        }

        // 检查域名白名单
        if !self.config.allowed_domains.is_empty() {
            let allowed = self.config.allowed_domains.iter()
                .any(|allowed_domain| {
                    domain == allowed_domain || domain.ends_with(&format!(".{}", allowed_domain))
                });
            
            if !allowed {
                return Err(anyhow!("域名不在白名单中: {}", domain));
            }
        }

        Ok(())
    }

    /// 验证系统命令执行权限
    pub fn validate_system_command(&self, command: &str) -> Result<()> {
        if !self.config.enabled {
            return Ok(());
        }

        if !self.config.allow_system_commands {
            return Err(anyhow!("系统命令执行被禁止"));
        }

        // 检查危险命令
        let dangerous_commands = [
            "rm", "del", "format", "fdisk", "mkfs",
            "sudo", "su", "chmod", "chown",
            "curl", "wget", "nc", "netcat",
            "python", "node", "bash", "sh", "cmd", "powershell",
        ];

        for dangerous in &dangerous_commands {
            if command.contains(dangerous) {
                return Err(anyhow!("危险命令被禁止: {}", command));
            }
        }

        Ok(())
    }

    /// 创建资源监控器
    pub fn create_resource_monitor(&self) -> ResourceMonitor {
        ResourceMonitor::new(
            self.config.memory_limit_mb,
            self.config.cpu_time_limit,
        )
    }

    /// 验证插件签名
    pub fn validate_plugin_signature(&self, plugin_path: &PathBuf) -> Result<()> {
        if !self.config.enabled || !self.config.signature_verification {
            return Ok(());
        }

        // 检查是否允许未签名插件
        if self.config.allow_unsigned {
            log::warn!("允许加载未签名插件: {:?}", plugin_path);
            return Ok(());
        }

        // TODO: 实现实际的签名验证逻辑
        // 这里应该：
        // 1. 读取插件的数字签名
        // 2. 验证签名是否有效
        // 3. 检查签名证书是否来自可信CA
        // 4. 验证证书是否在有效期内

        log::debug!("验证插件签名: {:?}", plugin_path);

        // 目前返回错误，需要实际实现
        Err(anyhow!("插件签名验证功能尚未完全实现"))
    }

    /// 检查插件能力
    pub fn check_plugin_capabilities(&self, capabilities: &[String]) -> Result<Vec<String>> {
        let mut violations = Vec::new();

        for capability in capabilities {
            match capability.as_str() {
                "file_read" => {
                    // 读取文件通常是允许的
                }
                "file_write" => {
                    if !self.config.allow_file_write {
                        violations.push("文件写入被禁止".to_string());
                    }
                }
                "network_access" => {
                    if !self.config.allow_network {
                        violations.push("网络访问被禁止".to_string());
                    }
                }
                "system_commands" => {
                    if !self.config.allow_system_commands {
                        violations.push("系统命令执行被禁止".to_string());
                    }
                }
                "registry_access" => {
                    if !self.config.capability_restrictions.allow_registry_access {
                        violations.push("注册表访问被禁止".to_string());
                    }
                }
                "dynamic_loading" => {
                    if !self.config.capability_restrictions.allow_dynamic_loading {
                        violations.push("动态库加载被禁止".to_string());
                    }
                }
                _ => {
                    violations.push(format!("未知能力要求: {}", capability));
                }
            }
        }

        if violations.is_empty() {
            Ok(violations)
        } else {
            Err(anyhow!("插件能力检查失败: {:?}", violations))
        }
    }
}

/// 文件访问类型
#[derive(Debug, Clone)]
pub enum FileAccessType {
    Read,
    Write,
    WriteCreate,
    Execute,
}

/// 资源监控器
pub struct ResourceMonitor {
    memory_limit_mb: usize,
    cpu_time_limit: u64,
    start_time: std::time::Instant,
}

impl ResourceMonitor {
    /// 创建新的资源监控器
    pub fn new(memory_limit_mb: usize, cpu_time_limit: u64) -> Self {
        Self {
            memory_limit_mb,
            cpu_time_limit,
            start_time: std::time::Instant::now(),
        }
    }

    /// 检查CPU时间限制
    pub fn check_cpu_time(&self) -> Result<()> {
        let elapsed = self.start_time.elapsed().as_secs();
        if elapsed > self.cpu_time_limit {
            return Err(anyhow!("CPU时间超限: {}s (限制: {}s)", elapsed, self.cpu_time_limit));
        }
        Ok(())
    }

    /// 检查内存使用量
    pub fn check_memory_usage(&self) -> Result<()> {
        // 获取当前进程内存使用量
        #[cfg(target_os = "linux")]
        {
            if let Ok(status) = std::fs::read_to_string("/proc/self/status") {
                for line in status.lines() {
                    if line.starts_with("VmRSS:") {
                        if let Some(memory_str) = line.split_whitespace().nth(1) {
                            if let Ok(memory_kb) = memory_str.parse::<usize>() {
                                let memory_mb = memory_kb / 1024;
                                if memory_mb > self.memory_limit_mb {
                                    return Err(anyhow!("内存使用超限: {}MB (限制: {}MB)", 
                                        memory_mb, self.memory_limit_mb));
                                }
                            }
                        }
                    }
                }
            }
        }

        // 其他平台的内存检查可以使用sysinfo crate
        #[cfg(not(target_os = "linux"))]
        {
            // TODO: 实现Windows和macOS的内存检查
            log::debug!("内存监控在此平台上尚未实现");
        }

        Ok(())
    }

    /// 检查所有资源限制
    pub fn check_all_limits(&self) -> Result<()> {
        self.check_cpu_time()?;
        self.check_memory_usage()?;
        Ok(())
    }

    /// 获取资源使用统计
    pub fn get_usage_stats(&self) -> ResourceUsageStats {
        ResourceUsageStats {
            cpu_time_seconds: self.start_time.elapsed().as_secs(),
            memory_usage_mb: self.get_current_memory_usage(),
            cpu_time_limit: self.cpu_time_limit,
            memory_limit_mb: self.memory_limit_mb,
        }
    }

    /// 获取当前内存使用量
    fn get_current_memory_usage(&self) -> usize {
        #[cfg(target_os = "linux")]
        {
            if let Ok(status) = std::fs::read_to_string("/proc/self/status") {
                for line in status.lines() {
                    if line.starts_with("VmRSS:") {
                        if let Some(memory_str) = line.split_whitespace().nth(1) {
                            if let Ok(memory_kb) = memory_str.parse::<usize>() {
                                return memory_kb / 1024;
                            }
                        }
                    }
                }
            }
        }

        0 // 无法获取时返回0
    }
}

/// 资源使用统计
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceUsageStats {
    pub cpu_time_seconds: u64,
    pub memory_usage_mb: usize,
    pub cpu_time_limit: u64,
    pub memory_limit_mb: usize,
}

/// 安全策略验证器
pub struct SecurityPolicyValidator {
    config: SandboxConfig,
}

impl SecurityPolicyValidator {
    /// 创建新的安全策略验证器
    pub fn new(config: SandboxConfig) -> Self {
        Self { config }
    }

    /// 验证插件是否符合安全策略
    pub fn validate_plugin_security(&self, plugin_path: &PathBuf, capabilities: &[String]) -> Result<SecurityValidationResult> {
        let mut warnings = Vec::new();
        let mut errors = Vec::new();

        // 检查插件位置
        if let Err(e) = self.validate_plugin_location(plugin_path) {
            errors.push(e.to_string());
        }

        // 检查插件签名
        if let Err(e) = SandboxExecutor::new(self.config.clone()).validate_plugin_signature(plugin_path) {
            if self.config.allow_unsigned {
                warnings.push(format!("插件未签名但被允许加载: {}", e));
            } else {
                errors.push(e.to_string());
            }
        }

        // 检查插件能力
        if let Err(e) = SandboxExecutor::new(self.config.clone()).check_plugin_capabilities(capabilities) {
            errors.push(e.to_string());
        }

        // 检查文件权限
        if let Err(e) = self.validate_file_permissions(plugin_path) {
            warnings.push(e.to_string());
        }

        let risk_level = if !errors.is_empty() {
            RiskLevel::High
        } else if !warnings.is_empty() {
            RiskLevel::Medium
        } else {
            RiskLevel::Low
        };

        Ok(SecurityValidationResult {
            passed: errors.is_empty(),
            risk_level,
            errors,
            warnings,
        })
    }

    /// 验证插件位置
    fn validate_plugin_location(&self, plugin_path: &PathBuf) -> Result<()> {
        // 检查是否在系统目录中
        let system_dirs = [
            "/system", "/etc", "/usr/bin", "/sbin",
            "C:\\Windows", "C:\\System32", "C:\\Program Files",
        ];

        for system_dir in &system_dirs {
            if plugin_path.starts_with(system_dir) {
                return Err(anyhow!("插件位于系统目录中，可能不安全: {:?}", plugin_path));
            }
        }

        Ok(())
    }

    /// 验证文件权限
    fn validate_file_permissions(&self, plugin_path: &PathBuf) -> Result<()> {
        if let Ok(metadata) = std::fs::metadata(plugin_path) {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let mode = metadata.permissions().mode();
                
                // 检查是否所有人都可写 (危险)
                if mode & 0o002 != 0 {
                    return Err(anyhow!("插件文件所有人可写，存在安全风险"));
                }

                // 检查是否所有人都可执行
                if mode & 0o001 != 0 {
                    log::warn!("插件文件所有人可执行");
                }
            }
        }

        Ok(())
    }
}

/// 安全验证结果
#[derive(Debug, Clone)]
pub struct SecurityValidationResult {
    pub passed: bool,
    pub risk_level: RiskLevel,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

/// 风险等级
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    #[test]
    fn test_sandbox_config_default() {
        let config = SandboxConfig::default();
        assert!(config.enabled);
        assert!(!config.allow_network);
        assert!(!config.allow_file_write);
        assert!(!config.allow_system_commands);
    }

    #[test]
    fn test_file_access_validation() {
        let config = SandboxConfig::default();
        let executor = SandboxExecutor::new(config);
        
        let temp_dir = TempDir::new().unwrap();
        let test_file = temp_dir.path().join("test.jar");
        fs::write(&test_file, "test content").unwrap();
        
        // 这应该失败，因为临时目录不在白名单中
        let result = executor.validate_file_access(&test_file, FileAccessType::Read);
        assert!(result.is_err());
    }

    #[test]
    fn test_network_access_validation() {
        let mut config = SandboxConfig::default();
        config.allow_network = true;
        config.allowed_domains = vec!["example.com".to_string()];
        
        let executor = SandboxExecutor::new(config);
        
        // 允许的域名应该通过
        assert!(executor.validate_network_access("example.com").is_ok());
        assert!(executor.validate_network_access("sub.example.com").is_ok());
        
        // 不允许的域名应该失败
        assert!(executor.validate_network_access("malicious.com").is_err());
    }

    #[test]
    fn test_system_command_validation() {
        let mut config = SandboxConfig::default();
        config.allow_system_commands = true;
        
        let executor = SandboxExecutor::new(config);
        
        // 安全命令应该通过
        assert!(executor.validate_system_command("ls -la").is_ok());
        
        // 危险命令应该失败
        assert!(executor.validate_system_command("rm -rf /").is_err());
        assert!(executor.validate_system_command("sudo su").is_err());
    }

    #[test]
    fn test_resource_monitor() {
        let monitor = ResourceMonitor::new(512, 10);
        
        // 初始状态应该通过所有检查
        assert!(monitor.check_cpu_time().is_ok());
        assert!(monitor.check_memory_usage().is_ok());
        assert!(monitor.check_all_limits().is_ok());
        
        let stats = monitor.get_usage_stats();
        assert!(stats.cpu_time_seconds < stats.cpu_time_limit);
        assert!(stats.memory_usage_mb <= stats.memory_limit_mb);
    }

    #[test]
    fn test_capability_restrictions() {
        let restrictions = CapabilityRestrictions::default();
        
        assert!(restrictions.allowed_file_extensions.contains("jar"));
        assert!(restrictions.allowed_file_extensions.contains("zip"));
        assert!(!restrictions.allow_registry_access);
        assert!(!restrictions.allow_dynamic_loading);
    }
}