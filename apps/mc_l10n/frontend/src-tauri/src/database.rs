// database.rs - SQLCipher加密数据库服务层
use crate::crypto::{SecurityConfig, EncryptionKey};
use rusqlite::{Connection, OpenFlags, params};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use anyhow::{Result, anyhow, Context};
use serde::{Serialize, Deserialize};
use log::{info, warn, error, debug};
use tokio::sync::RwLock;
use std::collections::HashMap;

/// 数据库连接配置
#[derive(Debug, Clone)]
pub struct DatabaseConfig {
    /// 数据库文件路径
    pub database_path: PathBuf,
    /// 是否启用WAL模式
    pub enable_wal: bool,
    /// 页面大小（SQLCipher优化）
    pub page_size: u32,
    /// 缓存大小（页数）
    pub cache_size: i32,
    /// 连接池大小
    pub pool_size: usize,
    /// 是否启用外键约束
    pub foreign_keys: bool,
    /// 同步模式
    pub synchronous: SynchronousMode,
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            database_path: PathBuf::from("data/app.db"),
            enable_wal: true,
            page_size: 4096, // SQLCipher优化的页面大小
            cache_size: -2000, // 2MB缓存
            pool_size: 10,
            foreign_keys: true,
            synchronous: SynchronousMode::Normal,
        }
    }
}

/// SQLite同步模式
#[derive(Debug, Clone)]
pub enum SynchronousMode {
    Off,
    Normal,
    Full,
    Extra,
}

impl SynchronousMode {
    fn as_str(&self) -> &'static str {
        match self {
            SynchronousMode::Off => "OFF",
            SynchronousMode::Normal => "NORMAL",
            SynchronousMode::Full => "FULL",
            SynchronousMode::Extra => "EXTRA",
        }
    }
}

/// 加密数据库连接
pub struct EncryptedConnection {
    connection: Connection,
    key: EncryptionKey,
    config: DatabaseConfig,
}

impl EncryptedConnection {
    /// 创建新的加密连接
    pub fn new(
        database_path: impl AsRef<Path>,
        key: EncryptionKey,
        config: DatabaseConfig,
    ) -> Result<Self> {
        let path = database_path.as_ref();
        
        // 确保数据库目录存在
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("Failed to create database directory: {:?}", parent))?;
        }
        
        // 创建连接（启用SQLCipher支持）
        let flags = OpenFlags::SQLITE_OPEN_READ_WRITE 
            | OpenFlags::SQLITE_OPEN_CREATE 
            | OpenFlags::SQLITE_OPEN_NO_MUTEX;
            
        let mut connection = Connection::open_with_flags(path, flags)
            .with_context(|| format!("Failed to open database: {:?}", path))?;
        
        // 配置SQLCipher加密
        Self::configure_encryption(&mut connection, &key, &config)?;
        
        // 配置数据库性能优化
        Self::configure_database(&mut connection, &config)?;
        
        info!("Successfully opened encrypted database at: {:?}", path);
        
        Ok(Self {
            connection,
            key,
            config,
        })
    }
    
    /// 配置SQLCipher加密
    fn configure_encryption(
        connection: &mut Connection,
        key: &EncryptionKey,
        config: &DatabaseConfig,
    ) -> Result<()> {
        // 设置加密密钥
        let key_hex = key.to_hex();
        connection.execute(&format!("PRAGMA key = 'x{}'", key_hex), [])?;
        
        // 设置加密页面大小
        connection.execute(&format!("PRAGMA cipher_page_size = {}", config.page_size), [])?;
        
        // 设置KDF迭代次数（增强安全性）
        connection.execute("PRAGMA kdf_iter = 250000", [])?;
        
        // 设置加密算法（使用AES-256）
        connection.execute("PRAGMA cipher = 'aes-256-cbc'", [])?;
        
        // 验证数据库可以正常访问（触发解密）
        match connection.execute("SELECT count(*) FROM sqlite_master", []) {
            Ok(_) => {
                debug!("Database encryption verification successful");
            }
            Err(e) => {
                error!("Database encryption verification failed: {}", e);
                return Err(anyhow!("Invalid encryption key or corrupted database"));
            }
        }
        
        Ok(())
    }
    
    /// 配置数据库性能优化
    fn configure_database(
        connection: &mut Connection,
        config: &DatabaseConfig,
    ) -> Result<()> {
        // 启用WAL模式（提高并发性能）
        if config.enable_wal {
            connection.execute("PRAGMA journal_mode = WAL", [])?;
            debug!("Enabled WAL journal mode");
        }
        
        // 设置同步模式
        connection.execute(
            &format!("PRAGMA synchronous = {}", config.synchronous.as_str()),
            []
        )?;
        
        // 设置缓存大小
        connection.execute(&format!("PRAGMA cache_size = {}", config.cache_size), [])?;
        
        // 启用外键约束
        if config.foreign_keys {
            connection.execute("PRAGMA foreign_keys = ON", [])?;
        }
        
        // 设置临时存储为内存
        connection.execute("PRAGMA temp_store = MEMORY", [])?;
        
        // 设置锁定超时
        connection.execute("PRAGMA busy_timeout = 30000", [])?; // 30秒
        
        // 优化查询性能
        connection.execute("PRAGMA optimize", [])?;
        
        info!("Database performance optimization configured");
        Ok(())
    }
    
    /// 获取连接引用
    pub fn connection(&self) -> &Connection {
        &self.connection
    }
    
    /// 获取可变连接引用
    pub fn connection_mut(&mut self) -> &mut Connection {
        &mut self.connection
    }
    
    /// 执行事务
    pub fn transaction<T, F>(&mut self, f: F) -> Result<T>
    where
        F: FnOnce(&Connection) -> Result<T>,
    {
        let transaction = self.connection.transaction()?;
        
        let result = f(&transaction).map_err(|e| {
            warn!("Transaction failed, rolling back: {}", e);
            e
        });
        
        match result {
            Ok(value) => {
                transaction.commit()?;
                debug!("Transaction committed successfully");
                Ok(value)
            }
            Err(e) => {
                if let Err(rollback_err) = transaction.rollback() {
                    error!("Failed to rollback transaction: {}", rollback_err);
                }
                Err(e)
            }
        }
    }
    
    /// 批量事务处理
    pub fn batch_transaction<T, F>(&mut self, operations: Vec<F>) -> Result<Vec<T>>
    where
        F: FnOnce(&Connection) -> Result<T>,
    {
        let transaction = self.connection.transaction()?;
        let mut results = Vec::with_capacity(operations.len());
        
        for operation in operations {
            match operation(&transaction) {
                Ok(result) => results.push(result),
                Err(e) => {
                    warn!("Batch operation failed, rolling back all: {}", e);
                    transaction.rollback()?;
                    return Err(e);
                }
            }
        }
        
        transaction.commit()?;
        debug!("Batch transaction with {} operations committed", results.len());
        Ok(results)
    }
    
    /// 数据库完整性检查
    pub fn integrity_check(&self) -> Result<bool> {
        let mut stmt = self.connection.prepare("PRAGMA integrity_check")?;
        let mut rows = stmt.query([])?;
        
        if let Some(row) = rows.next()? {
            let result: String = row.get(0)?;
            if result == "ok" {
                info!("Database integrity check passed");
                Ok(true)
            } else {
                error!("Database integrity check failed: {}", result);
                Ok(false)
            }
        } else {
            error!("Database integrity check returned no results");
            Ok(false)
        }
    }
    
    /// 优化数据库
    pub fn optimize(&self) -> Result<()> {
        self.connection.execute("PRAGMA optimize", [])?;
        if self.config.enable_wal {
            self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)", [])?;
        }
        info!("Database optimization completed");
        Ok(())
    }
    
    /// 获取数据库统计信息
    pub fn get_stats(&self) -> Result<DatabaseStats> {
        let mut stats = DatabaseStats::default();
        
        // 数据库大小
        let mut stmt = self.connection.prepare("PRAGMA page_count")?;
        let page_count: i64 = stmt.query_row([], |row| row.get(0))?;
        stats.page_count = page_count;
        stats.database_size = page_count * self.config.page_size as i64;
        
        // WAL大小
        if self.config.enable_wal {
            if let Ok(mut stmt) = self.connection.prepare("PRAGMA wal_autocheckpoint") {
                if let Ok(wal_size) = stmt.query_row([], |row| row.get::<_, i64>(0)) {
                    stats.wal_size = Some(wal_size);
                }
            }
        }
        
        // 缓存命中率
        if let Ok(mut stmt) = self.connection.prepare("PRAGMA cache_hit_ratio") {
            if let Ok(hit_ratio) = stmt.query_row([], |row| row.get::<_, f64>(0)) {
                stats.cache_hit_ratio = Some(hit_ratio);
            }
        }
        
        Ok(stats)
    }
}

/// 数据库统计信息
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct DatabaseStats {
    pub page_count: i64,
    pub database_size: i64,
    pub wal_size: Option<i64>,
    pub cache_hit_ratio: Option<f64>,
}

/// 加密数据库管理器
pub struct EncryptedDatabaseManager {
    config: DatabaseConfig,
    security_config: SecurityConfig,
    connections: Arc<RwLock<HashMap<String, Arc<Mutex<EncryptedConnection>>>>>,
}

impl EncryptedDatabaseManager {
    /// 创建新的数据库管理器
    pub fn new(config: DatabaseConfig, security_config: SecurityConfig) -> Self {
        Self {
            config,
            security_config,
            connections: Arc::new(RwLock::new(HashMap::new())),
        }
    }
    
    /// 获取或创建数据库连接
    pub async fn get_connection(&self, database_name: &str, user_passphrase: Option<&str>) -> Result<Arc<Mutex<EncryptedConnection>>> {
        let connections = self.connections.read().await;
        
        if let Some(connection) = connections.get(database_name) {
            debug!("Reusing existing connection for database: {}", database_name);
            return Ok(connection.clone());
        }
        
        drop(connections);
        
        // 创建新连接
        info!("Creating new encrypted connection for database: {}", database_name);
        let key = self.security_config.derive_database_key(user_passphrase)?;
        
        // 验证密钥（如果有验证哈希）
        if !self.security_config.verify_key(&key) {
            return Err(anyhow!("Invalid encryption key"));
        }
        
        let db_path = self.config.database_path.with_file_name(
            format!("{}.db", database_name)
        );
        
        let connection = EncryptedConnection::new(db_path, key, self.config.clone())?;
        let connection = Arc::new(Mutex::new(connection));
        
        let mut connections = self.connections.write().await;
        connections.insert(database_name.to_string(), connection.clone());
        
        Ok(connection)
    }
    
    /// 关闭指定数据库连接
    pub async fn close_connection(&self, database_name: &str) -> Result<()> {
        let mut connections = self.connections.write().await;
        
        if let Some(connection) = connections.remove(database_name) {
            // 优化数据库后关闭
            if let Ok(conn) = connection.lock() {
                if let Err(e) = conn.optimize() {
                    warn!("Failed to optimize database before closing: {}", e);
                }
            }
            info!("Closed database connection: {}", database_name);
        }
        
        Ok(())
    }
    
    /// 关闭所有连接
    pub async fn close_all_connections(&self) -> Result<()> {
        let mut connections = self.connections.write().await;
        
        for (name, connection) in connections.drain() {
            if let Ok(conn) = connection.lock() {
                if let Err(e) = conn.optimize() {
                    warn!("Failed to optimize database {} before closing: {}", name, e);
                }
            }
        }
        
        info!("Closed all database connections");
        Ok(())
    }
    
    /// 初始化数据库表结构
    pub async fn initialize_schema(&self, database_name: &str, schema_sql: &str) -> Result<()> {
        let connection = self.get_connection(database_name, None).await?;
        let mut conn = connection.lock().map_err(|_| anyhow!("Failed to acquire connection lock"))?;
        
        conn.transaction(|tx| {
            tx.execute_batch(schema_sql)?;
            info!("Database schema initialized for: {}", database_name);
            Ok(())
        })?;
        
        Ok(())
    }
    
    /// 备份数据库
    pub async fn backup_database(&self, database_name: &str, backup_path: impl AsRef<Path>) -> Result<()> {
        let connection = self.get_connection(database_name, None).await?;
        let conn = connection.lock().map_err(|_| anyhow!("Failed to acquire connection lock"))?;
        
        let backup_path = backup_path.as_ref();
        if let Some(parent) = backup_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        // SQLite备份API
        let backup_conn = Connection::open(backup_path)?;
        let backup = rusqlite::backup::Backup::new(conn.connection(), &backup_conn)?;
        backup.run_to_completion(5, std::time::Duration::from_millis(250), None)?;
        
        info!("Database backup completed: {} -> {:?}", database_name, backup_path);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    
    fn create_test_config(temp_dir: &TempDir) -> (DatabaseConfig, SecurityConfig) {
        let mut db_config = DatabaseConfig::default();
        db_config.database_path = temp_dir.path().join("test.db");
        
        let security_config = SecurityConfig::initialize().unwrap();
        
        (db_config, security_config)
    }
    
    #[test]
    fn test_encrypted_connection_creation() {
        let temp_dir = TempDir::new().unwrap();
        let (db_config, security_config) = create_test_config(&temp_dir);
        
        let key = security_config.derive_database_key(None).unwrap();
        let connection = EncryptedConnection::new(
            &db_config.database_path,
            key,
            db_config,
        ).unwrap();
        
        // 验证连接可用
        assert!(connection.integrity_check().unwrap());
    }
    
    #[test]
    fn test_transaction_rollback() {
        let temp_dir = TempDir::new().unwrap();
        let (db_config, security_config) = create_test_config(&temp_dir);
        
        let key = security_config.derive_database_key(None).unwrap();
        let mut connection = EncryptedConnection::new(
            &db_config.database_path,
            key,
            db_config,
        ).unwrap();
        
        // 创建测试表
        connection.connection().execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)",
            []
        ).unwrap();
        
        // 测试失败的事务应该回滚
        let result = connection.transaction(|tx| {
            tx.execute("INSERT INTO test (value) VALUES (?)", params!["test1"])?;
            tx.execute("INSERT INTO test (value) VALUES (?)", params!["test2"])?;
            // 故意触发错误
            Err(anyhow!("Test error"))
        });
        
        assert!(result.is_err());
        
        // 验证数据没有被插入
        let mut stmt = connection.connection().prepare("SELECT COUNT(*) FROM test").unwrap();
        let count: i64 = stmt.query_row([], |row| row.get(0)).unwrap();
        assert_eq!(count, 0);
    }
    
    #[tokio::test]
    async fn test_database_manager() {
        let temp_dir = TempDir::new().unwrap();
        let (db_config, security_config) = create_test_config(&temp_dir);
        
        let manager = EncryptedDatabaseManager::new(db_config, security_config);
        
        // 获取连接
        let connection1 = manager.get_connection("test", None).await.unwrap();
        let connection2 = manager.get_connection("test", None).await.unwrap();
        
        // 应该返回同一个连接实例
        assert!(Arc::ptr_eq(&connection1, &connection2));
        
        // 关闭连接
        manager.close_connection("test").await.unwrap();
        
        // 再次获取应该是新的连接
        let connection3 = manager.get_connection("test", None).await.unwrap();
        assert!(!Arc::ptr_eq(&connection1, &connection3));
    }
}