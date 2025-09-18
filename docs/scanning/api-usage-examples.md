# 扫描API使用示例

## 🚀 快速开始

### 基础扫描流程

```bash
# 1. 启动扫描
curl -X POST "http://localhost:18000/api/v1/scan/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/path/to/minecraft/modpack",
    "incremental": true
  }'

# 响应
{
  "success": true,
  "scan_id": "scan_20241216_143022_abc123",
  "message": "扫描已启动"
}

# 2. 检查扫描状态
curl -X GET "http://localhost:18000/api/v1/scan/status/scan_20241216_143022_abc123"

# 3. 取消扫描（如需要）
curl -X POST "http://localhost:18000/api/v1/scan/cancel/scan_20241216_143022_abc123"
```

## 📊 三种扫描器详细用法

### 1. 标准扫描器

#### 启动基础扫描
```bash
curl -X POST "http://localhost:18000/api/v1/scan/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/home/user/minecraft/mods",
    "incremental": true,
    "scan_options": {
      "skip_hidden_files": true,
      "validate_jar_files": false
    }
  }'
```

#### 响应示例
```json
{
  "success": true,
  "scan_id": "scan_20241216_143022_std001",
  "message": "标准扫描已启动",
  "estimated_duration": "5-10分钟",
  "scanner_type": "simple"
}
```

#### 获取扫描状态
```bash
curl -X GET "http://localhost:18000/api/v1/scan/status/scan_20241216_143022_std001"
```

#### 状态响应示例
```json
{
  "success": true,
  "scan_id": "scan_20241216_143022_std001",
  "status": "running",
  "progress": {
    "percentage": 45.3,
    "current_file": "/path/to/current/mod.jar",
    "processed_files": 127,
    "total_files": 280,
    "found_mods": 89,
    "found_language_files": 423
  },
  "performance": {
    "start_time": "2024-12-16T14:30:22Z",
    "elapsed_seconds": 152,
    "estimated_remaining_seconds": 183,
    "files_per_minute": 50.2
  },
  "memory_usage": {
    "current_mb": 245.6,
    "peak_mb": 312.1
  }
}
```

### 2. 优化扫描器

#### 启动高性能扫描
```bash
curl -X POST "http://localhost:18000/api/v1/scan-optimized/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/path/to/large/modpack",
    "incremental": true,
    "max_workers": 8,
    "enable_smart_cache": true,
    "scan_options": {
      "batch_insert_size": 100,
      "cache_size": 2000,
      "enable_compression": true
    }
  }'
```

#### 响应示例
```json
{
  "success": true,
  "scan_id": "scan_20241216_143022_opt001",
  "message": "优化扫描已启动",
  "configuration": {
    "max_workers": 8,
    "cache_enabled": true,
    "estimated_speed_improvement": "3-5x"
  },
  "scanner_type": "optimized"
}
```

#### 获取高级状态信息
```bash
curl -X GET "http://localhost:18000/api/v1/scan-optimized/status/scan_20241216_143022_opt001"
```

#### 高级状态响应
```json
{
  "success": true,
  "scan_id": "scan_20241216_143022_opt001",
  "status": "running",
  "progress": {
    "percentage": 78.2,
    "current_batch": 15,
    "total_batches": 19,
    "concurrent_workers": 8,
    "queue_size": 12
  },
  "performance": {
    "throughput_files_per_minute": 245.7,
    "cache_hit_rate": 89.3,
    "parallel_efficiency": 85.2
  },
  "cache_statistics": {
    "total_entries": 1847,
    "cache_hits": 1649,
    "cache_misses": 198,
    "hit_rate_percentage": 89.3,
    "memory_usage_mb": 156.2
  },
  "worker_status": [
    {"worker_id": 1, "status": "processing", "current_file": "mod1.jar"},
    {"worker_id": 2, "status": "processing", "current_file": "mod2.jar"},
    {"worker_id": 3, "status": "idle"},
    {"worker_id": 4, "status": "processing", "current_file": "mod3.jar"}
  ]
}
```

#### 缓存管理
```bash
# 查看缓存状态
curl -X GET "http://localhost:18000/api/v1/scan-optimized/cache/status"

# 清理缓存
curl -X POST "http://localhost:18000/api/v1/scan-optimized/cache/clear"

# 缓存统计
curl -X GET "http://localhost:18000/api/v1/scan-optimized/cache/stats"
```

#### 性能基准测试
```bash
curl -X POST "http://localhost:18000/api/v1/scan-optimized/benchmark" \
  -H "Content-Type: application/json" \
  -d '{
    "test_directory": "/path/to/test/modpack",
    "compare_scanners": ["simple", "optimized"],
    "test_duration_minutes": 5
  }'
```

### 3. 低内存扫描器

#### 启动内存优化扫描
```bash
curl -X POST "http://localhost:18000/api/v1/scan-low-memory/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/path/to/modpack",
    "incremental": true,
    "memory_limit_mb": 512,
    "batch_size": 2,
    "max_file_size_mb": 50
  }'
```

#### 响应示例
```json
{
  "success": true,
  "scan_id": "scan_20241216_143022_mem001",
  "message": "低内存扫描已启动",
  "configuration": {
    "memory_limit_mb": 512,
    "batch_size": 2,
    "streaming_enabled": true,
    "gc_monitoring": true
  },
  "scanner_type": "low_memory"
}
```

#### 系统内存分析
```bash
# 获取系统内存信息
curl -X GET "http://localhost:18000/api/v1/scan-low-memory/system-memory"
```

#### 系统内存响应
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

#### 获取配置推荐
```bash
curl -X GET "http://localhost:18000/api/v1/scan-low-memory/memory-recommendations"
```

#### 配置推荐响应
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

#### 内存使用测试
```bash
curl -X POST "http://localhost:18000/api/v1/scan-low-memory/memory-test?memory_limit_mb=512&duration_seconds=30"
```

#### 内存测试响应
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

## 🔧 高级用法

### 批量扫描多个目录

```bash
#!/bin/bash
# 批量扫描脚本

DIRECTORIES=(
  "/path/to/modpack1"
  "/path/to/modpack2" 
  "/path/to/modpack3"
)

for dir in "${DIRECTORIES[@]}"; do
  echo "开始扫描: $dir"
  
  # 启动扫描
  response=$(curl -s -X POST "http://localhost:18000/api/v1/scan-optimized/start" \
    -H "Content-Type: application/json" \
    -d "{\"directory\": \"$dir\", \"incremental\": true}")
  
  scan_id=$(echo $response | jq -r '.scan_id')
  echo "扫描ID: $scan_id"
  
  # 等待扫描完成
  while true; do
    status_response=$(curl -s -X GET "http://localhost:18000/api/v1/scan-optimized/status/$scan_id")
    status=$(echo $status_response | jq -r '.status')
    
    if [[ "$status" == "completed" ]]; then
      echo "扫描完成: $dir"
      break
    elif [[ "$status" == "failed" ]]; then
      echo "扫描失败: $dir"
      break
    else
      progress=$(echo $status_response | jq -r '.progress.percentage')
      echo "进度: $progress%"
      sleep 10
    fi
  done
  
  echo "---"
done
```

### 监控扫描进度

```bash
#!/bin/bash
# 实时监控脚本

SCAN_ID=$1

if [ -z "$SCAN_ID" ]; then
  echo "用法: $0 <scan_id>"
  exit 1
fi

echo "监控扫描: $SCAN_ID"
echo "按 Ctrl+C 停止监控"

while true; do
  response=$(curl -s -X GET "http://localhost:18000/api/v1/scan/status/$SCAN_ID")
  
  if [ $? -ne 0 ]; then
    echo "无法连接到API服务器"
    sleep 5
    continue
  fi
  
  status=$(echo $response | jq -r '.status')
  progress=$(echo $response | jq -r '.progress.percentage')
  current_file=$(echo $response | jq -r '.progress.current_file')
  files_per_minute=$(echo $response | jq -r '.performance.files_per_minute')
  
  timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  if [[ "$status" == "completed" ]]; then
    echo "[$timestamp] 扫描完成！"
    break
  elif [[ "$status" == "failed" ]]; then
    echo "[$timestamp] 扫描失败！"
    break
  elif [[ "$status" == "cancelled" ]]; then
    echo "[$timestamp] 扫描已取消"
    break
  else
    echo "[$timestamp] 进度: $progress% | 速度: $files_per_minute 文件/分钟"
    echo "  当前文件: $(basename "$current_file")"
  fi
  
  sleep 5
done
```

### 配置文件驱动的扫描

```json
// scan_config.json
{
  "profiles": {
    "development": {
      "scanner_type": "simple",
      "incremental": true,
      "scan_options": {
        "skip_hidden_files": true,
        "validate_jar_files": false
      }
    },
    "production": {
      "scanner_type": "optimized", 
      "incremental": true,
      "max_workers": 8,
      "enable_smart_cache": true,
      "scan_options": {
        "batch_insert_size": 100,
        "cache_size": 2000
      }
    },
    "low_memory": {
      "scanner_type": "low_memory",
      "incremental": true,
      "memory_limit_mb": 256,
      "batch_size": 1,
      "max_file_size_mb": 30
    }
  },
  "directories": [
    "/path/to/modpack1",
    "/path/to/modpack2"
  ]
}
```

```python
#!/usr/bin/env python3
# scan_from_config.py

import json
import requests
import time
import sys

def load_config(config_file):
    with open(config_file, 'r') as f:
        return json.load(f)

def start_scan(directory, profile_config):
    scanner_type = profile_config['scanner_type']
    
    # 根据扫描器类型选择API端点
    endpoints = {
        'simple': '/api/v1/scan/start',
        'optimized': '/api/v1/scan-optimized/start', 
        'low_memory': '/api/v1/scan-low-memory/start'
    }
    
    endpoint = endpoints[scanner_type]
    url = f"http://localhost:18000{endpoint}"
    
    # 准备请求数据
    request_data = {
        'directory': directory,
        **profile_config
    }
    
    # 移除scanner_type，因为它不是API参数
    request_data.pop('scanner_type', None)
    
    response = requests.post(url, json=request_data)
    return response.json()

def monitor_scan(scan_id, scanner_type):
    endpoints = {
        'simple': f'/api/v1/scan/status/{scan_id}',
        'optimized': f'/api/v1/scan-optimized/status/{scan_id}',
        'low_memory': f'/api/v1/scan-low-memory/status/{scan_id}'
    }
    
    endpoint = endpoints[scanner_type]
    url = f"http://localhost:18000{endpoint}"
    
    while True:
        response = requests.get(url)
        data = response.json()
        
        status = data.get('status')
        progress = data.get('progress', {}).get('percentage', 0)
        
        print(f"扫描 {scan_id}: {status} - {progress:.1f}%")
        
        if status in ['completed', 'failed', 'cancelled']:
            break
            
        time.sleep(5)

def main():
    if len(sys.argv) != 3:
        print("用法: python3 scan_from_config.py <config_file> <profile_name>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    profile_name = sys.argv[2]
    
    config = load_config(config_file)
    profile = config['profiles'][profile_name]
    directories = config['directories']
    
    for directory in directories:
        print(f"开始扫描目录: {directory}")
        print(f"使用配置: {profile_name}")
        
        result = start_scan(directory, profile)
        
        if result['success']:
            scan_id = result['scan_id']
            print(f"扫描已启动: {scan_id}")
            monitor_scan(scan_id, profile['scanner_type'])
        else:
            print(f"扫描启动失败: {result.get('detail', '未知错误')}")

if __name__ == "__main__":
    main()
```

### 使用示例

```bash
# 开发环境扫描
python3 scan_from_config.py scan_config.json development

# 生产环境高性能扫描  
python3 scan_from_config.py scan_config.json production

# 低内存环境扫描
python3 scan_from_config.py scan_config.json low_memory
```

## 🚨 错误处理

### 常见错误响应

#### 1. 目录不存在
```json
{
  "success": false,
  "error": "DirectoryNotFound",
  "detail": "目录不存在: /invalid/path",
  "status_code": 400
}
```

#### 2. 扫描器忙碌
```json
{
  "success": false,
  "error": "ScannerBusy", 
  "detail": "扫描器正在处理其他任务",
  "status_code": 409,
  "retry_after_seconds": 30
}
```

#### 3. 内存不足
```json
{
  "success": false,
  "error": "InsufficientMemory",
  "detail": "可用内存不足以启动扫描",
  "status_code": 507,
  "recommended_action": "减少memory_limit_mb参数或使用低内存扫描器"
}
```

#### 4. 权限不足
```json
{
  "success": false,
  "error": "PermissionDenied",
  "detail": "无法访问目录: /restricted/path",
  "status_code": 403
}
```

### 错误处理示例

```bash
#!/bin/bash
# 错误处理示例

start_scan_with_retry() {
  local directory=$1
  local max_retries=3
  local retry_count=0
  
  while [ $retry_count -lt $max_retries ]; do
    response=$(curl -s -X POST "http://localhost:18000/api/v1/scan/start" \
      -H "Content-Type: application/json" \
      -d "{\"directory\": \"$directory\", \"incremental\": true}")
    
    success=$(echo $response | jq -r '.success')
    
    if [ "$success" = "true" ]; then
      echo "扫描启动成功"
      scan_id=$(echo $response | jq -r '.scan_id')
      echo "扫描ID: $scan_id"
      return 0
    else
      error=$(echo $response | jq -r '.error')
      detail=$(echo $response | jq -r '.detail')
      
      echo "扫描启动失败: $error - $detail"
      
      case "$error" in
        "ScannerBusy")
          retry_after=$(echo $response | jq -r '.retry_after_seconds // 30')
          echo "扫描器忙碌，${retry_after}秒后重试..."
          sleep $retry_after
          ;;
        "InsufficientMemory")
          echo "内存不足，切换到低内存扫描器..."
          # 重试使用低内存扫描器
          response=$(curl -s -X POST "http://localhost:18000/api/v1/scan-low-memory/start" \
            -H "Content-Type: application/json" \
            -d "{\"directory\": \"$directory\", \"memory_limit_mb\": 256}")
          success=$(echo $response | jq -r '.success')
          if [ "$success" = "true" ]; then
            echo "低内存扫描启动成功"
            return 0
          fi
          ;;
        "DirectoryNotFound"|"PermissionDenied")
          echo "无法恢复的错误，跳过此目录"
          return 1
          ;;
      esac
    fi
    
    retry_count=$((retry_count + 1))
    echo "重试 $retry_count/$max_retries..."
    sleep 5
  done
  
  echo "达到最大重试次数，扫描失败"
  return 1
}

# 使用示例
start_scan_with_retry "/path/to/modpack"
```

## 📊 性能监控

### 实时性能监控

```python
#!/usr/bin/env python3
# performance_monitor.py

import requests
import time
import json
from datetime import datetime
import matplotlib.pyplot as plt

class ScanPerformanceMonitor:
    def __init__(self, base_url="http://localhost:18000"):
        self.base_url = base_url
        self.metrics_history = []
    
    def monitor_scan(self, scan_id, scanner_type="simple", interval=5):
        """监控扫描性能"""
        endpoints = {
            'simple': f'/api/v1/scan/status/{scan_id}',
            'optimized': f'/api/v1/scan-optimized/status/{scan_id}',
            'low_memory': f'/api/v1/scan-low-memory/status/{scan_id}'
        }
        
        endpoint = endpoints[scanner_type]
        
        print(f"开始监控扫描: {scan_id}")
        print("时间戳\t\t\t进度\t内存(MB)\t速度(文件/分钟)")
        print("-" * 70)
        
        while True:
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                data = response.json()
                
                if not data.get('success'):
                    print(f"获取状态失败: {data}")
                    break
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                status = data.get('status')
                progress = data.get('progress', {})
                performance = data.get('performance', {})
                memory = data.get('memory_usage', {})
                
                # 收集指标
                metrics = {
                    'timestamp': time.time(),
                    'progress_percent': progress.get('percentage', 0),
                    'memory_mb': memory.get('current_mb', 0),
                    'files_per_minute': performance.get('files_per_minute', 0),
                    'status': status
                }
                self.metrics_history.append(metrics)
                
                # 显示当前状态
                print(f"{timestamp}\t\t{metrics['progress_percent']:.1f}%\t{metrics['memory_mb']:.1f}\t\t{metrics['files_per_minute']:.1f}")
                
                if status in ['completed', 'failed', 'cancelled']:
                    print(f"\n扫描结束: {status}")
                    break
                    
                time.sleep(interval)
                
            except Exception as e:
                print(f"监控错误: {e}")
                time.sleep(interval)
    
    def generate_report(self, output_file="scan_performance_report.png"):
        """生成性能报告图表"""
        if not self.metrics_history:
            print("没有性能数据")
            return
        
        timestamps = [m['timestamp'] for m in self.metrics_history]
        progress = [m['progress_percent'] for m in self.metrics_history]
        memory = [m['memory_mb'] for m in self.metrics_history]
        speed = [m['files_per_minute'] for m in self.metrics_history]
        
        # 创建子图
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 进度图
        ax1.plot(timestamps, progress, 'b-', linewidth=2)
        ax1.set_title('扫描进度')
        ax1.set_ylabel('进度 (%)')
        ax1.grid(True)
        
        # 内存使用图
        ax2.plot(timestamps, memory, 'r-', linewidth=2)
        ax2.set_title('内存使用')
        ax2.set_ylabel('内存 (MB)')
        ax2.grid(True)
        
        # 处理速度图
        ax3.plot(timestamps, speed, 'g-', linewidth=2)
        ax3.set_title('处理速度')
        ax3.set_ylabel('文件/分钟')
        ax3.grid(True)
        
        # 综合效率图
        ax4.scatter(memory, speed, c=progress, cmap='viridis', alpha=0.6)
        ax4.set_xlabel('内存使用 (MB)')
        ax4.set_ylabel('处理速度 (文件/分钟)')
        ax4.set_title('内存-速度关系图')
        colorbar = plt.colorbar(ax4.collections[0], ax=ax4)
        colorbar.set_label('进度 (%)')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"性能报告已保存: {output_file}")

# 使用示例
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python3 performance_monitor.py <scan_id> <scanner_type>")
        sys.exit(1)
    
    scan_id = sys.argv[1]
    scanner_type = sys.argv[2]
    
    monitor = ScanPerformanceMonitor()
    monitor.monitor_scan(scan_id, scanner_type)
    monitor.generate_report(f"scan_{scan_id}_performance.png")
```

---

通过这些详细的API使用示例，您可以充分利用MC L10n的三种扫描器，根据不同的需求和环境选择最适合的扫描方案。