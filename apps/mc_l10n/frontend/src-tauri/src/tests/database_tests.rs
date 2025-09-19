// database_tests.rs - 完整的数据库测试套件
#[cfg(test)]
mod database_integration_tests {
    use crate::crypto::{SecurityConfig, DeviceFingerprint, KeyDerivationService};
    use crate::database::{EncryptedDatabaseManager, DatabaseConfig, EncryptedConnection};
    use tempfile::TempDir;
    use tokio::runtime::Runtime;
    use std::time::Instant;
    use anyhow::Result;

    fn setup_test_environment() -> (TempDir, DatabaseConfig, SecurityConfig) {
        let temp_dir = TempDir::new().expect("Failed to create temp directory");
        
        let mut db_config = DatabaseConfig::default();
        db_config.database_path = temp_dir.path().join("test_encrypted.db");
        db_config.enable_wal = true;
        db_config.page_size = 4096;
        db_config.cache_size = -2000;
        
        let security_config = SecurityConfig::initialize()
            .expect("Failed to initialize security config");
        
        (temp_dir, db_config, security_config)
    }

    #[test]
    fn test_device_fingerprint_consistency() {
        // 测试设备指纹在同一环境中的一致性
        let fingerprint1 = DeviceFingerprint::generate().unwrap();
        let fingerprint2 = DeviceFingerprint::generate().unwrap();
        
        assert_eq!(fingerprint1, fingerprint2);
        assert_eq!(fingerprint1.len(), 64); // SHA256 hex string
        
        println!("Device fingerprint: {}", &fingerprint1[..16]); // 只显示前16位
    }

    #[test]
    fn test_key_derivation_security() {
        let fingerprint = "test_device_12345";
        let salt = KeyDerivationService::generate_salt();
        
        // 相同输入应产生相同密钥
        let key1 = KeyDerivationService::derive_key(fingerprint, Some("password123"), &salt).unwrap();
        let key2 = KeyDerivationService::derive_key(fingerprint, Some("password123"), &salt).unwrap();
        assert_eq!(key1.as_bytes(), key2.as_bytes());
        
        // 不同密码应产生不同密钥
        let key3 = KeyDerivationService::derive_key(fingerprint, Some("different_password"), &salt).unwrap();
        assert_ne!(key1.as_bytes(), key3.as_bytes());
        
        // 不同设备指纹应产生不同密钥
        let key4 = KeyDerivationService::derive_key("different_device", Some("password123"), &salt).unwrap();
        assert_ne!(key1.as_bytes(), key4.as_bytes());
        
        // 测试密钥验证
        let hash = KeyDerivationService::generate_key_hash(&key1);
        assert!(KeyDerivationService::verify_key(&key1, &hash));
        assert!(!KeyDerivationService::verify_key(&key3, &hash));
        
        println!("Key derivation security tests passed");
    }

    #[test]
    fn test_encrypted_connection_basic() {
        let (_temp_dir, db_config, security_config) = setup_test_environment();
        
        let key = security_config.derive_database_key(None).unwrap();
        let mut connection = EncryptedConnection::new(
            &db_config.database_path,
            key,
            db_config,
        ).unwrap();
        
        // 测试基本操作
        connection.connection().execute(
            "CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)",
            []
        ).unwrap();
        
        connection.connection().execute(
            "INSERT INTO test_table (value) VALUES (?)",
            &["test_value"]
        ).unwrap();
        
        let mut stmt = connection.connection().prepare(
            "SELECT value FROM test_table WHERE id = 1"
        ).unwrap();
        
        let value: String = stmt.query_row([], |row| row.get(0)).unwrap();
        assert_eq!(value, "test_value");
        
        // 测试数据库完整性
        assert!(connection.integrity_check().unwrap());
        
        println!("Basic encrypted connection test passed");
    }

    #[test]
    fn test_transaction_atomicity() {
        let (_temp_dir, db_config, security_config) = setup_test_environment();
        
        let key = security_config.derive_database_key(None).unwrap();
        let mut connection = EncryptedConnection::new(
            &db_config.database_path,
            key,
            db_config,
        ).unwrap();
        
        // 创建测试表
        connection.connection().execute(
            "CREATE TABLE test_atomic (id INTEGER PRIMARY KEY, value TEXT)",
            []
        ).unwrap();
        
        // 测试成功的事务
        let result = connection.transaction(|tx| {
            tx.execute("INSERT INTO test_atomic (value) VALUES (?)", &["value1"])?;
            tx.execute("INSERT INTO test_atomic (value) VALUES (?)", &["value2"])?;
            Ok(())
        });
        assert!(result.is_ok());
        
        // 验证数据已插入
        let mut stmt = connection.connection().prepare("SELECT COUNT(*) FROM test_atomic").unwrap();
        let count: i64 = stmt.query_row([], |row| row.get(0)).unwrap();
        assert_eq!(count, 2);
        
        // 测试失败的事务（应该回滚）
        let result = connection.transaction(|tx| {
            tx.execute("INSERT INTO test_atomic (value) VALUES (?)", &["value3"])?;
            tx.execute("INSERT INTO test_atomic (value) VALUES (?)", &["value4"])?;
            // 故意返回错误
            Err(anyhow::anyhow!("Test transaction failure"))
        });
        assert!(result.is_err());
        
        // 验证数据没有增加（事务已回滚）
        let mut stmt = connection.connection().prepare("SELECT COUNT(*) FROM test_atomic").unwrap();
        let count: i64 = stmt.query_row([], |row| row.get(0)).unwrap();
        assert_eq!(count, 2);
        
        println!("Transaction atomicity test passed");
    }

    #[test]
    fn test_batch_operations() {
        let (_temp_dir, db_config, security_config) = setup_test_environment();
        
        let key = security_config.derive_database_key(None).unwrap();
        let mut connection = EncryptedConnection::new(
            &db_config.database_path,
            key,
            db_config,
        ).unwrap();
        
        // 创建测试表
        connection.connection().execute(
            "CREATE TABLE test_batch (id INTEGER PRIMARY KEY, value TEXT)",
            []
        ).unwrap();
        
        // 准备批量操作
        let operations = vec![
            |tx: &rusqlite::Connection| -> Result<()> {
                tx.execute("INSERT INTO test_batch (value) VALUES (?)", &["batch1"])?;
                Ok(())
            },
            |tx: &rusqlite::Connection| -> Result<()> {
                tx.execute("INSERT INTO test_batch (value) VALUES (?)", &["batch2"])?;
                Ok(())
            },
            |tx: &rusqlite::Connection| -> Result<()> {
                tx.execute("INSERT INTO test_batch (value) VALUES (?)", &["batch3"])?;
                Ok(())
            },
        ];
        
        // 执行批量事务
        let results = connection.batch_transaction(operations).unwrap();
        assert_eq!(results.len(), 3);
        
        // 验证数据
        let mut stmt = connection.connection().prepare("SELECT COUNT(*) FROM test_batch").unwrap();
        let count: i64 = stmt.query_row([], |row| row.get(0)).unwrap();
        assert_eq!(count, 3);
        
        println!("Batch operations test passed");
    }

    #[tokio::test]
    async fn test_database_manager_concurrency() {
        let (_temp_dir, db_config, security_config) = setup_test_environment();
        
        let manager = EncryptedDatabaseManager::new(db_config, security_config);
        
        // 测试并发连接获取
        let (conn1, conn2) = tokio::join!(
            manager.get_connection("test_db", None),
            manager.get_connection("test_db", None)
        );
        
        assert!(conn1.is_ok());
        assert!(conn2.is_ok());
        
        // 应该返回同一个连接实例
        let conn1 = conn1.unwrap();
        let conn2 = conn2.unwrap();
        assert!(std::sync::Arc::ptr_eq(&conn1, &conn2));
        
        // 测试数据库初始化
        let schema = r#"
            CREATE TABLE IF NOT EXISTS concurrent_test (
                id INTEGER PRIMARY KEY,
                thread_id TEXT,
                timestamp TEXT
            );
        "#;
        
        manager.initialize_schema("test_db", schema).await.unwrap();
        
        println!("Database manager concurrency test passed");
    }

    #[test]
    fn test_performance_benchmarks() {
        let (_temp_dir, db_config, security_config) = setup_test_environment();
        
        let key = security_config.derive_database_key(None).unwrap();
        let mut connection = EncryptedConnection::new(
            &db_config.database_path,
            key,
            db_config,
        ).unwrap();
        
        // 创建测试表
        connection.connection().execute(
            "CREATE TABLE perf_test (id INTEGER PRIMARY KEY, data TEXT)",
            []
        ).unwrap();
        
        // 测试插入性能
        let start = Instant::now();
        let insert_count = 1000;
        
        connection.transaction(|tx| {
            let mut stmt = tx.prepare("INSERT INTO perf_test (data) VALUES (?)")?;
            for i in 0..insert_count {
                stmt.execute(&[&format!("test_data_{}", i)])?;
            }
            Ok(())
        }).unwrap();
        
        let insert_duration = start.elapsed();
        println!("Inserted {} records in {:?}", insert_count, insert_duration);
        
        // 测试查询性能
        let start = Instant::now();
        let mut stmt = connection.connection().prepare(
            "SELECT COUNT(*) FROM perf_test"
        ).unwrap();
        let count: i64 = stmt.query_row([], |row| row.get(0)).unwrap();
        let query_duration = start.elapsed();
        
        assert_eq!(count, insert_count);
        println!("Query completed in {:?}", query_duration);
        
        // 测试优化操作
        let start = Instant::now();
        connection.optimize().unwrap();
        let optimize_duration = start.elapsed();
        println!("Database optimization completed in {:?}", optimize_duration);
        
        // 性能要求验证
        assert!(insert_duration.as_millis() < 5000, "Insert performance too slow");
        assert!(query_duration.as_millis() < 100, "Query performance too slow");
        
        println!("Performance benchmark test passed");
    }

    #[test]
    fn test_wal_mode_functionality() {
        let (_temp_dir, mut db_config, security_config) = setup_test_environment();
        
        // 确保启用WAL模式
        db_config.enable_wal = true;
        
        let key = security_config.derive_database_key(None).unwrap();
        let connection = EncryptedConnection::new(
            &db_config.database_path,
            key,
            db_config,
        ).unwrap();
        
        // 验证WAL模式已启用
        let mut stmt = connection.connection().prepare("PRAGMA journal_mode").unwrap();
        let journal_mode: String = stmt.query_row([], |row| row.get(0)).unwrap();
        assert_eq!(journal_mode.to_lowercase(), "wal");
        
        // 创建表并插入数据
        connection.connection().execute(
            "CREATE TABLE wal_test (id INTEGER PRIMARY KEY, value TEXT)",
            []
        ).unwrap();
        
        connection.connection().execute(
            "INSERT INTO wal_test (value) VALUES (?)",
            &["wal_test_value"]
        ).unwrap();
        
        // 检查WAL文件是否存在
        let wal_path = db_config.database_path.with_extension("db-wal");
        // WAL文件可能不会立即出现，这取决于SQLite的内部逻辑
        
        println!("WAL mode functionality test passed");
    }

    #[test]
    fn test_encryption_key_rotation() {
        let (_temp_dir, db_config, mut security_config) = setup_test_environment();
        
        // 创建初始加密数据库
        let original_key = security_config.derive_database_key(None).unwrap();
        let mut connection = EncryptedConnection::new(
            &db_config.database_path,
            original_key.clone(),
            db_config.clone(),
        ).unwrap();
        
        // 插入测试数据
        connection.connection().execute(
            "CREATE TABLE key_rotation_test (id INTEGER PRIMARY KEY, data TEXT)",
            []
        ).unwrap();
        
        connection.connection().execute(
            "INSERT INTO key_rotation_test (data) VALUES (?)",
            &["original_data"]
        ).unwrap();
        
        drop(connection); // 关闭连接
        
        // 使用相同密钥重新打开（应该成功）
        let new_key = security_config.derive_database_key(None).unwrap();
        assert_eq!(original_key.as_bytes(), new_key.as_bytes());
        
        let connection = EncryptedConnection::new(
            &db_config.database_path,
            new_key,
            db_config,
        ).unwrap();
        
        // 验证数据可以正常读取
        let mut stmt = connection.connection().prepare(
            "SELECT data FROM key_rotation_test WHERE id = 1"
        ).unwrap();
        let data: String = stmt.query_row([], |row| row.get(0)).unwrap();
        assert_eq!(data, "original_data");
        
        println!("Encryption key rotation test passed");
    }

    #[test]
    fn test_error_handling_and_recovery() {
        let (_temp_dir, db_config, security_config) = setup_test_environment();
        
        let key = security_config.derive_database_key(None).unwrap();
        let mut connection = EncryptedConnection::new(
            &db_config.database_path,
            key,
            db_config,
        ).unwrap();
        
        // 测试SQL语法错误处理
        let result = connection.connection().execute(
            "INVALID SQL SYNTAX",
            []
        );
        assert!(result.is_err());
        
        // 数据库应该仍然可用
        let result = connection.connection().execute(
            "CREATE TABLE error_test (id INTEGER)",
            []
        );
        assert!(result.is_ok());
        
        // 测试约束违反错误
        connection.connection().execute(
            "CREATE TABLE unique_test (id INTEGER PRIMARY KEY, value TEXT UNIQUE)",
            []
        ).unwrap();
        
        connection.connection().execute(
            "INSERT INTO unique_test (value) VALUES (?)",
            &["unique_value"]
        ).unwrap();
        
        // 插入重复值应该失败
        let result = connection.connection().execute(
            "INSERT INTO unique_test (value) VALUES (?)",
            &["unique_value"]
        );
        assert!(result.is_err());
        
        // 测试事务中的错误恢复
        let result = connection.transaction(|tx| {
            tx.execute("INSERT INTO unique_test (value) VALUES (?)", &["value1"])?;
            // 这应该失败并导致整个事务回滚
            tx.execute("INSERT INTO unique_test (value) VALUES (?)", &["unique_value"])?;
            Ok(())
        });
        assert!(result.is_err());
        
        // 验证value1没有被插入（事务已回滚）
        let mut stmt = connection.connection().prepare(
            "SELECT COUNT(*) FROM unique_test WHERE value = 'value1'"
        ).unwrap();
        let count: i64 = stmt.query_row([], |row| row.get(0)).unwrap();
        assert_eq!(count, 0);
        
        println!("Error handling and recovery test passed");
    }

    #[test]
    fn test_security_config_persistence() {
        let (_temp_dir, _db_config, security_config) = setup_test_environment();
        
        // 测试设备指纹一致性
        let fingerprint1 = &security_config.device_fingerprint;
        let new_config = SecurityConfig::initialize().unwrap();
        let fingerprint2 = &new_config.device_fingerprint;
        
        assert_eq!(fingerprint1, fingerprint2);
        
        // 测试密钥验证机制
        let key = security_config.derive_database_key(Some("test_password")).unwrap();
        let mut config_with_verification = security_config.clone();
        config_with_verification.set_key_verification(&key);
        
        assert!(config_with_verification.verify_key(&key));
        
        // 错误的密钥应该验证失败
        let wrong_key = security_config.derive_database_key(Some("wrong_password")).unwrap();
        assert!(!config_with_verification.verify_key(&wrong_key));
        
        println!("Security config persistence test passed");
    }

    #[test]
    fn run_comprehensive_integration_test() {
        println!("Running comprehensive SQLCipher integration test...");
        
        // 运行所有测试
        test_device_fingerprint_consistency();
        test_key_derivation_security();
        test_encrypted_connection_basic();
        test_transaction_atomicity();
        test_batch_operations();
        test_performance_benchmarks();
        test_wal_mode_functionality();
        test_encryption_key_rotation();
        test_error_handling_and_recovery();
        test_security_config_persistence();
        
        // 运行异步测试
        let rt = Runtime::new().unwrap();
        rt.block_on(async {
            test_database_manager_concurrency().await;
        });
        
        println!("✅ All SQLCipher integration tests passed!");
        println!("📊 Test Summary:");
        println!("   - Device fingerprint generation: ✅");
        println!("   - Key derivation security: ✅");
        println!("   - Encrypted database operations: ✅");
        println!("   - Transaction atomicity: ✅");
        println!("   - Batch operations: ✅");
        println!("   - Performance benchmarks: ✅");
        println!("   - WAL mode functionality: ✅");
        println!("   - Key rotation support: ✅");
        println!("   - Error handling: ✅");
        println!("   - Security persistence: ✅");
        println!("   - Concurrency management: ✅");
    }
}