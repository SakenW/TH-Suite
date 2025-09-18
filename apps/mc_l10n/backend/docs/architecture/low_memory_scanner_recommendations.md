# 低内存扫描解决方案研究报告

## 🎯 问题分析

针对"扫描整合包会非常卡，配置低的电脑怎么办"的问题，主要内存瓶颈：

1. **一次性加载**：将所有发现的文件路径存储在内存中
2. **JAR内容缓存**：将每个JAR的语言文件内容全部加载到内存
3. **并发内存放大**：8个并发JAR同时解压，内存使用成倍增长
4. **对象积累**：扫描结果在内存中累积，不及时释放

## 📚 现成库调研

### 1. 内存优化的ZIP处理库

#### `zipfile36` (Python 3.6+ 优化版)
- 支持流式读取
- 内存使用更高效
- 兼容标准zipfile API

#### `py7zr` (7-Zip format)
- 支持大文件流式处理
- 内存占用小
- 但主要针对7z格式

#### `zipstream-ng` (流式ZIP创建/读取)
```python
# 流式读取，内存占用恒定
import zipstream
stream = zipstream.ZipStream.from_path('large.zip')
for chunk in stream:
    process_chunk(chunk)
```

### 2. 大文件处理最佳实践库

#### `mmap` (内存映射文件)
```python
import mmap
with open('large.jar', 'r+b') as f:
    mm = mmap.mmap(f.fileno(), 0)
    # 文件内容映射到虚拟内存，按需加载
```

#### `ijson` (流式JSON解析)
```python
import ijson
# 对于大的语言文件JSON，流式解析
parser = ijson.parse(file_stream)
for prefix, event, value in parser:
    if event == 'string':
        process_translation_key(value)
```

#### `psutil` (内存监控)
```python
import psutil
# 实时监控内存使用，动态调整策略
```

## 🚀 推荐的低内存扫描架构

### 核心设计原则

1. **流式处理**：Never load entire file contents into memory
2. **分批处理**：Process files in small batches (2-5 JAR files)
3. **内存阈值**：Monitor memory usage and trigger GC/backpressure
4. **延迟加载**：Only load file contents when actually needed
5. **增量释放**：Immediately release processed data

### 架构方案对比

| 方案 | 内存使用 | 处理速度 | 实现难度 | 推荐指数 |
|------|----------|----------|----------|----------|
| **流式扫描器** | 50-100MB | 中等 | 低 | ⭐⭐⭐⭐⭐ |
| **分批处理器** | 100-200MB | 快 | 中 | ⭐⭐⭐⭐ |
| **内存映射** | 20-50MB | 快 | 高 | ⭐⭐⭐ |
| **外部工具调用** | 极低 | 慢 | 低 | ⭐⭐ |

## 💡 具体实现建议

### 方案1: 流式扫描器 (推荐)

```python
class LowMemoryScanner:
    def __init__(self, memory_limit_mb=256):
        self.memory_limit = memory_limit_mb
        
    def scan_jar_streaming(self, jar_path):
        """流式扫描，内存使用恒定"""
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # 1. 只读取文件列表(轻量)
            filenames = jar.namelist()
            
            # 2. 检查MOD特征(不解压)
            if not self._is_mod_quick_check(filenames):
                return
                
            # 3. 流式读取元数据(单个小文件)
            metadata = self._extract_metadata_streaming(jar)
            
            # 4. 流式处理语言文件(逐个处理，立即释放)
            for lang_result in self._process_languages_streaming(jar):
                yield {**metadata, **lang_result}
                
    def _process_languages_streaming(self, jar):
        """逐个处理语言文件，不积累在内存"""
        for filename in jar.namelist():
            if '/lang/' in filename and filename.endswith('.json'):
                with jar.open(filename) as f:
                    # 限制读取大小
                    content = f.read(512 * 1024)  # 最多512KB
                    try:
                        data = json.loads(content)
                        yield {
                            'language': Path(filename).stem,
                            'key_count': len(data),
                            'sample_keys': list(data.keys())[:5]
                            # 不保存完整data，立即释放
                        }
                    finally:
                        del content, data  # 显式释放
```

### 方案2: 内存阈值控制

```python
class MemoryAwareScanner:
    def __init__(self, memory_limit_mb=512):
        self.memory_limit = memory_limit_mb
        self.batch_size = 3  # 动态调整
        
    def scan_with_memory_control(self, jar_files):
        """根据内存使用动态调整处理策略"""
        for i in range(0, len(jar_files), self.batch_size):
            batch = jar_files[i:i + self.batch_size]
            
            # 处理前检查内存
            if self._get_memory_usage() > self.memory_limit * 0.8:
                self._emergency_cleanup()
                self.batch_size = max(1, self.batch_size - 1)
            
            # 处理批次
            for result in self._process_batch(batch):
                yield result
                
            # 处理后清理
            gc.collect()
            
    def _emergency_cleanup(self):
        """紧急内存清理"""
        gc.collect()
        # 可以考虑清理缓存等
```

### 方案3: 外部工具辅助

```python
class ExternalToolScanner:
    """使用外部工具辅助，极低内存使用"""
    
    def scan_with_external_tools(self, jar_path):
        """使用系统工具预处理"""
        # 使用unzip -l列出文件，不解压
        result = subprocess.run(['unzip', '-l', str(jar_path)], 
                              capture_output=True, text=True)
        
        if self._contains_mod_files(result.stdout):
            # 只解压需要的文件
            subprocess.run(['unzip', '-j', str(jar_path), 
                          'fabric.mod.json', '-d', '/tmp/'])
            
            # 处理元数据
            metadata = self._parse_metadata('/tmp/fabric.mod.json')
            
            # 清理临时文件
            os.remove('/tmp/fabric.mod.json')
            
            return metadata
```

## 🎛️ 配置建议

### 低配置电脑 (4GB内存)
```json
{
  "memory_limit_mb": 256,
  "batch_size": 2,
  "max_concurrent_jars": 1,
  "enable_streaming": true,
  "max_language_file_size_kb": 256,
  "emergency_gc_threshold": 0.8
}
```

### 中等配置 (8GB内存)
```json
{
  "memory_limit_mb": 512,
  "batch_size": 4,
  "max_concurrent_jars": 3,
  "enable_streaming": true,
  "max_language_file_size_kb": 512,
  "emergency_gc_threshold": 0.7
}
```

### 高配置 (16GB+ 内存)
```json
{
  "memory_limit_mb": 1024,
  "batch_size": 8,
  "max_concurrent_jars": 8,
  "enable_streaming": false,
  "max_language_file_size_kb": 1024,
  "emergency_gc_threshold": 0.6
}
```

## 📊 性能对比预期

| 配置 | 原始扫描器 | 流式扫描器 | 内存节省 | 速度变化 |
|------|------------|------------|----------|----------|
| 4GB内存 | 经常OOM | 稳定运行 | 70-80% | -20% |
| 8GB内存 | 800MB+ | 200-300MB | 60-70% | -10% |
| 16GB内存 | 1.5GB+ | 300-500MB | 70% | 持平 |

## 🔧 实现优先级

1. **立即实现** - 流式扫描器 (2-3小时)
2. **短期实现** - 内存监控和阈值控制 (1天)
3. **中期实现** - 动态配置和自适应 (2-3天) 
4. **长期实现** - 外部工具集成 (1周)

## 📝 总结

**推荐方案**: 流式扫描器 + 内存阈值控制

- **优点**: 内存使用稳定、兼容性好、实现简单
- **缺点**: 速度略慢(10-20%)，但内存安全性大幅提升
- **适用**: 所有配置的电脑，特别是4-8GB内存的设备

这个方案可以确保即使在低配置电脑上也能稳定运行，避免因内存不足导致的系统卡顿或崩溃。