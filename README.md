# Semantic Scholar Research Automation

基于 Semantic Scholar API 的学术论文自动化研究工具集，专注于**金刚石 NV 色心**与**量子传感**领域。支持每日自动追踪最新论文并推送至飞书。

## 功能概览

| 场景 | 脚本 | 说明 |
|------|------|------|
| 文献综述 | `literature_review_pipeline.py` | 输入关键词，自动检索、筛选论文，生成结构化综述草稿 |
| 引用网络 | `citation_network.py` | 从种子论文出发，递归展开引用网络，识别核心论文 |
| 论文追踪 | `paper_tracker.py` | 每日/每周自动监控新论文，生成中文摘要日报 |
| 研究 Gap | `research_gap_finder.py` | 分析领域"已解决"和"未解决"问题，挖掘研究空白 |
| Related Work | `related_work_writer.py` | 给定论文草稿，自动检索相关文献，生成 Related Work 段落 |
| 选刊助手 | `venue_selector.py` | 分析目标期刊特征，与研究方向匹配，给出选刊建议 |
| 作者追踪 | `author_tracker.py` | 追踪特定作者的新发表论文 |
| 个性化推荐 | `personalized_recommender.py` | 基于种子论文获取个性化推荐 |
| 每日简报 | `daily_report.py` | **整合以上功能，每日生成飞书文档+消息推送** |

## 快速开始

### 1. 环境要求

- Python 3.8+
- Node.js 16+ (用于 lark-cli)
- Git

### 2. 克隆项目

```bash
git clone https://github.com/Eric-4058/semantic-scholar-research.git
cd semantic-scholar-research
```

### 3. 安装依赖

```bash
# Python 依赖
pip install requests python-dotenv

# 安装 lark-cli (飞书 CLI 工具)
npm install -g @larksuite/cli

# 认证 lark-cli (使用 Bot 模式，Token 永不过期)
npx lark-cli auth login --domain docs,wiki --recommend
```

### 4. 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的凭证
nano .env
```

### 5. 运行

```bash
# 每日简报 (推荐)
python daily_report.py

# 指定天数
python daily_report.py --days 7

# 仅本地生成，不推送飞书
python daily_report.py --dry-run
```

## 配置说明

### .env 文件

```ini
# Semantic Scholar API Key (必需)
# 申请地址: https://www.semanticscholar.org/product/api
# 免费账号: 1 req/sec
SEMANTIC_SCHOLAR_API_KEY=your-key-here

# 飞书应用凭证 (用于文档创建和消息推送)
# 创建应用: https://open.feishu.cn/app
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
```

### config.py 关键配置

```python
# 核心关键词 (优先搜索，高相关度)
CORE_KEYWORDS = [
    "NV center", "nitrogen-vacancy", "quantum sensing",
    "NV magnetometer", "diamond quantum", "ODMR",
]

# 扩展关键词 (补充搜索，广覆盖)
WATCH_KEYWORDS = [
    # 核心概念、物理机制、传感器件、应用领域、制备表征、前沿技术
    "NV center", "nitrogen-vacancy", "金刚石NV色心", ...
]

# 追踪的作者 (可选)
WATCH_AUTHORS = ["Author Name 1", "Author Name 2"]

# 输出目录
OUTPUT_DIR = "output/"
```

## 项目结构

```
semantic-scholar-research/
├── config.py                    # 全局配置
├── semantic_scholar_client.py   # Semantic Scholar API 客户端 ⭐核心
├── arxiv_client.py              # arXiv 搜索客户端
├── feishu_publisher.py          # 飞书文档与消息推送 (lark-cli)
├── paper_tracker.py             # 论文追踪
├── citation_network.py           # 引用网络分析
├── literature_review_pipeline.py # 文献综述生成
├── research_gap_finder.py       # 研究 Gap 挖掘
├── related_work_writer.py        # Related Work 写作辅助
├── venue_selector.py            # 选刊助手
├── author_tracker.py            # 作者追踪
├── personalized_recommender.py  # 个性化推荐
├── daily_report.py              # 每日简报 (整合以上功能)
├── setup_cron.sh               # Cron 定时任务设置
├── .env.example                # 环境变量模板
├── .gitignore                 # Git 忽略规则
├── requirements.txt            # Python 依赖
├── README.md                  # 本文档
└── TECHNICAL.md               # 技术文档
```

## 技术文档

详见 [TECHNICAL.md](./TECHNICAL.md)，包含：

- API 速率限制与应对策略
- 批量搜索 vs 普通搜索的选择
- 布尔查询优化
- 指数退避重试机制
- 飞书 API vs lark-cli 对比
- 缓存与去重策略

## 每日定时任务

### 设置 Cron

```bash
# 编辑 crontab
crontab -e

# 添加定时任务 (每天早上 8:00 运行)
0 8 * * * cd /path/to/semantic-scholar-research && python3 daily_report.py >> logs/daily_report.log 2>&1
```

### 查看日志

```bash
tail -f logs/daily_report.log
```

## 常见问题

### Q: API 返回 "Max retries exceeded"

**原因**: 触发了 Semantic Scholar 的速率限制 (免费账号 1 req/sec)

**解决**:
1. 等待 1-2 分钟后再试
2. 减少搜索关键词数量
3. 使用批量搜索而非多次单独搜索

### Q: 飞书文档创建失败 "permission denied"

**原因**: 应用缺少文档权限

**解决**: 在 [飞书开放平台](https://open.feishu.cn/app) 给应用添加以下权限：
- `docx` (云文档)
- `im:message:send_as_bot` (发送消息)

### Q: lark-cli 命令找不到

**解决**: 确保 PATH 包含 npm 全局 bin 目录：
```bash
export PATH="$(npm root -g)/bin:$PATH"
```

## 输出示例

### 飞书消息卡片

```
📚 每日科研简报 2024-01-15

研究方向: 金刚石NV色心 · 量子传感

---
今日新论文: 12 篇
高影响力: 3 篇 🔥

📖 点击查看完整报告
```

### 飞书文档内容

- 统计概览 (论文总数、高影响力数量)
- 高影响力论文列表
- 最新论文列表 (含 TLDR/摘要)
- 作者追踪
- 搜索关键词记录

## 相关文档

- [Semantic Scholar API 文档](https://www.semanticscholar.org/product/api)
- [lark-cli 文档](https://open.feishu.cn/document/tools-and-clis/clis/readme)
- [飞书开放平台](https://open.feishu.cn/)

## License

MIT License
