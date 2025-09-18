# 低内存优化配置指南

## 🧠 内存优化核心原理

低内存扫描器专为配置受限的电脑设计，通过以下技术确保在低内存环境下稳定运行：

### 核心技术

#### 1. 流式处理 (Streaming Processing)
```python
# 传统方式（内存消耗大）
with zipfile.ZipFile(jar_path) as jar:
    all_files = jar.extractall()  # 全部解压到内存
    process_all_files(all_files)

# 流式处理（内存恒定）
with zipfile.ZipFile(jar_path) as jar:
    for filename in jar.namelist():
        with jar.open(filename) as f:
            content = f.read(512 * 1024)  # 最多512KB
            process_single_file(content)
            del content  # 立即释放
```

#### 2. 内存监控与自动清理
```python
def check_memory_usage(self):
    """实时监控内存使用"""
    current_memory = psutil.Process().memory_info().rss / 1024**2
    
    if current_memory > self.memory_limit_mb * 0.8:
        logging.warning(f"内存使用接近限制: {current_memory:.1f}MB")
        gc.collect()  # 强制垃圾回收
        
    if current_memory > self.memory_limit_mb:
        raise MemoryError("内存使用超过限制")
```

#### 3. 分批处理与动态调整
```python
def adaptive_batch_processing(self, files, system_memory):
    """根据系统资源动态调整批处理大小"""
    if system_memory < 4096:  # 4GB
        batch_size = 1
    elif system_memory < 8192:  # 8GB
        batch_size = 2
    else:
        batch_size = min(4, len(files) // 10)
    
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        process_batch(batch)
        gc.collect()  # 每批次后清理
```

## ⚙️ 配置参数详解

### 基础配置参数

#### `memory_limit_mb` - 内存限制
```python
# 保守配置（适用于4GB内存）
{
    "memory_limit_mb": 256,  # 限制使用256MB内存
    "description": "确保系统其他程序正常运行"
}

# 平衡配置（适用于8GB内存）
{
    "memory_limit_mb": 512,  # 限制使用512MB内存
    "description": "平衡性能和稳定性"
}

# 积极配置（适用于16GB内存，但仍使用低内存扫描器）
{
    "memory_limit_mb": 1024,  # 限制使用1GB内存
    "description": "在内存充足时提供更好性能"
}
```

#### `batch_size` - 批处理大小
```python
# 各配置下的推荐批处理大小
memory_recommendations = {
    "4GB": {"batch_size": 1, "reason": "最小化内存峰值"},
    "8GB": {"batch_size": 2, "reason": "平衡效率和安全性"},
    "16GB": {"batch_size": 4, "reason": "提高处理效率"}
}
```

#### `max_file_size_mb` - 最大文件大小
```python
# 文件大小限制策略
file_size_limits = {
    "conservative": 30,  # 跳过大于30MB的文件
    "balanced": 50,      # 跳过大于50MB的文件
    "aggressive": 100    # 跳过大于100MB的文件
}
```

### 高级配置参数

#### 内存清理策略
```python
{
    "gc_threshold": 0.8,        # 内存使用率达到80%时触发GC
    "aggressive_gc": True,      # 启用积极垃圾回收
    "gc_interval": 10,          # 每处理10个文件强制GC一次
    "memory_check_interval": 5  # 每5个文件检查一次内存
}
```

#### 流式处理参数
```python
{
    "streaming_threshold": 1024 * 1024,  # 1MB以上文件使用流式处理
    "chunk_size": 512 * 1024,           # 每次读取512KB
    "max_extract_size": 256 * 1024,     # 最大提取256KB内容
    "skip_large_files": True             # 跳过超大文件
}
```

## 🎯 硬件配置推荐

### 低配置电脑（4GB内存）

#### 系统要求
- **内存**: 4GB DDR3/DDR4
- **CPU**: 双核 2.0GHz+
- **存储**: 机械硬盘/SSD
- **可用内存**: ≥ 2GB

#### 推荐配置
```json
{
    "scanner_type": "low_memory",
    "memory_limit_mb": 256,
    "batch_size": 1,
    "max_file_size_mb": 30,
    "gc_threshold": 0.8,
    "aggressive_gc": true,
    "streaming_threshold": 512000,
    "enable_cache": false,
    "max_concurrent_files": 1
}
```

#### 预期性能
- **扫描速度**: 30-50 文件/分钟
- **内存使用**: 150-250MB
- **系统影响**: 最小，其他程序正常运行

### 中等配置电脑（8GB内存）

#### 系统要求
- **内存**: 8GB DDR4
- **CPU**: 四核 2.5GHz+
- **存储**: SSD推荐
- **可用内存**: ≥ 4GB

#### 推荐配置
```json
{
    "scanner_type": "low_memory",
    "memory_limit_mb": 512,
    "batch_size": 2,
    "max_file_size_mb": 50,
    "gc_threshold": 0.7,
    "aggressive_gc": false,
    "streaming_threshold": 1048576,
    "enable_cache": true,
    "cache_size": 200,
    "max_concurrent_files": 2
}
```

#### 预期性能
- **扫描速度**: 50-80 文件/分钟
- **内存使用**: 200-500MB
- **系统影响**: 轻微，多任务处理良好

### 高配置电脑（16GB+内存，但选择保守扫描）

#### 适用场景
- 运行其他内存密集型程序
- 需要最高稳定性保证
- 多用户共享系统
- 服务器环境

#### 推荐配置
```json
{
    "scanner_type": "low_memory",
    "memory_limit_mb": 1024,
    "batch_size": 4,
    "max_file_size_mb": 100,
    "gc_threshold": 0.6,
    "aggressive_gc": false,
    "streaming_threshold": 2097152,
    "enable_cache": true,
    "cache_size": 500,
    "max_concurrent_files": 3,
    "enable_compression": true
}
```

#### 预期性能
- **扫描速度**: 70-120 文件/分钟
- **内存使用**: 300-800MB
- **系统影响**: 几乎无感，可并行运行其他任务

## 🔧 实时配置调优

### 自动配置推荐API

#### 获取系统推荐配置
```bash
curl -X GET "http://localhost:18000/api/v1/scan-low-memory/memory-recommendations"
```

响应示例：
```json
{
    "success": true,
    "system_info": {
        "total_memory_gb": 7.8,
        "available_memory_gb": 4.2,
        "memory_usage_percent": 46.2
    },
    "recommended_config": {
        "config_level": "中等配置模式",
        "memory_limit_mb": 512,
        "batch_size": 2,
        "max_file_size_mb": 50,
        "description": "适用于4-8GB内存的电脑，平衡性能和稳定性"
    },
    "memory_optimization_tips": [
        "💡 关闭其他大型应用程序释放内存",
        "🔄 如果扫描过程中内存不足，会自动降低批处理大小",
        "📊 实时监控内存使用，超过80%时自动清理"
    ]
}
```

#### 实时内存监控
```bash
curl -X GET "http://localhost:18000/api/v1/scan-low-memory/system-memory"
```

响应示例：
```json
{
    "success": true,
    "system_memory": {
        "total_mb": 7982.1,
        "available_mb": 4328.7,
        "used_mb": 3653.4,
        "percent": 45.8,
        "free_mb": 1672.3
    },
    "process_memory": {
        "rss_mb": 156.3,
        "vms_mb": 678.9,
        "percent": 1.96
    },
    "recommendations": {
        "safe_limit_mb": 1298,
        "conservative_limit_mb": 865,
        "status": "充足"
    }
}
```

### 内存压力测试

#### 运行内存测试
```bash
curl -X POST "http://localhost:18000/api/v1/scan-low-memory/memory-test?memory_limit_mb=512&duration_seconds=30"
```

#### 测试结果分析
```json
{
    "success": true,
    "test_results": {
        "initial_memory_mb": 147.2,
        "max_memory_mb": 423.1,
        "final_memory_mb": 152.8,
        "memory_increase_mb": 275.9,
        "gc_triggered_count": 3,
        "memory_limit_mb": 512,
        "limit_exceeded": false
    },
    "assessment": {
        "memory_efficiency": "良好",
        "recommended_action": "当前配置合适"
    }
}
```

## 🚨 故障排除

### 常见内存问题

#### 1. 内存使用过高
**症状**: 扫描过程中系统卡顿
```bash
# 诊断命令
GET /api/v1/scan-low-memory/system-memory

# 解决方案
1. 降低 memory_limit_mb 参数
2. 减小 batch_size 到 1
3. 启用 aggressive_gc
4. 关闭其他应用程序
```

#### 2. 频繁垃圾回收
**症状**: 扫描速度很慢，日志显示频繁GC
```json
// 调整配置
{
    "memory_limit_mb": 256,  // 降低内存限制
    "gc_threshold": 0.9,     // 提高GC阈值
    "batch_size": 1,         // 减少批处理大小
    "max_file_size_mb": 20   // 跳过更多大文件
}
```

#### 3. 内存泄漏检测
```python
# 监控内存趋势
import matplotlib.pyplot as plt
import requests
import time

memory_usage = []
timestamps = []

for i in range(60):  # 监控1分钟
    response = requests.get("http://localhost:18000/api/v1/scan-low-memory/system-memory")
    data = response.json()
    memory_usage.append(data["process_memory"]["rss_mb"])
    timestamps.append(time.time())
    time.sleep(1)

# 绘制内存使用趋势图
plt.plot(timestamps, memory_usage)
plt.xlabel("Time (seconds)")
plt.ylabel("Memory Usage (MB)")
plt.title("Memory Usage Trend")
plt.show()
```

### 性能优化技巧

#### 1. 系统级优化
```bash
# Linux 系统优化
echo 3 > /proc/sys/vm/drop_caches  # 清理系统缓存
swapoff -a && swapon -a           # 重置交换空间

# Windows 系统优化
# 运行磁盘清理工具
# 关闭视觉效果
# 禁用启动项
```

#### 2. 应用级优化
```python
# 扫描前准备
{
    "close_browser_tabs": "关闭浏览器多余标签页",
    "stop_background_apps": "停止后台应用程序",
    "clear_temp_files": "清理临时文件",
    "restart_if_needed": "如果内存碎片严重，重启系统"
}
```

#### 3. 配置文件优化
```json
// ~/.th-suite/low_memory_config.json
{
    "profiles": {
        "ultra_conservative": {
            "memory_limit_mb": 128,
            "batch_size": 1,
            "max_file_size_mb": 20,
            "use_case": "老旧电脑或虚拟机"
        },
        "minimal_impact": {
            "memory_limit_mb": 256,
            "batch_size": 1,
            "max_file_size_mb": 30,
            "use_case": "需要同时运行其他程序"
        },
        "balanced_low_memory": {
            "memory_limit_mb": 512,
            "batch_size": 2,
            "max_file_size_mb": 50,
            "use_case": "专用扫描，追求效率平衡"
        }
    }
}
```

## 📊 监控与告警

### 实时监控Dashboard

创建监控脚本监控扫描过程：

```python
#!/usr/bin/env python3
"""
低内存扫描实时监控脚本
"""
import requests
import time
import json
from datetime import datetime

def monitor_scan(scan_id, interval=5):
    """监控扫描进程"""
    while True:
        try:
            # 获取扫描状态
            scan_response = requests.get(f"http://localhost:18000/api/v1/scan-low-memory/status/{scan_id}")
            scan_data = scan_response.json()
            
            # 获取系统内存
            memory_response = requests.get("http://localhost:18000/api/v1/scan-low-memory/system-memory")
            memory_data = memory_response.json()
            
            # 输出监控信息
            timestamp = datetime.now().strftime("%H:%M:%S")
            progress = scan_data.get("progress", {}).get("percentage", 0)
            memory_percent = memory_data.get("system_memory", {}).get("percent", 0)
            process_memory = memory_data.get("process_memory", {}).get("rss_mb", 0)
            
            print(f"[{timestamp}] 进度: {progress:.1f}% | 系统内存: {memory_percent:.1f}% | 进程内存: {process_memory:.1f}MB")
            
            if scan_data.get("status") in ["completed", "failed", "cancelled"]:
                print(f"扫描结束: {scan_data.get('status')}")
                break
                
            # 内存告警
            if memory_percent > 90:
                print(f"⚠️ 系统内存使用过高: {memory_percent:.1f}%")
            if process_memory > 800:
                print(f"⚠️ 进程内存使用过高: {process_memory:.1f}MB")
                
        except Exception as e:
            print(f"监控错误: {e}")
            
        time.sleep(interval)

if __name__ == "__main__":
    scan_id = input("请输入扫描ID: ")
    monitor_scan(scan_id)
```

### 自动化告警

```python
def setup_memory_alerts():
    """设置内存使用告警"""
    alerts = {
        "system_memory_high": {
            "threshold": 85,
            "action": "pause_scan",
            "message": "系统内存使用过高，暂停扫描"
        },
        "process_memory_high": {
            "threshold": 1024,  # MB
            "action": "reduce_batch_size",
            "message": "进程内存过高，降低批处理大小"
        },
        "gc_frequent": {
            "threshold": 10,  # 每分钟GC次数
            "action": "reduce_memory_limit",
            "message": "频繁垃圾回收，建议降低内存限制"
        }
    }
    return alerts
```

---

通过本指南，您可以根据具体的硬件配置和使用需求，精确调优低内存扫描器的各项参数，确保在资源受限的环境下获得最佳的扫描体验。