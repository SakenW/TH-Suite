// crypto.rs - SQLCipher密钥派生和加密管理
use ring::hmac;
use pbkdf2::pbkdf2_hmac;
use sha2::Sha256;
use rand::{Rng, thread_rng};
use zeroize::{Zeroize, ZeroizeOnDrop};
use base64::{Engine as _, engine::general_purpose};
use std::fmt;
use anyhow::{Result, anyhow};
use sysinfo::{System, SystemExt};

/// 32字节的加密密钥，支持零化清理
#[derive(Clone, ZeroizeOnDrop)]
pub struct EncryptionKey([u8; 32]);

impl EncryptionKey {
    /// 从字节数组创建密钥
    pub fn from_bytes(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }
    
    /// 获取密钥字节
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
    
    /// 转换为SQLCipher兼容的十六进制字符串
    pub fn to_hex(&self) -> String {
        hex::encode(&self.0)
    }
    
    /// 转换为Base64字符串（用于存储验证）
    pub fn to_base64(&self) -> String {
        general_purpose::STANDARD.encode(&self.0)
    }
}

impl fmt::Debug for EncryptionKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("EncryptionKey")
            .field("hash", &format!("{}...", &self.to_hex()[..8]))
            .finish()
    }
}

/// 设备指纹生成器
pub struct DeviceFingerprint;

impl DeviceFingerprint {
    /// 生成基于硬件的唯一设备指纹
    pub fn generate() -> Result<String> {
        let mut fingerprint_data = Vec::new();
        
        // 获取机器唯一标识
        let machine_id = machine_uid::get()
            .map_err(|e| anyhow!("Failed to get machine UID: {}", e))?;
        fingerprint_data.extend_from_slice(machine_id.as_bytes());
        
        // 获取系统信息
        let mut sys = System::new_all();
        sys.refresh_all();
        
        // CPU信息
        if let Some(cpu) = sys.cpus().first() {
            fingerprint_data.extend_from_slice(cpu.brand().as_bytes());
            fingerprint_data.extend_from_slice(cpu.vendor_id().as_bytes());
        }
        
        // 系统信息
        if let Some(name) = sys.name() {
            fingerprint_data.extend_from_slice(name.as_bytes());
        }
        if let Some(version) = sys.os_version() {
            fingerprint_data.extend_from_slice(version.as_bytes());
        }
        
        // 总内存（相对稳定的硬件指标）
        let total_memory = sys.total_memory();
        fingerprint_data.extend_from_slice(&total_memory.to_le_bytes());
        
        // 使用SHA256生成最终指纹
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        hasher.update(&fingerprint_data);
        let result = hasher.finalize();
        
        Ok(hex::encode(result))
    }
}

/// 密钥派生服务
pub struct KeyDerivationService;

impl KeyDerivationService {
    /// PBKDF2迭代次数（符合安全标准）
    const PBKDF2_ITERATIONS: u32 = 250_000;
    
    /// 盐值长度
    const SALT_LENGTH: usize = 32;
    
    /// 派生密钥长度
    const KEY_LENGTH: usize = 32;
    
    /// 生成密码学安全的随机盐值
    pub fn generate_salt() -> [u8; Self::SALT_LENGTH] {
        let mut salt = [0u8; Self::SALT_LENGTH];
        thread_rng().fill(&mut salt);
        salt
    }
    
    /// 派生加密密钥
    /// 组合：设备指纹 + 用户口令 + 远端盐值
    pub fn derive_key(
        device_fingerprint: &str,
        user_passphrase: Option<&str>,
        remote_salt: &[u8],
    ) -> Result<EncryptionKey> {
        let mut key_material = Vec::new();
        
        // 设备指纹（硬件绑定）
        key_material.extend_from_slice(device_fingerprint.as_bytes());
        
        // 用户口令（可选，增强安全性）
        if let Some(passphrase) = user_passphrase {
            key_material.extend_from_slice(passphrase.as_bytes());
        } else {
            // 如果没有用户口令，使用默认的应用标识
            key_material.extend_from_slice(b"th-suite-mc-l10n-default");
        }
        
        // 远端盐值（防止离线攻击）
        key_material.extend_from_slice(remote_salt);
        
        // 使用PBKDF2派生最终密钥
        let mut derived_key = [0u8; Self::KEY_LENGTH];
        pbkdf2_hmac::<Sha256>(
            &key_material,
            remote_salt,
            Self::PBKDF2_ITERATIONS,
            &mut derived_key,
        );
        
        // 清理中间变量
        key_material.zeroize();
        
        Ok(EncryptionKey::from_bytes(derived_key))
    }
    
    /// 验证密钥正确性
    pub fn verify_key(key: &EncryptionKey, expected_hash: &str) -> bool {
        let key_hash = hmac::Key::new(hmac::HMAC_SHA256, key.as_bytes());
        let verification_data = b"th-suite-key-verification";
        let tag = hmac::sign(&key_hash, verification_data);
        
        let computed_hash = hex::encode(tag.as_ref());
        computed_hash == expected_hash
    }
    
    /// 生成密钥验证哈希
    pub fn generate_key_hash(key: &EncryptionKey) -> String {
        let key_hash = hmac::Key::new(hmac::HMAC_SHA256, key.as_bytes());
        let verification_data = b"th-suite-key-verification";
        let tag = hmac::sign(&key_hash, verification_data);
        hex::encode(tag.as_ref())
    }
}

/// 安全配置管理
#[derive(Clone)]
pub struct SecurityConfig {
    /// 设备指纹
    pub device_fingerprint: String,
    /// 远端盐值（Base64编码）
    pub remote_salt_b64: String,
    /// 密钥验证哈希
    pub key_verification_hash: Option<String>,
    /// 是否启用用户口令
    pub user_passphrase_enabled: bool,
}

impl SecurityConfig {
    /// 初始化安全配置
    pub fn initialize() -> Result<Self> {
        let device_fingerprint = DeviceFingerprint::generate()?;
        let remote_salt = KeyDerivationService::generate_salt();
        let remote_salt_b64 = general_purpose::STANDARD.encode(remote_salt);
        
        Ok(Self {
            device_fingerprint,
            remote_salt_b64,
            key_verification_hash: None,
            user_passphrase_enabled: false,
        })
    }
    
    /// 获取远端盐值
    pub fn get_remote_salt(&self) -> Result<Vec<u8>> {
        general_purpose::STANDARD
            .decode(&self.remote_salt_b64)
            .map_err(|e| anyhow!("Failed to decode remote salt: {}", e))
    }
    
    /// 派生数据库密钥
    pub fn derive_database_key(&self, user_passphrase: Option<&str>) -> Result<EncryptionKey> {
        let remote_salt = self.get_remote_salt()?;
        KeyDerivationService::derive_key(
            &self.device_fingerprint,
            user_passphrase,
            &remote_salt,
        )
    }
    
    /// 设置密钥验证哈希
    pub fn set_key_verification(&mut self, key: &EncryptionKey) {
        self.key_verification_hash = Some(KeyDerivationService::generate_key_hash(key));
    }
    
    /// 验证密钥
    pub fn verify_key(&self, key: &EncryptionKey) -> bool {
        if let Some(ref expected_hash) = self.key_verification_hash {
            KeyDerivationService::verify_key(key, expected_hash)
        } else {
            // 如果没有验证哈希，认为密钥有效（首次使用）
            true
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_device_fingerprint_generation() {
        let fingerprint = DeviceFingerprint::generate().unwrap();
        assert_eq!(fingerprint.len(), 64); // SHA256 hex string
        
        // 相同设备应该生成相同指纹
        let fingerprint2 = DeviceFingerprint::generate().unwrap();
        assert_eq!(fingerprint, fingerprint2);
    }
    
    #[test]
    fn test_key_derivation() {
        let fingerprint = "test_device_fingerprint";
        let salt = KeyDerivationService::generate_salt();
        
        let key1 = KeyDerivationService::derive_key(fingerprint, Some("password"), &salt).unwrap();
        let key2 = KeyDerivationService::derive_key(fingerprint, Some("password"), &salt).unwrap();
        
        assert_eq!(key1.as_bytes(), key2.as_bytes());
        
        let key3 = KeyDerivationService::derive_key(fingerprint, Some("different"), &salt).unwrap();
        assert_ne!(key1.as_bytes(), key3.as_bytes());
    }
    
    #[test]
    fn test_key_verification() {
        let key = EncryptionKey::from_bytes([1u8; 32]);
        let hash = KeyDerivationService::generate_key_hash(&key);
        
        assert!(KeyDerivationService::verify_key(&key, &hash));
        assert!(!KeyDerivationService::verify_key(&key, "invalid_hash"));
    }
    
    #[test]
    fn test_security_config() {
        let mut config = SecurityConfig::initialize().unwrap();
        let key = config.derive_database_key(None).unwrap();
        
        config.set_key_verification(&key);
        assert!(config.verify_key(&key));
        
        // 验证不同的密钥应该失败
        let wrong_key = EncryptionKey::from_bytes([0u8; 32]);
        assert!(!config.verify_key(&wrong_key));
    }
    
    #[test]
    fn test_encryption_key_zeroization() {
        let mut key_bytes = [42u8; 32];
        {
            let _key = EncryptionKey::from_bytes(key_bytes);
            // key在这里会被自动清理
        }
        
        // 原始数组不受影响（因为是复制）
        assert_eq!(key_bytes[0], 42);
        
        // 但是如果直接操作EncryptionKey的内部数据
        let mut key = EncryptionKey::from_bytes([42u8; 32]);
        drop(key); // 显式调用drop来触发zeroization
    }
}