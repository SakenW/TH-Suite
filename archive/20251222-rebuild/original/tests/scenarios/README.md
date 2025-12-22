# 场景化测试框架使用指南

## 快速开始

### 1. 运行完整场景

```bash
# 进入项目根目录
cd TH-Suite

# 运行MC L10n基础场景
python tests/scenarios/shared/scripts/run_scenario.py tests/scenarios/mc-l10n-basic/manifest.yaml
```

### 2. 仅运行特定步骤

```bash
# 仅运行环境设置步骤
python tests/scenarios/shared/scripts/run_scenario.py tests/scenarios/mc-l10n-basic/manifest.yaml --step setup

# 仅运行扫描步骤
python tests/scenarios/shared/scripts/run_scenario.py tests/scenarios/mc-l10n-basic/manifest.yaml --step scan_project
```

### 3. 查看结果

场景运行完成后，结果保存在 `.artifacts/` 目录中：

```
.artifacts/
├── db/                  # 测试数据库
├── logs/                # 日志文件
│   └── scenario.log     # 场景执行日志
├── output/              # 输出产物
├── temp/                # 临时文件（自动清理）
├── results.json         # JSON格式结果报告
└── performance_*.json    # 性能指标
```

## 场景文件结构

```
tests/scenarios/
├── mc-l10n-basic/               # MC L10n基础场景
│   ├── manifest.yaml           # 场景定义文件
│   ├── README.md               # 场景说明
│   ├── inputs/                 # 测试输入数据
│   │   ├── mod_metadata.jsonl
│   │   ├── language_entries.jsonl
│   │   ├── translation_requests.jsonl
│   │   └── build_config.jsonl
│   └── scripts/                # 场景脚本
│       ├── setup.py
│       ├── import_data.py
│       ├── monitor_performance.py
│       └── ...
├── rw-l10n-basic/              # RW Studio基础场景
└── shared/                     # 共享脚本
    └── scripts/
        └── run_scenario.py     # 场景执行引擎
```

## 创建新场景

### 1. 创建场景目录

```bash
mkdir -p tests/scenarios/my-scenario/inputs tests/scenarios/my-scenario/scripts
```

### 2. 创建manifest.yaml

参考 `tests/scenarios/mc-l10n-basic/manifest.yaml` 的格式，定义你的场景步骤。

### 3. 准备测试数据

使用JSONL格式准备测试数据，每行一个JSON对象。

### 4. 实现步骤脚本

每个步骤可以是一个Python脚本或其他可执行命令。

## 最佳实践

1. **数据隔离**：每个场景使用独立的数据库schema和临时目录
2. **幂等性**：脚本应该可以重复运行而不会产生副作用
3. **错误处理**：脚本应该返回适当的退出码
4. **日志记录**：使用标准输出记录重要信息
5. **清理机制**：确保测试后清理所有临时资源

## 扩展场景

### 添加自定义断言

在manifest.yaml的assertions部分添加自定义验证：

```yaml
assertions:
  custom:
    - script: "scripts/verify_output.py"
      description: "验证输出格式"
```

### 添加性能监控

在步骤中集成性能监控：

```yaml
steps:
  - name: "性能测试"
    command: "python scripts/performance_test.py"
    after:
      - "python scripts/monitor_performance.py --step performance_test"
```

### 并行执行

场景执行引擎支持并行执行独立步骤：

```yaml
steps:
  - name: "任务1"
    id: "task1"
    parallel_group: "group1"
    
  - name: "任务2"
    id: "task2"
    parallel_group: "group1"
    
  - name: "汇总"
    id: "summary"
    depends_on: ["task1", "task2"]
```