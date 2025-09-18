# 性能测试与故障排除指南

## 🧪 性能测试

### 基准测试框架

#### 自动化基准测试
```bash
# 使用内置基准测试API
curl -X POST "http://localhost:18000/api/v1/scan-optimized/benchmark" \
  -H "Content-Type: application/json" \
  -d '{
    "test_directory": "/path/to/test/modpack",
    "compare_scanners": ["simple", "optimized", "low_memory"],
    "test_iterations": 3,
    "warm_up_runs": 1
  }'
```

#### 基准测试响应示例
```json
{
  "success": true,
  "benchmark_id": "bench_20241216_143022",
  "test_configuration": {
    "test_directory": "/path/to/test/modpack",
    "total_files": 1247,
    "total_size_mb": 2156.7,
    "test_iterations": 3
  },
  "results": {
    "simple_scanner": {
      "average_duration_seconds": 187.4,
      "average_memory_peak_mb": 645.2,
      "average_throughput_files_per_minute": 398.7,
      "success_rate": 100.0,
      "consistency_score": 0.92
    },
    "optimized_scanner": {
      "average_duration_seconds": 52.1,
      "average_memory_peak_mb": 287.3,
      "average_throughput_files_per_minute": 1434.8,
      "success_rate": 100.0,
      "consistency_score": 0.95,
      "cache_hit_rate": 89.2
    },
    "low_memory_scanner": {
      "average_duration_seconds": 142.6,
      "average_memory_peak_mb": 156.9,
      "average_throughput_files_per_minute": 524.3,
      "success_rate": 100.0,
      "consistency_score": 0.88
    }
  },
  "performance_comparison": {
    "speed_ranking": ["optimized", "simple", "low_memory"],
    "memory_ranking": ["low_memory", "optimized", "simple"],
    "overall_efficiency": ["optimized", "low_memory", "simple"]
  },
  "recommendations": {
    "for_performance": "使用优化扫描器可获得3.6倍速度提升",
    "for_memory": "低内存扫描器内存使用仅为标准扫描器的24%",
    "for_stability": "所有扫描器成功率均为100%，推荐根据硬件配置选择"
  }
}
```

### 自定义性能测试脚本

#### 综合性能测试
```python
#!/usr/bin/env python3
"""
MC L10n扫描器综合性能测试工具
"""
import requests
import time
import json
import psutil
import statistics
from pathlib import Path
from datetime import datetime
import argparse

class ScannerBenchmark:
    def __init__(self, base_url="http://localhost:18000"):
        self.base_url = base_url
        self.results = {}
    
    def test_scanner(self, scanner_type, test_directory, iterations=3):
        """测试指定扫描器性能"""
        print(f"\n🧪 测试 {scanner_type} 扫描器")
        print("=" * 50)
        
        endpoints = {
            'simple': '/api/v1/scan/start',
            'optimized': '/api/v1/scan-optimized/start',
            'low_memory': '/api/v1/scan-low-memory/start'
        }
        
        status_endpoints = {
            'simple': '/api/v1/scan/status',
            'optimized': '/api/v1/scan-optimized/status',
            'low_memory': '/api/v1/scan-low-memory/status'
        }
        
        test_results = []
        
        for i in range(iterations):
            print(f"\n第 {i+1}/{iterations} 次测试")
            
            # 清理缓存（如果支持）
            if scanner_type == 'optimized':
                requests.post(f"{self.base_url}/api/v1/scan-optimized/cache/clear")
            
            # 启动扫描
            start_payload = {
                'directory': test_directory,
                'incremental': False  # 完整扫描确保一致性
            }
            
            if scanner_type == 'optimized':
                start_payload.update({
                    'max_workers': 8,
                    'enable_smart_cache': True
                })
            elif scanner_type == 'low_memory':
                start_payload.update({
                    'memory_limit_mb': 512,
                    'batch_size': 2
                })
            
            start_time = time.time()
            initial_memory = psutil.Process().memory_info().rss / 1024**2
            
            response = requests.post(f"{self.base_url}{endpoints[scanner_type]}", 
                                   json=start_payload)
            
            if not response.json().get('success'):
                print(f"启动失败: {response.json()}")
                continue
            
            scan_id = response.json()['scan_id']
            
            # 监控扫描过程
            peak_memory = initial_memory
            memory_samples = []
            last_progress = 0
            
            while True:
                status_response = requests.get(f"{self.base_url}{status_endpoints[scanner_type]}/{scan_id}")
                status_data = status_response.json()
                
                if not status_data.get('success'):
                    break
                
                status = status_data.get('status')
                progress = status_data.get('progress', {}).get('percentage', 0)
                
                # 记录内存使用
                current_memory = psutil.Process().memory_info().rss / 1024**2
                peak_memory = max(peak_memory, current_memory)
                memory_samples.append(current_memory)
                
                if progress > last_progress:
                    print(f"  进度: {progress:.1f}% | 内存: {current_memory:.1f}MB")
                    last_progress = progress
                
                if status in ['completed', 'failed', 'cancelled']:
                    break
                
                time.sleep(1)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 收集结果
            final_status = status_data.get('status')
            progress_info = status_data.get('progress', {})
            
            test_result = {
                'iteration': i + 1,
                'success': final_status == 'completed',
                'duration_seconds': duration,
                'peak_memory_mb': peak_memory,
                'average_memory_mb': statistics.mean(memory_samples) if memory_samples else 0,
                'files_processed': progress_info.get('processed_files', 0),
                'mods_found': progress_info.get('found_mods', 0),
                'language_files_found': progress_info.get('found_language_files', 0),
                'throughput': (progress_info.get('processed_files', 0) / duration * 60) if duration > 0 else 0
            }
            
            test_results.append(test_result)
            
            print(f"  ✅ 完成: {duration:.1f}秒 | 峰值内存: {peak_memory:.1f}MB | 吞吐量: {test_result['throughput']:.1f} 文件/分钟")
            
            # 间隔时间让系统稳定
            time.sleep(5)
        
        # 计算统计结果
        successful_tests = [r for r in test_results if r['success']]
        
        if successful_tests:
            stats = {
                'scanner_type': scanner_type,
                'total_tests': len(test_results),
                'successful_tests': len(successful_tests),
                'success_rate': len(successful_tests) / len(test_results) * 100,
                'average_duration': statistics.mean([r['duration_seconds'] for r in successful_tests]),
                'median_duration': statistics.median([r['duration_seconds'] for r in successful_tests]),
                'std_duration': statistics.stdev([r['duration_seconds'] for r in successful_tests]) if len(successful_tests) > 1 else 0,
                'average_peak_memory': statistics.mean([r['peak_memory_mb'] for r in successful_tests]),
                'average_throughput': statistics.mean([r['throughput'] for r in successful_tests]),
                'consistency_score': 1 - (statistics.stdev([r['throughput'] for r in successful_tests]) / statistics.mean([r['throughput'] for r in successful_tests])) if len(successful_tests) > 1 else 1,
                'raw_results': test_results
            }
            
            self.results[scanner_type] = stats
            return stats
        else:
            print(f"❌ {scanner_type} 扫描器所有测试都失败了")
            return None
    
    def run_comprehensive_test(self, test_directory, iterations=3):
        """运行全面性能测试"""
        print(f"🚀 开始综合性能测试")
        print(f"测试目录: {test_directory}")
        print(f"测试轮次: {iterations}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 检查目录
        if not Path(test_directory).exists():
            raise FileNotFoundError(f"测试目录不存在: {test_directory}")
        
        # 测试所有扫描器
        scanners = ['simple', 'optimized', 'low_memory']
        
        for scanner in scanners:
            self.test_scanner(scanner, test_directory, iterations)
        
        # 生成对比报告
        self.generate_comparison_report()
    
    def generate_comparison_report(self):
        """生成对比报告"""
        if not self.results:
            print("没有测试结果可供对比")
            return
        
        print("\n" + "=" * 80)
        print("📊 性能对比报告")
        print("=" * 80)
        
        # 表格标题
        print(f"{'扫描器':<12} {'成功率':<8} {'平均时间(s)':<12} {'内存峰值(MB)':<14} {'吞吐量(f/m)':<12} {'一致性':<8}")
        print("-" * 80)
        
        # 对比数据
        for scanner_type, stats in self.results.items():
            print(f"{scanner_type:<12} {stats['success_rate']:<7.1f}% {stats['average_duration']:<11.1f} {stats['average_peak_memory']:<13.1f} {stats['average_throughput']:<11.1f} {stats['consistency_score']:<7.3f}")
        
        # 性能排名
        print("\n🏆 性能排名:")
        
        # 速度排名
        speed_ranking = sorted(self.results.items(), key=lambda x: x[1]['average_throughput'], reverse=True)
        print("  速度排名:")
        for i, (scanner, stats) in enumerate(speed_ranking, 1):
            print(f"    {i}. {scanner}: {stats['average_throughput']:.1f} 文件/分钟")
        
        # 内存效率排名
        memory_ranking = sorted(self.results.items(), key=lambda x: x[1]['average_peak_memory'])
        print("  内存效率排名:")
        for i, (scanner, stats) in enumerate(memory_ranking, 1):
            print(f"    {i}. {scanner}: {stats['average_peak_memory']:.1f} MB")
        
        # 稳定性排名
        stability_ranking = sorted(self.results.items(), key=lambda x: (x[1]['success_rate'], x[1]['consistency_score']), reverse=True)
        print("  稳定性排名:")
        for i, (scanner, stats) in enumerate(stability_ranking, 1):
            print(f"    {i}. {scanner}: {stats['success_rate']:.1f}%成功率, {stats['consistency_score']:.3f}一致性")
        
        # 建议
        print("\n💡 使用建议:")
        best_speed = speed_ranking[0][0]
        best_memory = memory_ranking[0][0]
        best_stability = stability_ranking[0][0]
        
        print(f"  • 追求最高性能: {best_speed} (吞吐量 {self.results[best_speed]['average_throughput']:.1f} 文件/分钟)")
        print(f"  • 内存受限环境: {best_memory} (峰值内存 {self.results[best_memory]['average_peak_memory']:.1f} MB)")
        print(f"  • 要求最高稳定性: {best_stability} (成功率 {self.results[best_stability]['success_rate']:.1f}%)")
        
        # 保存详细结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"scan_benchmark_{timestamp}.json"
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细结果已保存到: {result_file}")

def main():
    parser = argparse.ArgumentParser(description='MC L10n扫描器性能测试工具')
    parser.add_argument('directory', help='测试目录路径')
    parser.add_argument('--iterations', '-i', type=int, default=3, help='测试轮次 (默认: 3)')
    parser.add_argument('--base-url', default='http://localhost:18000', help='API基础URL')
    parser.add_argument('--scanners', nargs='+', choices=['simple', 'optimized', 'low_memory'], 
                       default=['simple', 'optimized', 'low_memory'], help='要测试的扫描器')
    
    args = parser.parse_args()
    
    benchmark = ScannerBenchmark(args.base_url)
    
    try:
        if len(args.scanners) == 3:
            benchmark.run_comprehensive_test(args.directory, args.iterations)
        else:
            # 只测试指定的扫描器
            for scanner in args.scanners:
                benchmark.test_scanner(scanner, args.directory, args.iterations)
            benchmark.generate_comparison_report()
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    main()
```

### 使用示例

```bash
# 基础性能测试
python3 performance_test.py "/path/to/modpack"

# 高级配置测试
python3 performance_test.py "/path/to/modpack" --iterations 5 --scanners optimized low_memory

# 自定义API地址测试
python3 performance_test.py "/path/to/modpack" --base-url "http://192.168.1.100:18000"
```

## 🚨 故障排除

### 常见问题诊断

#### 1. 扫描无响应

**症状**: 点击扫描后无任何反应，API调用无响应

**诊断步骤**:
```bash
# 1. 检查API服务状态
curl -X GET "http://localhost:18000/health" || echo "API服务不可达"

# 2. 检查进程冲突
ps aux | grep "poetry run python main.py" | wc -l

# 3. 检查端口占用
netstat -tulpn | grep :18000

# 4. 检查日志
tail -f /path/to/logs/app.log
```

**解决方案**:
```bash
# 清理冲突进程
poetry run python main.py --kill-all

# 重启服务
cd /home/saken/project/TH-Suite/apps/mc_l10n/backend
poetry run python main.py

# 验证服务状态
curl -X GET "http://localhost:18000/docs"
```

#### 2. 内存不足导致的问题

**症状**: 扫描过程中系统卡顿，OOM错误

**诊断步骤**:
```bash
# 检查系统内存
curl -X GET "http://localhost:18000/api/v1/scan-low-memory/system-memory"

# 监控内存使用趋势
watch -n 1 'free -h && echo "--- Process Memory ---" && ps aux | grep python | head -5'
```

**解决方案**:
```bash
# 1. 切换到低内存扫描器
curl -X POST "http://localhost:18000/api/v1/scan-low-memory/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/path/to/modpack",
    "memory_limit_mb": 256,
    "batch_size": 1
  }'

# 2. 优化系统内存
# Linux
sudo sysctl vm.swappiness=10
echo 3 | sudo tee /proc/sys/vm/drop_caches

# 3. 关闭其他程序释放内存
```

#### 3. 扫描速度过慢

**症状**: 扫描时间远超预期，进度更新缓慢

**诊断步骤**:
```bash
# 1. 检查磁盘IO
iostat -x 1 5

# 2. 检查CPU使用
top -p $(pgrep -f "python main.py")

# 3. 分析扫描器配置
curl -X GET "http://localhost:18000/api/v1/scan/status/YOUR_SCAN_ID"
```

**解决方案**:
```bash
# 1. 切换到优化扫描器
curl -X POST "http://localhost:18000/api/v1/scan-optimized/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/path/to/modpack",
    "max_workers": 8,
    "enable_smart_cache": true
  }'

# 2. 优化文件系统
# 临时禁用文件索引（Windows）
# 使用SSD而非机械硬盘
# 确保足够的磁盘空间
```

#### 4. 数据库写入问题

**症状**: 扫描完成但数据库中无数据

**诊断步骤**:
```bash
# 1. 检查数据库文件
ls -la *.db *.sqlite

# 2. 检查数据库表结构
sqlite3 app.db ".tables"

# 3. 检查数据库权限
ls -la app.db

# 4. 查看扫描结果
sqlite3 app.db "SELECT COUNT(*) FROM core_mods;"
```

**解决方案**:
```bash
# 1. 重新初始化数据库
rm -f app.db
poetry run python -c "from infrastructure.db_initializer import initialize_database; initialize_database()"

# 2. 检查磁盘空间
df -h .

# 3. 修复权限
chmod 664 app.db
```

#### 5. JAR文件处理错误

**症状**: 特定JAR文件导致扫描失败

**诊断步骤**:
```bash
# 1. 验证JAR文件完整性
unzip -t problematic.jar

# 2. 检查文件权限
ls -la problematic.jar

# 3. 分析文件结构
unzip -l problematic.jar | head -20
```

**解决方案**:
```bash
# 1. 跳过损坏的文件
curl -X POST "http://localhost:18000/api/v1/scan/start" \
  -H "Content-Type: application/json" \
  -d '{
    "directory": "/path/to/modpack",
    "scan_options": {
      "skip_corrupted_files": true,
      "validate_jar_files": false
    }
  }'

# 2. 重新下载损坏的MOD文件
```

### 故障排除自动化脚本

#### 系统健康检查脚本
```bash
#!/bin/bash
# scan_health_check.sh

echo "🩺 MC L10n扫描系统健康检查"
echo "========================================"

# 1. API服务检查
echo -n "API服务状态: "
if curl -s -f "http://localhost:18000/health" > /dev/null; then
    echo "✅ 正常"
else
    echo "❌ 异常"
    echo "  解决方案: 重启后端服务"
fi

# 2. 进程检查
process_count=$(ps aux | grep -c "poetry run python main.py")
echo -n "Python进程数量: $process_count "
if [ $process_count -gt 3 ]; then
    echo "⚠️ 过多 (可能有冲突)"
    echo "  解决方案: poetry run python main.py --kill-all"
elif [ $process_count -eq 0 ]; then
    echo "❌ 无进程"
    echo "  解决方案: 启动后端服务"
else
    echo "✅ 正常"
fi

# 3. 内存检查
available_memory=$(free | awk '/^Mem:/ {printf("%.1f", $7/1024/1024)}')
echo -n "可用内存: ${available_memory}GB "
if (( $(echo "$available_memory < 1.0" | bc -l) )); then
    echo "⚠️ 不足"
    echo "  建议: 使用低内存扫描器"
else
    echo "✅ 充足"
fi

# 4. 磁盘空间检查
disk_usage=$(df . | awk 'NR==2 {print $5}' | sed 's/%//')
echo -n "磁盘使用率: ${disk_usage}% "
if [ $disk_usage -gt 90 ]; then
    echo "⚠️ 过高"
    echo "  建议: 清理磁盘空间"
else
    echo "✅ 正常"
fi

# 5. 数据库检查
if [ -f "app.db" ]; then
    echo -n "数据库状态: "
    if sqlite3 app.db "SELECT 1;" &> /dev/null; then
        table_count=$(sqlite3 app.db ".tables" | wc -w)
        echo "✅ 正常 (${table_count}个表)"
    else
        echo "❌ 损坏"
        echo "  解决方案: 重新初始化数据库"
    fi
else
    echo "数据库状态: ❌ 不存在"
    echo "  解决方案: 初始化数据库"
fi

# 6. 端口检查
echo -n "端口18000状态: "
if netstat -tlnp 2>/dev/null | grep -q ":18000 "; then
    echo "✅ 已监听"
else
    echo "❌ 未监听"
    echo "  解决方案: 启动后端服务"
fi

echo ""
echo "🔧 快速修复命令:"
echo "  重启服务: cd $PWD && poetry run python main.py"
echo "  清理进程: poetry run python main.py --kill-all"
echo "  重建数据库: rm -f app.db && poetry run python -c 'from infrastructure.db_initializer import initialize_database; initialize_database()'"
```

#### 性能问题诊断脚本
```python
#!/usr/bin/env python3
# performance_diagnostic.py

import requests
import psutil
import time
import json

def diagnose_performance_issues():
    """诊断性能问题"""
    print("🔍 性能问题诊断工具")
    print("=" * 40)
    
    issues = []
    recommendations = []
    
    # 1. 系统资源检查
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)
    disk_usage = psutil.disk_usage('.')
    
    print(f"💻 系统资源状态:")
    print(f"  内存使用: {memory.percent:.1f}% ({memory.available/1024**3:.1f}GB 可用)")
    print(f"  CPU使用: {cpu_percent:.1f}%")
    print(f"  磁盘使用: {disk_usage.percent:.1f}%")
    
    # 内存问题
    if memory.percent > 85:
        issues.append("系统内存使用过高")
        recommendations.append("使用低内存扫描器，降低memory_limit_mb参数")
    
    # CPU问题
    if cpu_percent > 90:
        issues.append("CPU使用率过高")
        recommendations.append("减少max_workers参数或等待其他任务完成")
    
    # 磁盘问题
    if disk_usage.percent > 95:
        issues.append("磁盘空间不足")
        recommendations.append("清理磁盘空间或移动扫描目标到其他磁盘")
    
    # 2. API服务检查
    try:
        response = requests.get("http://localhost:18000/health", timeout=5)
        if response.status_code == 200:
            print("🌐 API服务: ✅ 正常")
        else:
            print(f"🌐 API服务: ❌ 异常 (状态码: {response.status_code})")
            issues.append("API服务响应异常")
            recommendations.append("重启后端服务")
    except Exception as e:
        print(f"🌐 API服务: ❌ 无法连接 ({e})")
        issues.append("API服务不可达")
        recommendations.append("检查后端服务是否启动")
    
    # 3. 扫描器状态检查
    try:
        memory_response = requests.get("http://localhost:18000/api/v1/scan-low-memory/system-memory", timeout=5)
        if memory_response.status_code == 200:
            memory_data = memory_response.json()
            recommendations_data = memory_data.get("recommendations", {})
            
            print(f"🧠 内存分析:")
            print(f"  推荐安全限制: {recommendations_data.get('safe_limit_mb', 'N/A')}MB")
            print(f"  保守限制: {recommendations_data.get('conservative_limit_mb', 'N/A')}MB")
            print(f"  状态: {recommendations_data.get('status', 'N/A')}")
            
            if recommendations_data.get('status') == '不足':
                issues.append("系统内存严重不足")
                recommendations.append(f"使用保守内存限制: {recommendations_data.get('conservative_limit_mb')}MB")
                
    except Exception as e:
        print(f"🧠 内存分析: ❌ 无法获取 ({e})")
    
    # 4. 进程检查
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
        try:
            if 'python' in proc.info['name'].lower() and any('main.py' in cmd for cmd in proc.info['cmdline']):
                python_processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print(f"🐍 Python进程: {len(python_processes)}个")
    if len(python_processes) > 2:
        issues.append(f"检测到{len(python_processes)}个Python进程，可能存在冲突")
        recommendations.append("执行: poetry run python main.py --kill-all")
    
    for proc in python_processes[:3]:  # 只显示前3个
        memory_mb = proc['memory_info'].rss / 1024**2
        print(f"  PID {proc['pid']}: {memory_mb:.1f}MB")
    
    # 5. 生成报告
    print("\n" + "=" * 40)
    if issues:
        print("❌ 发现问题:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n💡 建议解决方案:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    else:
        print("✅ 未发现明显性能问题")
        print("如果仍然遇到性能问题，请检查:")
        print("  - 扫描目标目录的文件数量和大小")
        print("  - 网络连接稳定性")
        print("  - 防火墙和杀毒软件设置")
    
    # 6. 生成配置建议
    if memory.total / 1024**3 < 8:  # 小于8GB
        print(f"\n🎯 推荐配置 (基于{memory.total/1024**3:.1f}GB内存):")
        print("  扫描器: low_memory")
        print("  内存限制: 256MB")
        print("  批处理大小: 1")
    else:
        print(f"\n🎯 推荐配置 (基于{memory.total/1024**3:.1f}GB内存):")
        print("  扫描器: optimized")
        print("  最大工作线程: 4-8")
        print("  启用智能缓存: true")

if __name__ == "__main__":
    diagnose_performance_issues()
```

### 使用故障排除工具

```bash
# 运行系统健康检查
chmod +x scan_health_check.sh
./scan_health_check.sh

# 运行性能诊断
python3 performance_diagnostic.py

# 持续监控扫描性能
python3 performance_monitor.py SCAN_ID optimized
```

## 📋 故障排除检查清单

### 扫描前检查
- [ ] API服务正常运行 (http://localhost:18000/health)
- [ ] 无冲突的Python进程
- [ ] 目标目录存在且可访问
- [ ] 可用内存 > 2GB (或适配扫描器类型)
- [ ] 磁盘空间 > 10% 可用

### 扫描过程监控
- [ ] 进度正常更新 (每分钟检查一次)
- [ ] 内存使用稳定 (不超过设定限制)
- [ ] CPU使用合理 (不持续100%)
- [ ] 无错误日志产生

### 扫描后验证
- [ ] 扫描状态为 "completed"
- [ ] 数据库中有相应数据记录
- [ ] 发现的MOD数量合理
- [ ] 语言文件数量符合预期

### 故障恢复
- [ ] 清理冲突进程: `poetry run python main.py --kill-all`
- [ ] 重启服务: `poetry run python main.py`
- [ ] 重建数据库: 删除并重新初始化
- [ ] 切换扫描器: 根据硬件选择合适类型

---

通过系统化的性能测试和故障排除，您可以确保MC L10n扫描系统在各种环境下都能稳定高效地运行。