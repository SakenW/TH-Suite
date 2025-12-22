# Trans-Hub 客户端开发与 API 集成指南

> **目标受众**: 开发上传/下载工具或将 Trans-Hub 集成到其他系统的客户端开发人员。
> **前置条件**: Python 3.10+, `httpx` 库。

## 1. 概述

Trans-Hub API 遵循 **整洁架构** 设计。集成关键点：
- **基础 URL**: `http://localhost:8000/api/v1` (开发环境)
- **认证方式**: Bearer Token (JWT)
- **数据格式**: 控制消息使用 JSON，大数据量（片段/术语）使用 **NDJSON + GZIP**。

## 2. 认证

Trans-Hub 使用 OAuth2 密码模式。你需要通过用户名/密码换取 `access_token`。

### Python 示例: 获取 Token
```python
import httpx

API_BASE = "http://localhost:8000/api/v1"

def login(email, password):
    with httpx.Client(base_url=API_BASE) as client:
        response = client.post("/auth/login/password", json={
            "username_or_email": email,
            "password": password
        })
        response.raise_for_status()
        data = response.json()
        return data["access_token"]

# 使用示例
token = login("admin@example.com", "secure_password")
headers = {"Authorization": f"Bearer {token}"}
```

## 3. 上传数据

为了上传大型数据集（例如数千个翻译片段），请使用 **流式导入** 接口。
**强制要求**: 内容必须是 GZip 压缩的 NDJSON (换行符分隔的 JSON)。

### 格式要求
- **格式**: NDJSON (`application/x-ndjson`)
- **编码**: GZIP (`Content-Encoding: gzip`)

### Python 示例: 流式上传
此示例通过流式压缩并上传数据，确保客户端内存占用极低。

```python
import gzip
import json
import httpx
import tempfile
import os

def stream_compress(data_iterator):
    """生成器：将字典迭代器转换为压缩的数据块"""
    # 简单且稳健的方法：写入临时文件并流式读取

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        with gzip.open(tmp.name, "wt", encoding="utf-8") as f:
            for record in data_iterator:
                f.write(json.dumps(record) + "\n")
        tmp_path = tmp.name

    # 流式读取文件内容
    with open(tmp_path, "rb") as f:
        yield from f

    os.remove(tmp_path)

def upload_segments(job_id, segments, token):
    """
    segments: 字典列表，例如 [{"external_id": "1", "content": "Hello"}]
    """
    endpoint = f"/jobs/{job_id}/segments/import"

    # 将生成器集成到 httpx
    def content_generator():
        yield from stream_compress(segments)

    response = httpx.post(
        f"{API_BASE}{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-ndjson",
            "Content-Encoding": "gzip"
        },
        content=content_generator(),
        timeout=60.0 # 大文件需增加超时时间
    )
    response.raise_for_status()
    print("上传成功:", response.json())

# 使用示例
data = [{"external_id": str(i), "content": f"片段 {i}"} for i in range(1000)]
# upload_segments("JOB_UUID_HERE", data, token)
```

## 4. 下载数据

要下载片段，使用导出接口。它返回 GZip 压缩的 NDJSON 流。

### Python 示例: 流式下载与解压
此示例接收流并逐行解压，适合处理超大响应。

```python
import zlib

def download_segments(job_id, token):
    endpoint = f"/jobs/{job_id}/segments/export"

    with httpx.Client(base_url=API_BASE) as client:
        #发起流式请求
        with client.stream("GET", endpoint, headers={"Authorization": f"Bearer {token}"}) as response:
            response.raise_for_status()

            # 创建 Gzip 解压对象 (自动检测头部)
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)

            buffer = ""
            for chunk in response.iter_bytes():
                data = d.decompress(chunk)
                if data:
                    buffer += data.decode("utf-8")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line:
                            yield json.loads(line)

# 使用示例
# for segment in download_segments("JOB_UUID_HERE", token):
#     print(segment)
```

## 5. 其他功能

### 任务状态查询
耗时操作（如导入）会返回 `task_id`。你需要轮询状态：

```python
def check_task(task_id, token):
    response = httpx.get(
        f"{API_BASE}/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()
```

### 完整工作流参考
1. **登录** -> 获取 Token。
2. **创建任务** (`POST /projects/{id}/jobs`) -> 获取 Job ID。
3. **上传片段** (流式 Gzip) -> 获取 Task ID。
4. **轮询状态** -> 等待状态变为 `completed`。
5. **预翻译** (`POST /jobs/{id}/actions/pre-translate`) -> 触发翻译。
6. **导出** (`GET /jobs/{id}/segments/export`) -> 下载结果。
