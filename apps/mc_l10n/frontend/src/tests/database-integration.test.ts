// database-integration.test.ts - 前端数据库集成测试
import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import { encryptedDb, type DatabaseStats, type SecurityConfig } from '../services/database/EncryptedDatabaseService';

describe('SQLCipher 加密数据库集成测试', () => {
  const testDbName = 'test_integration_db';
  
  beforeAll(async () => {
    // 初始化测试数据库
    try {
      await encryptedDb.initialize(testDbName);
      console.log('Test database initialized successfully');
    } catch (error) {
      console.error('Failed to initialize test database:', error);
      throw error;
    }
  });

  afterAll(async () => {
    // 清理测试数据
    try {
      await encryptedDb.execute(
        'DROP TABLE IF EXISTS test_users',
        [],
        testDbName
      );
      await encryptedDb.execute(
        'DROP TABLE IF EXISTS test_projects',
        [],
        testDbName
      );
      console.log('Test cleanup completed');
    } catch (error) {
      console.warn('Test cleanup failed:', error);
    }
  });

  beforeEach(async () => {
    // 每个测试前清理表
    try {
      await encryptedDb.execute('DELETE FROM test_users', [], testDbName);
      await encryptedDb.execute('DELETE FROM test_projects', [], testDbName);
    } catch {
      // 表可能不存在，忽略错误
    }
  });

  describe('数据库初始化和配置', () => {
    it('应该能够获取设备指纹', async () => {
      const fingerprint = await encryptedDb.getDeviceFingerprint();
      
      expect(fingerprint).toBeDefined();
      expect(typeof fingerprint).toBe('string');
      expect(fingerprint.length).toBe(64); // SHA256 hex string
      
      console.log(`Device fingerprint: ${fingerprint.substring(0, 16)}...`);
    });

    it('应该能够初始化安全配置', async () => {
      const securityConfig: SecurityConfig = await encryptedDb.initializeSecurityConfig();
      
      expect(securityConfig.device_fingerprint_hash).toBeDefined();
      expect(typeof securityConfig.user_passphrase_enabled).toBe('boolean');
      expect(typeof securityConfig.has_verification_hash).toBe('boolean');
      
      console.log('Security config:', {
        fingerprint_hash: securityConfig.device_fingerprint_hash,
        passphrase_enabled: securityConfig.user_passphrase_enabled,
        has_verification: securityConfig.has_verification_hash
      });
    });

    it('应该能够获取数据库统计信息', async () => {
      const stats: DatabaseStats = await encryptedDb.getStats(testDbName);
      
      expect(stats.page_count).toBeGreaterThan(0);
      expect(stats.database_size).toBeGreaterThan(0);
      
      console.log('Database stats:', stats);
    });

    it('应该能够检查数据库完整性', async () => {
      const isValid = await encryptedDb.checkIntegrity(testDbName);
      expect(isValid).toBe(true);
    });
  });

  describe('基本CRUD操作', () => {
    beforeEach(async () => {
      // 创建测试表
      await encryptedDb.execute(`
        CREATE TABLE IF NOT EXISTS test_users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT UNIQUE NOT NULL,
          email TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `, [], testDbName);
    });

    it('应该能够插入和查询数据', async () => {
      // 插入数据
      const affectedRows = await encryptedDb.insert('test_users', {
        username: 'testuser',
        email: 'test@example.com'
      }, testDbName);
      
      expect(affectedRows).toBe(1);
      
      // 查询数据
      const user = await encryptedDb.findOne('test_users', {
        username: 'testuser'
      }, undefined, testDbName);
      
      expect(user).toBeDefined();
      expect(user!.username).toBe('testuser');
      expect(user!.email).toBe('test@example.com');
    });

    it('应该能够更新数据', async () => {
      // 先插入数据
      await encryptedDb.insert('test_users', {
        username: 'updateuser',
        email: 'old@example.com'
      }, testDbName);
      
      // 更新数据
      const affectedRows = await encryptedDb.update(
        'test_users',
        { email: 'new@example.com' },
        { username: 'updateuser' },
        testDbName
      );
      
      expect(affectedRows).toBe(1);
      
      // 验证更新
      const user = await encryptedDb.findOne('test_users', {
        username: 'updateuser'
      }, undefined, testDbName);
      
      expect(user!.email).toBe('new@example.com');
    });

    it('应该能够删除数据', async () => {
      // 先插入数据
      await encryptedDb.insert('test_users', {
        username: 'deleteuser',
        email: 'delete@example.com'
      }, testDbName);
      
      // 删除数据
      const affectedRows = await encryptedDb.delete('test_users', {
        username: 'deleteuser'
      }, testDbName);
      
      expect(affectedRows).toBe(1);
      
      // 验证删除
      const user = await encryptedDb.findOne('test_users', {
        username: 'deleteuser'
      }, undefined, testDbName);
      
      expect(user).toBeNull();
    });

    it('应该能够统计记录数量', async () => {
      // 插入多条数据
      await encryptedDb.insert('test_users', {
        username: 'user1',
        email: 'user1@example.com'
      }, testDbName);
      
      await encryptedDb.insert('test_users', {
        username: 'user2',
        email: 'user2@example.com'
      }, testDbName);
      
      // 统计数量
      const count = await encryptedDb.count('test_users', {}, testDbName);
      expect(count).toBe(2);
      
      // 带条件统计
      const userCount = await encryptedDb.count('test_users', {
        username: 'user1'
      }, testDbName);
      expect(userCount).toBe(1);
    });
  });

  describe('事务操作', () => {
    beforeEach(async () => {
      await encryptedDb.execute(`
        CREATE TABLE IF NOT EXISTS test_projects (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `, [], testDbName);
    });

    it('应该支持成功的事务操作', async () => {
      const result = await encryptedDb.transaction(async (db) => {
        await db.insert('test_projects', {
          name: 'Project 1',
          status: 'active'
        }, testDbName);
        
        await db.insert('test_projects', {
          name: 'Project 2',
          status: 'pending'
        }, testDbName);
        
        return 'transaction_success';
      }, testDbName);
      
      expect(result).toBe('transaction_success');
      
      // 验证数据已插入
      const count = await encryptedDb.count('test_projects', {}, testDbName);
      expect(count).toBe(2);
    });

    it('应该支持失败事务的回滚', async () => {
      // 先插入一条数据
      await encryptedDb.insert('test_projects', {
        name: 'Existing Project',
        status: 'active'
      }, testDbName);
      
      // 尝试执行会失败的事务
      try {
        await encryptedDb.transaction(async (db) => {
          await db.insert('test_projects', {
            name: 'Project A',
            status: 'active'
          }, testDbName);
          
          // 故意抛出错误
          throw new Error('Transaction test error');
        }, testDbName);
        
        // 不应该到达这里
        expect(true).toBe(false);
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
      }
      
      // 验证只有原来的数据存在（事务已回滚）
      const count = await encryptedDb.count('test_projects', {}, testDbName);
      expect(count).toBe(1);
      
      const projects = await encryptedDb.findMany('test_projects', {}, undefined, undefined, undefined, testDbName);
      expect(projects[0].name).toBe('Existing Project');
    });
  });

  describe('缓存操作', () => {
    it('应该能够设置和获取缓存', async () => {
      const testData = { key: 'value', number: 42, array: [1, 2, 3] };
      
      // 设置缓存
      await encryptedDb.setCache('test_key', testData, undefined, testDbName);
      
      // 获取缓存
      const cachedData = await encryptedDb.getCache<typeof testData>('test_key', testDbName);
      
      expect(cachedData).toEqual(testData);
    });

    it('应该支持缓存过期', async () => {
      const testData = 'expires_soon';
      
      // 设置1秒过期的缓存
      await encryptedDb.setCache('expire_key', testData, 1, testDbName);
      
      // 立即获取应该成功
      let cachedData = await encryptedDb.getCache('expire_key', testDbName);
      expect(cachedData).toBe(testData);
      
      // 等待2秒后获取应该失败
      await new Promise(resolve => setTimeout(resolve, 2000));
      cachedData = await encryptedDb.getCache('expire_key', testDbName);
      expect(cachedData).toBeNull();
    });

    it('应该能够删除缓存', async () => {
      // 设置缓存
      await encryptedDb.setCache('delete_key', 'to_be_deleted', undefined, testDbName);
      
      // 验证缓存存在
      let cachedData = await encryptedDb.getCache('delete_key', testDbName);
      expect(cachedData).toBe('to_be_deleted');
      
      // 删除缓存
      await encryptedDb.deleteCache('delete_key', testDbName);
      
      // 验证缓存已删除
      cachedData = await encryptedDb.getCache('delete_key', testDbName);
      expect(cachedData).toBeNull();
    });

    it('应该能够清理过期缓存', async () => {
      // 设置多个缓存，部分过期
      await encryptedDb.setCache('permanent', 'never_expires', undefined, testDbName);
      await encryptedDb.setCache('short_lived', 'expires_fast', 1, testDbName);
      
      // 等待过期
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // 清理过期缓存
      const deletedCount = await encryptedDb.cleanExpiredCache(testDbName);
      expect(deletedCount).toBeGreaterThanOrEqual(1);
      
      // 验证永久缓存仍然存在
      const permanentData = await encryptedDb.getCache('permanent', testDbName);
      expect(permanentData).toBe('never_expires');
      
      // 验证过期缓存已被清理
      const expiredData = await encryptedDb.getCache('short_lived', testDbName);
      expect(expiredData).toBeNull();
    });
  });

  describe('性能和优化', () => {
    it('应该能够处理批量操作', async () => {
      await encryptedDb.execute(`
        CREATE TABLE IF NOT EXISTS perf_test (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          data TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `, [], testDbName);
      
      const startTime = Date.now();
      const batchSize = 100;
      
      // 使用事务批量插入
      await encryptedDb.transaction(async (db) => {
        for (let i = 0; i < batchSize; i++) {
          await db.insert('perf_test', {
            data: `test_data_${i}`
          }, testDbName);
        }
      }, testDbName);
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      console.log(`Batch insert of ${batchSize} records took ${duration}ms`);
      
      // 验证数据
      const count = await encryptedDb.count('perf_test', {}, testDbName);
      expect(count).toBe(batchSize);
      
      // 性能要求：100条记录插入应在5秒内完成
      expect(duration).toBeLessThan(5000);
    });

    it('应该能够优化数据库', async () => {
      const result = await encryptedDb.optimize(testDbName);
      expect(result).toContain('optimization completed');
    });

    it('应该能够备份数据库', async () => {
      // 插入一些测试数据
      await encryptedDb.execute(`
        CREATE TABLE IF NOT EXISTS backup_test (
          id INTEGER PRIMARY KEY,
          value TEXT
        )
      `, [], testDbName);
      
      await encryptedDb.insert('backup_test', {
        id: 1,
        value: 'backup_test_data'
      }, testDbName);
      
      // 执行备份
      const backupPath = './test_backup.db';
      const result = await encryptedDb.backup(backupPath, testDbName);
      
      expect(result).toContain('backed up');
      expect(result).toContain(backupPath);
    });
  });

  describe('表结构操作', () => {
    it('应该能够检查表是否存在', async () => {
      // 检查不存在的表
      const notExists = await encryptedDb.tableExists('non_existent_table', testDbName);
      expect(notExists).toBe(false);
      
      // 创建表
      await encryptedDb.execute(`
        CREATE TABLE table_exists_test (
          id INTEGER PRIMARY KEY,
          name TEXT
        )
      `, [], testDbName);
      
      // 检查存在的表
      const exists = await encryptedDb.tableExists('table_exists_test', testDbName);
      expect(exists).toBe(true);
    });

    it('应该能够获取表信息', async () => {
      await encryptedDb.execute(`
        CREATE TABLE table_info_test (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT UNIQUE,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `, [], testDbName);
      
      const tableInfo = await encryptedDb.getTableInfo('table_info_test', testDbName);
      
      expect(tableInfo.length).toBeGreaterThan(0);
      expect(tableInfo.some(col => col.name === 'id')).toBe(true);
      expect(tableInfo.some(col => col.name === 'name')).toBe(true);
      expect(tableInfo.some(col => col.name === 'email')).toBe(true);
      
      console.log('Table info:', tableInfo);
    });
  });
});