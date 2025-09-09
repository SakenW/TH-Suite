# 后端目录结构

## 目录说明

```
backend/
├── core/               # 核心业务逻辑
│   ├── mc_database.py  # 统一数据库实现（v5.0规范）
│   └── ddd_scanner.py  # MOD扫描和语言文件提取
│
├── utils/              # 工具函数
│   └── simple_logging.py # 结构化日志工厂
│
├── scripts/            # 独立脚本和工具
│   ├── cleanup_duplicates.py # 重复数据清理工具
│   └── verify_full_data.py   # 数据验证工具
│
├── data/               # 数据文件
│   ├── *.db            # SQLite数据库文件
│   └── *.json          # JSON数据文件
│
├── archive/            # 归档的旧代码
│   ├── database_old/   # 旧的数据库实现
│   └── *.py            # 临时和废弃的文件
│
├── api/                # API相关（FastAPI路由等）
├── src/                # 旧的源代码目录（待迁移）
├── tests/              # 测试文件
└── main.py             # 主应用程序入口

## 关键文件

### main.py
FastAPI应用主入口，提供以下功能：
- REST API端点
- WebSocket实时通信
- 扫描进度跟踪
- 数据库管理

### core/mc_database.py
生产级数据库实现：
- 单例模式管理
- 连接池支持
- WAL模式优化
- 完整的v5.0数据库规范
- 10个核心表 + 20个索引 + 4个视图

### core/ddd_scanner.py
扫描服务实现：
- JAR文件解析
- 语言文件提取
- 异步扫描支持
- 进度报告

## 导入示例

```python
# 从main.py导入
from core.mc_database import Database
from core.ddd_scanner import get_scanner_instance
from utils.simple_logging import StructLogFactory

# 从其他模块导入
from ..core.mc_database import Database
from ..utils.simple_logging import StructLogFactory
```

## 数据库规范

当前使用v5.0数据库规范，包含以下表：
- projects（项目管理）
- mods（MOD信息）
- language_files（语言文件）
- translation_entries（翻译条目）
- scan_cache（扫描缓存）
- glossary（术语表）
- work_queue（工作队列）
- scan_progress（扫描进度）
- sync_log（同步日志）
- mod_metadata（MOD元数据）

## 注意事项

1. 所有新代码应放入相应的目录（core/、utils/、scripts/）
2. 避免在根目录创建新的Python文件
3. 数据文件应放在data/目录
4. 废弃代码移至archive/目录
5. 使用相对导入处理模块间依赖