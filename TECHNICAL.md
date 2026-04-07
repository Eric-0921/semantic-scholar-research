# 技术文档 - 经验教训与技术路线

## 目录

1. [API 速率限制与应对策略](#1-api-速率限制与应对策略)
2. [批量搜索 vs 普通搜索](#2-批量搜索-vs-普通搜索)
3. [布尔查询优化](#3-布尔查询优化)
4. [指数退避重试机制](#4-指数退避重试机制)
5. [飞书 API vs lark-cli](#5-飞书-api-vs-lark-cli)
6. [缓存与去重策略](#6-缓存与去重策略)
7. [关键词策略](#7-关键词策略)
8. [踩坑记录](#8-踩坑记录)

---

## 1. API 速率限制与应对策略

### Semantic Scholar API 限制

| 账号类型 | 速率限制 | 日限额 |
|---------|---------|--------|
| 免费账号 | **1 req/sec** | 1000 req/day |
| 付费账号 | 10 req/sec | 10000 req/day |

### 应对策略

#### 策略一：减少 API 调用次数

```python
# ❌ 错误：每个关键词单独调用
for kw in KEYWORDS:  # 30+ 次 API 调用
    results = client.search_papers(kw, limit=20)
    time.sleep(1)  # 每次等待 1 秒

# ✅ 正确：合并为布尔查询
combined_query = " OR ".join(f'"{kw}"' for kw in KEYWORDS)
results = client.search_papers(combined_query, limit=100)  # 仅 1-2 次调用
```

#### 策略二：使用批量搜索

```python
# search_papers_bulk 每次最多返回 1000 条
results = client.search_papers_bulk(
    query="NV center OR quantum sensing",
    limit=500  # 500 条/次
)
```

#### 策略三：合理设置缓存

```python
CACHE_FILE = "output/tracker_cache.json"

# 加载已处理论文 ID
processed_ids = load_cache()
if pid in processed_ids:
    continue  # 跳过已处理的论文
```

---

## 2. 批量搜索 vs 普通搜索

| 方法 | API 端点 | 最大返回 | 适用场景 |
|-----|---------|---------|---------|
| `search_papers` | `/paper/search` | 100 条/次 | 精确搜索、需要排序 |
| `search_papers_bulk` | `/paper/search/bulk` | **1000 条/次** | 大规模检索、每日追踪 |

### 选择建议

- **每日追踪**: 使用 `search_papers_bulk`，减少 API 调用
- **精确查找**: 使用 `search_papers`，支持排序和过滤
- **引用网络**: 使用 `batch_get_papers`，批量获取论文详情

### 代码示例

```python
# 批量搜索 (每日追踪首选)
results = client.search_papers_bulk(
    query="NV center OR quantum sensing",
    limit=500,
    fields="paperId,title,abstract,year,citationCount"
)

# 普通搜索 (需要排序)
results = client.search_papers(
    query="NV center",
    limit=100,
    sort="citationCount",  # 按引用排序
    year_start=2020
)
```

---

## 3. 布尔查询优化

### 基础语法

```python
# OR: 匹配任一关键词
query = '"NV center" OR "quantum sensing"'

# AND: 同时匹配 (注意：需要引号包裹短语)
query = '"deep learning" AND "quantum"'

# 组合
query = '("NV center" OR "nitrogen-vacancy") AND ("magnetometry" OR "sensing")'
```

### 优化技巧

#### 3.1 关键词分组

```python
# ❌ 低效：所有关键词平铺
query = '"NV center" OR "quantum sensing" OR "diamond" OR "spin" ...'

# ✅ 高效：分组组合
core = '"NV center" OR "nitrogen-vacancy" OR "diamond quantum"'
application = '"magnetometry" OR "sensing" OR "NMR"'
query = f"({core}) AND ({application})"
```

#### 3.2 避免过于宽泛

```python
# ❌ 太宽泛：匹配噪音多
query = "quantum"

# ✅ 精确：限定领域
query = '"quantum sensing" OR "quantum magnetometry"'
```

#### 3.3 中文关键词处理

Semantic Scholar 对中文支持有限，建议使用英文或拼音：

```python
# ❌ 中文可能匹配不佳
WATCH_KEYWORDS = ["金刚石NV色心", "量子传感"]

# ✅ 英文 + 中文混合
WATCH_KEYWORDS = [
    "NV center", "nitrogen-vacancy", "quantum sensing",
    "金刚石NV色心",  # 部分支持
    "quantum sensing magnetometry",  # 推荐
]
```

---

## 4. 指数退避重试机制

### 实现代码

```python
import time

MAX_RETRIES = 5

def fetch_with_backoff(url, params):
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # 速率限制，等待后重试
                wait_time = 2 ** attempt  # 1, 2, 4, 8, 16 秒
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"API error {response.status_code}")
        except requests.exceptions.Timeout:
            time.sleep(2 ** attempt)
    raise Exception("Max retries exceeded")
```

### 等待时间表

| 重试次数 | 等待时间 |
|---------|---------|
| 1 | 1 秒 |
| 2 | 2 秒 |
| 3 | 4 秒 |
| 4 | 8 秒 |
| 5 | 16 秒 |

### 注意事项

1. **不要无限重试**: 设置最大重试次数避免死循环
2. **记录日志**: 方便排查问题
3. **考虑熔断**: 连续失败时触发告警

---

## 5. 飞书 API vs lark-cli

### 对比

| 方式 | 优点 | 缺点 |
|-----|------|------|
| **直接调用 API** | 灵活、可定制 | 需要处理 Token 刷新、权限问题 |
| **lark-cli** | 简单、Bot Token 不过期 | 功能有限、需要安装 |

### lark-cli 使用

```bash
# 安装
npm install -g @larksuite/cli

# 认证 (Bot 模式)
npx lark-cli auth login --domain docs,wiki --recommend

# 创建文档
npx lark-cli docs +create \
    --title "每日简报" \
    --markdown "# 内容" \
    --as bot \
    --wiki-space my_library

# 发送消息
npx lark-cli im +messages-send \
    --as bot \
    --user-id ou_xxx \
    --markdown "**消息内容**"
```

### Python 封装

```python
import subprocess
import json

def run_lark_cli(cmd):
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": "/home/linuxbrew/.linuxbrew/bin:" + os.environ.get("PATH", "")}
    )
    return json.loads(result.stdout)

# 使用
result = run_lark_cli([
    "npx", "lark-cli", "docs", "+create",
    "--title", "文档标题",
    "--markdown", "# 内容",
    "--as", "bot"
])

if result.get("ok"):
    print(result["data"]["doc_url"])
```

---

## 6. 缓存与去重策略

### 论文去重

```python
CACHE_FILE = "output/tracker_cache.json"

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            data = json.load(f)
            return set(data.get("processed_ids", []))
    return set()

def save_cache(processed_ids):
    with open(CACHE_FILE, "w") as f:
        json.dump({
            "processed_ids": list(processed_ids),
            "updated": datetime.now().isoformat()
        }, f)

# 使用
processed_ids = load_cache()
for paper in results:
    if paper["paperId"] not in processed_ids:
        process(paper)
        processed_ids.add(paper["paperId"])

save_cache(processed_ids)
```

### 缓存文件格式

```json
{
    "processed_ids": [
        "PaperId1",
        "PaperId2"
    ],
    "updated": "2024-01-15T08:00:00"
}
```

---

## 7. 关键词策略

### 分层关键词

```python
# 核心关键词 (高优先级，每次必搜)
CORE_KEYWORDS = [
    "NV center",
    "nitrogen-vacancy",
    "quantum sensing",
    "NV magnetometer",
    "diamond quantum",
    "ODMR",
]

# 扩展关键词 (补充搜索)
EXTENDED_KEYWORDS = [
    # 物理机制
    "spin qubit", "coherence", "decoherence", "Rabi oscillation",
    # 传感器件
    "magnetometry", "magnetic field sensing", "quantum magnetometer",
    # 应用领域
    "NMR", "MRI", "bioimaging", "temperature sensing",
    # 制备表征
    "ion implantation", "electron beam", "CVD diamond",
    # 前沿技术
    "quantum entanglement", "quantum error correction",
]
```

### 搜索策略

1. **每日追踪**: 只搜索 CORE_KEYWORDS，减少 API 调用
2. **每周综述**: CORE + 部分 EXTENDED
3. **按需分析**: 根据具体研究方向选择

---

## 8. 踩坑记录

### 坑 1: API Key 硬编码

**问题**: 代码中硬编码了 API Key，被推送到 GitHub

**解决**:
```python
# ❌ 错误
API_KEY = "your-key-here"

# ✅ 正确
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
```

**教训**: 所有密钥必须通过环境变量读取，`.env` 文件要加入 `.gitignore`

---

### 坑 2: 速率限制未处理

**问题**: 短时间内发起多个 API 请求，被限流后程序崩溃

**表现**:
```
Rate limited, waiting 1s...
Rate limited, waiting 2s...
Rate limited, waiting 4s...
Rate limited, waiting 8s...
Rate limited, waiting 16s...
Max retries exceeded
```

**解决**: 实现指数退避 + 批量搜索

**教训**: 免费 API 必须实现重试机制，且要考虑限流影响

---

### 坑 3: 飞书应用权限不足

**问题**: 直接调用飞书 API 创建文档返回 `No permission`

**原因**:
1. 应用没有添加 `docx` 权限
2. 个人版不支持 Wiki 创建

**解决**: 使用 `lark-cli --as bot` 方式

**教训**: 先用 CLI 测试权限，再写代码

---

### 坑 4: User Token 过期

**问题**: 使用飞书 User Token 调用 API，2 小时后失败

**表现**: `{"code": 99991663, "msg": "token expired"}`

**解决**: 使用 Bot Token (永不过期)

```bash
# User Token (会过期)
npx lark-cli auth login --domain docs,wiki

# Bot Token (不过期)
npx lark-cli auth login --domain docs,wiki --recommend
```

**教训**: 自动化任务必须使用 Bot Token

---

### 坑 5: Markdown 转飞书块格式错误

**问题**: 直接发送 Markdown 文本，格式错乱

**原因**: 飞书 post 消息需要特定的 JSON 格式

**解决**: 使用 `lark-cli --markdown` 自动转换

```python
# ❌ 错误：直接发送文本
send_message(text="# 标题\n内容")

# ✅ 正确：使用 lark-cli 的 markdown 参数
subprocess.run([
    "npx", "lark-cli", "im", "+messages-send",
    "--markdown", "# 标题\n内容"
])
```

**教训**: 飞书消息格式与 Markdown 不完全兼容，需要转换

---

### 坑 6: 代理环境变量

**问题**: cron 环境中 lark-cli 找不到

**原因**: cron 的 PATH 不包含 npm 全局 bin 目录

**解决**:
```python
full_env = os.environ.copy()
full_env["PATH"] = "/home/linuxbrew/.linuxbrew/bin:" + full_env["PATH"]
full_env["HTTP_PROXY"] = "http://127.0.0.1:7897"
full_env["HTTPS_PROXY"] = "http://127.0.0.1:7897"

subprocess.run(cmd, env=full_env)
```

**教训**: cron 任务需要完整的环境变量配置

---

## 附录：推荐的 API 调用模式

### 每日简报调用顺序

```
1. search_papers_bulk (1 次，获取论文列表)
   ↓
2. batch_get_papers (1 次，获取论文详情)
   ↓
3. create_wiki_node (1 次，创建飞书文档)
   ↓
4. send_daily_report_card (1 次，发送消息)
```

### 最小化 API 调用的代码示例

```python
# 每日简报完整流程
def daily_report():
    # 1 次 API 调用：批量搜索
    papers = client.search_papers_bulk(
        query=" OR ".join(f'"{kw}"' for kw in CORE_KEYWORDS),
        limit=100,
        fields="paperId,title,abstract,tldr,year,citationCount,influentialCitationCount"
    )

    # 本地处理：去重、排序、筛选
    papers = deduplicate(papers)
    papers = filter_by_date(papers, days=7)
    papers = sort_by_influence(papers)

    # 2 次 lark-cli 调用：文档 + 消息
    doc_url = create_feishu_doc("每日简报", render_markdown(papers))
    send_card(doc_url, len(papers))
```

---

*最后更新: 2026-04-07*
