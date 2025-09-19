// EncryptedDatabaseService.ts - 前端加密数据库服务
import { invoke } from '@tauri-apps/api/core';

export interface DatabaseStats {
  page_count: number;
  database_size: number;
  wal_size?: number;
  cache_hit_ratio?: number;
}

export interface SecurityConfig {
  device_fingerprint_hash: string;
  user_passphrase_enabled: boolean;
  has_verification_hash: boolean;
}

export interface QueryResult {
  [key: string]: any;
}

export class EncryptedDatabaseService {
  private static instance: EncryptedDatabaseService;
  private initialized = false;
  private defaultDatabaseName = 'app_data';

  private constructor() {}

  public static getInstance(): EncryptedDatabaseService {
    if (!EncryptedDatabaseService.instance) {
      EncryptedDatabaseService.instance = new EncryptedDatabaseService();
    }
    return EncryptedDatabaseService.instance;
  }

  /**
   * 初始化安全数据库
   */
  public async initialize(
    databaseName?: string,
    userPassphrase?: string
  ): Promise<string> {
    const dbName = databaseName || this.defaultDatabaseName;
    
    try {
      const result = await invoke<string>('initialize_secure_database', {
        databaseName: dbName,
        userPassphrase: userPassphrase || null,
      });
      
      this.initialized = true;
      console.log(`Secure database initialized: ${result}`);
      return result;
    } catch (error) {
      console.error('Failed to initialize secure database:', error);
      throw new Error(`Database initialization failed: ${error}`);
    }
  }

  /**
   * 获取数据库统计信息
   */
  public async getStats(databaseName?: string): Promise<DatabaseStats> {
    const dbName = databaseName || this.defaultDatabaseName;
    
    try {
      return await invoke<DatabaseStats>('get_database_stats', {
        databaseName: dbName,
      });
    } catch (error) {
      console.error('Failed to get database stats:', error);
      throw new Error(`Failed to get database stats: ${error}`);
    }
  }

  /**
   * 执行查询
   */
  public async query(
    sql: string,
    params: any[] = [],
    databaseName?: string
  ): Promise<QueryResult[]> {
    const dbName = databaseName || this.defaultDatabaseName;
    
    try {
      return await invoke<QueryResult[]>('execute_secure_query', {
        databaseName: dbName,
        query: sql,
        params,
      });
    } catch (error) {
      console.error('Database query failed:', error);
      throw new Error(`Query failed: ${error}`);
    }
  }

  /**
   * 执行更新操作（INSERT, UPDATE, DELETE）
   */
  public async execute(
    sql: string,
    params: any[] = [],
    databaseName?: string
  ): Promise<number> {
    const dbName = databaseName || this.defaultDatabaseName;
    
    try {
      return await invoke<number>('execute_secure_update', {
        databaseName: dbName,
        query: sql,
        params,
      });
    } catch (error) {
      console.error('Database execution failed:', error);
      throw new Error(`Execution failed: ${error}`);
    }
  }

  /**
   * 备份数据库
   */
  public async backup(
    backupPath: string,
    databaseName?: string
  ): Promise<string> {
    const dbName = databaseName || this.defaultDatabaseName;
    
    try {
      return await invoke<string>('backup_secure_database', {
        databaseName: dbName,
        backupPath,
      });
    } catch (error) {
      console.error('Database backup failed:', error);
      throw new Error(`Backup failed: ${error}`);
    }
  }

  /**
   * 优化数据库
   */
  public async optimize(databaseName?: string): Promise<string> {
    const dbName = databaseName || this.defaultDatabaseName;
    
    try {
      return await invoke<string>('optimize_secure_database', {
        databaseName: dbName,
      });
    } catch (error) {
      console.error('Database optimization failed:', error);
      throw new Error(`Optimization failed: ${error}`);
    }
  }

  /**
   * 检查数据库完整性
   */
  public async checkIntegrity(databaseName?: string): Promise<boolean> {
    const dbName = databaseName || this.defaultDatabaseName;
    
    try {
      return await invoke<boolean>('check_database_integrity', {
        databaseName: dbName,
      });
    } catch (error) {
      console.error('Database integrity check failed:', error);
      throw new Error(`Integrity check failed: ${error}`);
    }
  }

  /**
   * 获取设备指纹
   */
  public async getDeviceFingerprint(): Promise<string> {
    try {
      return await invoke<string>('get_device_fingerprint');
    } catch (error) {
      console.error('Failed to get device fingerprint:', error);
      throw new Error(`Device fingerprint generation failed: ${error}`);
    }
  }

  /**
   * 初始化安全配置
   */
  public async initializeSecurityConfig(): Promise<SecurityConfig> {
    try {
      return await invoke<SecurityConfig>('initialize_security_config');
    } catch (error) {
      console.error('Failed to initialize security config:', error);
      throw new Error(`Security config initialization failed: ${error}`);
    }
  }

  // === 便捷方法 ===

  /**
   * 插入记录
   */
  public async insert(
    table: string,
    data: Record<string, any>,
    databaseName?: string
  ): Promise<number> {
    const columns = Object.keys(data);
    const placeholders = columns.map(() => '?').join(', ');
    const values = Object.values(data);
    
    const sql = `INSERT INTO ${table} (${columns.join(', ')}) VALUES (${placeholders})`;
    return this.execute(sql, values, databaseName);
  }

  /**
   * 更新记录
   */
  public async update(
    table: string,
    data: Record<string, any>,
    where: Record<string, any>,
    databaseName?: string
  ): Promise<number> {
    const setClause = Object.keys(data).map(key => `${key} = ?`).join(', ');
    const whereClause = Object.keys(where).map(key => `${key} = ?`).join(' AND ');
    
    const sql = `UPDATE ${table} SET ${setClause} WHERE ${whereClause}`;
    const params = [...Object.values(data), ...Object.values(where)];
    
    return this.execute(sql, params, databaseName);
  }

  /**
   * 删除记录
   */
  public async delete(
    table: string,
    where: Record<string, any>,
    databaseName?: string
  ): Promise<number> {
    const whereClause = Object.keys(where).map(key => `${key} = ?`).join(' AND ');
    const sql = `DELETE FROM ${table} WHERE ${whereClause}`;
    const params = Object.values(where);
    
    return this.execute(sql, params, databaseName);
  }

  /**
   * 查找记录
   */
  public async findOne(
    table: string,
    where: Record<string, any> = {},
    columns: string[] = ['*'],
    databaseName?: string
  ): Promise<QueryResult | null> {
    const selectClause = columns.join(', ');
    let sql = `SELECT ${selectClause} FROM ${table}`;
    const params: any[] = [];
    
    if (Object.keys(where).length > 0) {
      const whereClause = Object.keys(where).map(key => `${key} = ?`).join(' AND ');
      sql += ` WHERE ${whereClause}`;
      params.push(...Object.values(where));
    }
    
    sql += ' LIMIT 1';
    
    const results = await this.query(sql, params, databaseName);
    return results.length > 0 ? results[0] : null;
  }

  /**
   * 查找多条记录
   */
  public async findMany(
    table: string,
    where: Record<string, any> = {},
    columns: string[] = ['*'],
    orderBy?: string,
    limit?: number,
    databaseName?: string
  ): Promise<QueryResult[]> {
    const selectClause = columns.join(', ');
    let sql = `SELECT ${selectClause} FROM ${table}`;
    const params: any[] = [];
    
    if (Object.keys(where).length > 0) {
      const whereClause = Object.keys(where).map(key => `${key} = ?`).join(' AND ');
      sql += ` WHERE ${whereClause}`;
      params.push(...Object.values(where));
    }
    
    if (orderBy) {
      sql += ` ORDER BY ${orderBy}`;
    }
    
    if (limit) {
      sql += ` LIMIT ${limit}`;
    }
    
    return this.query(sql, params, databaseName);
  }

  /**
   * 计数记录
   */
  public async count(
    table: string,
    where: Record<string, any> = {},
    databaseName?: string
  ): Promise<number> {
    let sql = `SELECT COUNT(*) as count FROM ${table}`;
    const params: any[] = [];
    
    if (Object.keys(where).length > 0) {
      const whereClause = Object.keys(where).map(key => `${key} = ?`).join(' AND ');
      sql += ` WHERE ${whereClause}`;
      params.push(...Object.values(where));
    }
    
    const result = await this.query(sql, params, databaseName);
    return result[0]?.count || 0;
  }

  /**
   * 检查表是否存在
   */
  public async tableExists(tableName: string, databaseName?: string): Promise<boolean> {
    const sql = `SELECT name FROM sqlite_master WHERE type='table' AND name=?`;
    const result = await this.query(sql, [tableName], databaseName);
    return result.length > 0;
  }

  /**
   * 获取表信息
   */
  public async getTableInfo(tableName: string, databaseName?: string): Promise<QueryResult[]> {
    const sql = `PRAGMA table_info(${tableName})`;
    return this.query(sql, [], databaseName);
  }

  /**
   * 执行事务
   */
  public async transaction<T>(
    operations: (db: EncryptedDatabaseService) => Promise<T>,
    databaseName?: string
  ): Promise<T> {
    const dbName = databaseName || this.defaultDatabaseName;
    
    try {
      await this.execute('BEGIN TRANSACTION', [], dbName);
      const result = await operations(this);
      await this.execute('COMMIT', [], dbName);
      return result;
    } catch (error) {
      await this.execute('ROLLBACK', [], dbName);
      throw error;
    }
  }

  // === 缓存操作 ===

  /**
   * 设置缓存
   */
  public async setCache(
    key: string,
    value: any,
    expiresInSeconds?: number,
    databaseName?: string
  ): Promise<void> {
    const serializedValue = JSON.stringify(value);
    const expiresAt = expiresInSeconds 
      ? new Date(Date.now() + expiresInSeconds * 1000).toISOString()
      : null;
    
    await this.execute(
      'INSERT OR REPLACE INTO cache_entries (key, value, expires_at) VALUES (?, ?, ?)',
      [key, serializedValue, expiresAt],
      databaseName
    );
  }

  /**
   * 获取缓存
   */
  public async getCache<T>(key: string, databaseName?: string): Promise<T | null> {
    const result = await this.query(
      'SELECT value, expires_at FROM cache_entries WHERE key = ?',
      [key],
      databaseName
    );
    
    if (result.length === 0) {
      return null;
    }
    
    const { value, expires_at } = result[0];
    
    // 检查是否过期
    if (expires_at && new Date(expires_at) < new Date()) {
      await this.deleteCache(key, databaseName);
      return null;
    }
    
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  }

  /**
   * 删除缓存
   */
  public async deleteCache(key: string, databaseName?: string): Promise<void> {
    await this.execute(
      'DELETE FROM cache_entries WHERE key = ?',
      [key],
      databaseName
    );
  }

  /**
   * 清理过期缓存
   */
  public async cleanExpiredCache(databaseName?: string): Promise<number> {
    return this.execute(
      'DELETE FROM cache_entries WHERE expires_at IS NOT NULL AND expires_at < ?',
      [new Date().toISOString()],
      databaseName
    );
  }

  /**
   * 获取初始化状态
   */
  public isInitialized(): boolean {
    return this.initialized;
  }
}

// 导出单例实例
export const encryptedDb = EncryptedDatabaseService.getInstance();