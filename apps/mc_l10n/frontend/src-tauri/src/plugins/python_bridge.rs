// Python子进程插件桥接
// 支持通过子进程运行Python插件，避免在GUI线程中运行解释器

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio, Child};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tokio::process::Command as TokioCommand;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader, BufWriter};
use serde::{Serialize, Deserialize};
use anyhow::{Result, anyhow};
use crate::plugins::{Extractor, ExtractionResult, ExtractorInfo};
use async_trait::async_trait;

/// Python配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonConfig {
    /// 是否启用Python插件支持
    pub enabled: bool,
    /// Python解释器路径
    pub python_executable: PathBuf,
    /// 虚拟环境路径
    pub virtual_env_path: Option<PathBuf>,
    /// Python插件目录
    pub plugin_dir: PathBuf,
    /// 子进程超时 (秒)
    pub subprocess_timeout: u64,
    /// 最大并发Python进程数
    pub max_concurrent_processes: usize,
    /// 内存限制 (MB)
    pub memory_limit_mb: usize,
    /// CPU时间限制 (秒)
    pub cpu_time_limit: u64,
    /// 是否启用沙箱模式
    pub sandbox_mode: bool,
}

impl Default for PythonConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            python_executable: PathBuf::from("python3"),
            virtual_env_path: None,
            plugin_dir: PathBuf::from("plugins/python"),
            subprocess_timeout: 30,
            max_concurrent_processes: 4,
            memory_limit_mb: 256,
            cpu_time_limit: 10,
            sandbox_mode: true,
        }
    }
}

/// JSON-RPC消息格式
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: u64,
    pub method: String,
    pub params: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: u64,
    pub result: Option<serde_json::Value>,
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    pub data: Option<serde_json::Value>,
}

/// Python进程状态
#[derive(Debug, Clone)]
pub enum ProcessStatus {
    Starting,
    Ready,
    Busy,
    Error(String),
    Stopped,
}

/// Python插件进程
pub struct PythonPluginProcess {
    plugin_id: String,
    child: Child,
    status: ProcessStatus,
    stdin: Option<BufWriter<tokio::process::ChildStdin>>,
    stdout: Option<BufReader<tokio::process::ChildStdout>>,
    next_request_id: u64,
    started_at: chrono::DateTime<chrono::Utc>,
    last_used: chrono::DateTime<chrono::Utc>,
}

impl PythonPluginProcess {
    /// 创建新的Python插件进程
    pub async fn new(plugin_id: String, plugin_path: &Path, config: &PythonConfig) -> Result<Self> {
        log::info!("🐍 启动Python插件进程: {}", plugin_id);

        // 构建Python命令
        let mut cmd = TokioCommand::new(&config.python_executable);
        
        // 如果有虚拟环境，激活它
        if let Some(venv_path) = &config.virtual_env_path {
            let python_path = if cfg!(target_os = "windows") {
                venv_path.join("Scripts").join("python.exe")
            } else {
                venv_path.join("bin").join("python")
            };
            cmd = TokioCommand::new(python_path);
        }

        // 添加插件运行器参数
        cmd.arg("-u") // 无缓冲输出
            .arg(plugin_path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        // 沙箱模式：设置环境变量限制
        if config.sandbox_mode {
            cmd.env("PYTHONDONTWRITEBYTECODE", "1")
                .env("PYTHONPATH", "")
                .env("TH_PLUGIN_SANDBOX", "1");
        }

        // 启动进程
        let mut child = cmd.spawn()
            .map_err(|e| anyhow!("无法启动Python进程: {}", e))?;

        // 获取stdin和stdout
        let stdin = child.stdin.take()
            .ok_or_else(|| anyhow!("无法获取Python进程stdin"))?;
        let stdout = child.stdout.take()
            .ok_or_else(|| anyhow!("无法获取Python进程stdout"))?;

        let stdin = BufWriter::new(stdin);
        let stdout = BufReader::new(stdout);

        let mut process = Self {
            plugin_id,
            child,
            status: ProcessStatus::Starting,
            stdin: Some(stdin),
            stdout: Some(stdout),
            next_request_id: 1,
            started_at: chrono::Utc::now(),
            last_used: chrono::Utc::now(),
        };

        // 初始化插件
        process.initialize().await?;

        log::info!("✅ Python插件进程启动成功: {}", process.plugin_id);
        Ok(process)
    }

    /// 初始化插件
    async fn initialize(&mut self) -> Result<()> {
        self.status = ProcessStatus::Starting;
        
        // 发送初始化请求
        let response = self.send_request("initialize", serde_json::json!({})).await?;
        
        if response.error.is_some() {
            let error_msg = response.error.unwrap().message;
            self.status = ProcessStatus::Error(error_msg.clone());
            return Err(anyhow!("插件初始化失败: {}", error_msg));
        }

        self.status = ProcessStatus::Ready;
        Ok(())
    }

    /// 发送JSON-RPC请求
    pub async fn send_request(&mut self, method: &str, params: serde_json::Value) -> Result<JsonRpcResponse> {
        if matches!(self.status, ProcessStatus::Error(_) | ProcessStatus::Stopped) {
            return Err(anyhow!("Python进程不可用: {:?}", self.status));
        }

        let request_id = self.next_request_id;
        self.next_request_id += 1;

        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: request_id,
            method: method.to_string(),
            params,
        };

        // 发送请求
        let request_json = serde_json::to_string(&request)?;
        log::debug!("发送Python RPC请求: {}", request_json);

        if let Some(ref mut stdin) = self.stdin {
            stdin.write_all(request_json.as_bytes()).await?;
            stdin.write_all(b"\n").await?;
            stdin.flush().await?;
        } else {
            return Err(anyhow!("Python进程stdin不可用"));
        }

        // 接收响应
        if let Some(ref mut stdout) = self.stdout {
            let mut response_line = String::new();
            stdout.read_line(&mut response_line).await?;
            
            log::debug!("接收Python RPC响应: {}", response_line.trim());
            
            let response: JsonRpcResponse = serde_json::from_str(&response_line)?;
            
            if response.id != request_id {
                return Err(anyhow!("响应ID不匹配: 期望 {}, 收到 {}", request_id, response.id));
            }

            self.last_used = chrono::Utc::now();
            Ok(response)
        } else {
            Err(anyhow!("Python进程stdout不可用"))
        }
    }

    /// 检查进程是否运行
    pub fn is_running(&mut self) -> bool {
        match self.child.try_wait() {
            Ok(Some(_)) => {
                self.status = ProcessStatus::Stopped;
                false
            }
            Ok(None) => true,
            Err(_) => {
                self.status = ProcessStatus::Error("进程状态检查失败".to_string());
                false
            }
        }
    }

    /// 终止进程
    pub async fn terminate(&mut self) -> Result<()> {
        log::info!("🛑 终止Python插件进程: {}", self.plugin_id);

        // 尝试优雅关闭
        if let Ok(_) = self.send_request("shutdown", serde_json::json!({})).await {
            // 等待进程自然退出
            tokio::time::timeout(
                std::time::Duration::from_secs(5),
                self.child.wait()
            ).await.ok();
        }

        // 强制终止
        if self.is_running() {
            self.child.kill().await?;
        }

        self.status = ProcessStatus::Stopped;
        Ok(())
    }

    /// 获取进程统计信息
    pub fn get_stats(&self) -> ProcessStats {
        ProcessStats {
            plugin_id: self.plugin_id.clone(),
            status: self.status.clone(),
            uptime_seconds: (chrono::Utc::now() - self.started_at).num_seconds() as u64,
            idle_seconds: (chrono::Utc::now() - self.last_used).num_seconds() as u64,
        }
    }
}

/// 进程统计信息
#[derive(Debug, Clone)]
pub struct ProcessStats {
    pub plugin_id: String,
    pub status: ProcessStatus,
    pub uptime_seconds: u64,
    pub idle_seconds: u64,
}

/// Python桥接器
pub struct PythonBridge {
    config: PythonConfig,
    processes: Arc<Mutex<HashMap<String, PythonPluginProcess>>>,
    semaphore: Arc<tokio::sync::Semaphore>,
}

impl PythonBridge {
    /// 创建新的Python桥接器
    pub fn new(config: PythonConfig) -> Result<Self> {
        let semaphore = Arc::new(tokio::sync::Semaphore::new(config.max_concurrent_processes));

        Ok(Self {
            config,
            processes: Arc::new(Mutex::new(HashMap::new())),
            semaphore,
        })
    }

    /// 初始化Python环境
    pub async fn initialize(&mut self) -> Result<()> {
        log::info!("🐍 初始化Python桥接环境");

        // 验证Python解释器
        self.validate_python_environment().await?;

        // 创建插件目录
        if !self.config.plugin_dir.exists() {
            std::fs::create_dir_all(&self.config.plugin_dir)?;
        }

        // 安装必要的依赖
        self.install_dependencies().await?;

        log::info!("✅ Python桥接环境初始化完成");
        Ok(())
    }

    /// 验证Python环境
    async fn validate_python_environment(&self) -> Result<()> {
        let output = TokioCommand::new(&self.config.python_executable)
            .arg("--version")
            .output()
            .await?;

        if !output.status.success() {
            return Err(anyhow!("Python解释器不可用: {:?}", self.config.python_executable));
        }

        let version = String::from_utf8_lossy(&output.stdout);
        log::info!("Python版本: {}", version.trim());

        // 检查最低版本要求
        if !version.contains("Python 3.") {
            return Err(anyhow!("需要Python 3.x版本，当前: {}", version.trim()));
        }

        Ok(())
    }

    /// 安装必要的依赖
    async fn install_dependencies(&self) -> Result<()> {
        log::info!("📦 检查Python依赖...");

        // 检查必要的包
        let required_packages = vec!["json", "sys", "os", "asyncio"];
        
        for package in required_packages {
            let output = TokioCommand::new(&self.config.python_executable)
                .arg("-c")
                .arg(format!("import {}", package))
                .output()
                .await?;

            if !output.status.success() {
                log::warn!("Python包缺失: {}", package);
            }
        }

        Ok(())
    }

    /// 加载Python插件
    pub async fn load_python_extractor(&mut self, plugin_id: &str, plugin_path: &Path) -> Result<Box<dyn Extractor + Send + Sync>> {
        log::info!("📜 加载Python插件: {}", plugin_id);

        // 检查插件文件
        if !plugin_path.exists() {
            return Err(anyhow!("Python插件文件不存在: {:?}", plugin_path));
        }

        // 创建包装的提取器
        let extractor = PythonExtractorWrapper::new(
            plugin_id.to_string(),
            plugin_path.to_path_buf(),
            self.config.clone(),
            self.processes.clone(),
            self.semaphore.clone(),
        )?;

        Ok(Box::new(extractor))
    }

    /// 卸载插件
    pub async fn unload_plugin(&mut self, plugin_id: &str) -> Result<()> {
        log::info!("🗑️ 卸载Python插件: {}", plugin_id);

        let mut processes = self.processes.lock().unwrap();
        if let Some(mut process) = processes.remove(plugin_id) {
            drop(processes); // 释放锁
            process.terminate().await?;
        }

        Ok(())
    }

    /// 获取所有进程统计信息
    pub fn get_process_stats(&self) -> Vec<ProcessStats> {
        let mut processes = self.processes.lock().unwrap();
        processes.values_mut()
            .map(|process| process.get_stats())
            .collect()
    }

    /// 清理闲置进程
    pub async fn cleanup_idle_processes(&self, max_idle_seconds: u64) -> Result<usize> {
        let plugin_ids_to_remove: Vec<String> = {
            let mut processes = self.processes.lock().unwrap();
            processes.iter_mut()
                .filter(|(_, process)| {
                    let stats = process.get_stats();
                    stats.idle_seconds > max_idle_seconds
                })
                .map(|(id, _)| id.clone())
                .collect()
        };

        let mut removed_count = 0;
        for plugin_id in plugin_ids_to_remove {
            if let Err(e) = self.unload_plugin(&plugin_id).await {
                log::error!("清理闲置进程失败 {}: {}", plugin_id, e);
            } else {
                removed_count += 1;
            }
        }

        if removed_count > 0 {
            log::info!("🧹 清理了 {} 个闲置Python进程", removed_count);
        }

        Ok(removed_count)
    }

    /// 关闭所有进程
    pub async fn shutdown(&mut self) -> Result<()> {
        log::info!("🛑 关闭所有Python进程...");

        let plugin_ids: Vec<String> = {
            let processes = self.processes.lock().unwrap();
            processes.keys().cloned().collect()
        };

        for plugin_id in plugin_ids {
            if let Err(e) = self.unload_plugin(&plugin_id).await {
                log::error!("关闭Python进程失败 {}: {}", plugin_id, e);
            }
        }

        log::info!("✅ 所有Python进程已关闭");
        Ok(())
    }
}

/// Python提取器包装器
/// 实现Extractor trait，将调用转发给Python子进程
pub struct PythonExtractorWrapper {
    plugin_id: String,
    plugin_path: PathBuf,
    config: PythonConfig,
    processes: Arc<Mutex<HashMap<String, PythonPluginProcess>>>,
    semaphore: Arc<tokio::sync::Semaphore>,
}

impl PythonExtractorWrapper {
    pub fn new(
        plugin_id: String,
        plugin_path: PathBuf,
        config: PythonConfig,
        processes: Arc<Mutex<HashMap<String, PythonPluginProcess>>>,
        semaphore: Arc<tokio::sync::Semaphore>,
    ) -> Result<Self> {
        Ok(Self {
            plugin_id,
            plugin_path,
            config,
            processes,
            semaphore,
        })
    }

    /// 获取或创建Python进程
    async fn get_or_create_process(&self) -> Result<()> {
        let mut processes = self.processes.lock().unwrap();
        
        if !processes.contains_key(&self.plugin_id) {
            drop(processes); // 释放锁
            
            // 获取信号量许可
            let _permit = self.semaphore.acquire().await?;
            
            // 创建新进程
            let process = PythonPluginProcess::new(
                self.plugin_id.clone(),
                &self.plugin_path,
                &self.config,
            ).await?;

            let mut processes = self.processes.lock().unwrap();
            processes.insert(self.plugin_id.clone(), process);
        }

        Ok(())
    }

    /// 发送请求到Python进程
    async fn send_request(&self, method: &str, params: serde_json::Value) -> Result<JsonRpcResponse> {
        self.get_or_create_process().await?;

        let mut processes = self.processes.lock().unwrap();
        if let Some(process) = processes.get_mut(&self.plugin_id) {
            // 检查进程状态
            if !process.is_running() {
                return Err(anyhow!("Python进程已停止"));
            }

            process.send_request(method, params).await
        } else {
            Err(anyhow!("Python进程不存在"))
        }
    }
}

#[async_trait]
impl Extractor for PythonExtractorWrapper {
    async fn supports(&self, file_path: &Path) -> Result<bool> {
        let params = serde_json::json!({
            "file_path": file_path.to_string_lossy()
        });

        let response = self.send_request("supports", params).await?;

        if let Some(error) = response.error {
            return Err(anyhow!("Python插件错误: {}", error.message));
        }

        response.result
            .and_then(|v| v.as_bool())
            .ok_or_else(|| anyhow!("无效的响应格式"))
    }

    async fn extract(&self, file_path: &Path) -> Result<ExtractionResult> {
        let params = serde_json::json!({
            "file_path": file_path.to_string_lossy()
        });

        let response = self.send_request("extract", params).await?;

        if let Some(error) = response.error {
            return Err(anyhow!("Python插件错误: {}", error.message));
        }

        response.result
            .ok_or_else(|| anyhow!("没有返回结果"))
            .and_then(|v| serde_json::from_value(v).map_err(|e| anyhow!("反序列化失败: {}", e)))
    }

    fn get_info(&self) -> ExtractorInfo {
        // 这里返回基本信息，实际信息需要从Python进程获取
        ExtractorInfo {
            name: format!("Python Plugin: {}", self.plugin_id),
            version: "1.0.0".to_string(),
            author: "Python Plugin".to_string(),
            description: format!("Python插件包装器: {}", self.plugin_path.display()),
            supported_formats: vec![], // 需要从Python进程获取
        }
    }

    fn supported_extensions(&self) -> Vec<String> {
        // 需要从Python进程获取，这里返回空
        vec![]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_python_config_default() {
        let config = PythonConfig::default();
        assert!(config.enabled);
        assert_eq!(config.subprocess_timeout, 30);
        assert_eq!(config.max_concurrent_processes, 4);
    }

    #[test]
    fn test_json_rpc_serialization() {
        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: 1,
            method: "test".to_string(),
            params: serde_json::json!({"key": "value"}),
        };

        let json = serde_json::to_string(&request).unwrap();
        let deserialized: JsonRpcRequest = serde_json::from_str(&json).unwrap();
        
        assert_eq!(request.jsonrpc, deserialized.jsonrpc);
        assert_eq!(request.id, deserialized.id);
        assert_eq!(request.method, deserialized.method);
    }

    #[tokio::test]
    async fn test_python_bridge_creation() {
        let config = PythonConfig::default();
        let bridge = PythonBridge::new(config);
        assert!(bridge.is_ok());
    }
}