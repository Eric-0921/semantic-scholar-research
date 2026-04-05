# Semantic Scholar Research Automation

基于 Semantic Scholar API 的学术论文自动化研究工具集，专注于金刚石 NV 色心与量子传感领域。

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

## 快速开始

### 环境要求

- Python 3.8+
- Semantic Scholar API Key

### 安装

```bash
# 克隆项目
git clone https://github.com/Eric-4058/semantic-scholar-research.git
cd semantic-scholar-research

# 安装依赖
pip install requests python-dotenv

# 配置 API Key
cp .env.example .env
# 编辑 .env 文件，填入您的 API Key
```

### 获取 API Key

1. 访问 [Semantic Scholar API](https://www.semanticscholar.org/product/api)
2. 注册并获取免费 API Key
3. 将 Key 填入 `.env` 文件

### 使用示例

```bash
# 文献综述
python literature_review_pipeline.py "NV center quantum sensing"

# 论文追踪（生成日报）
python paper_tracker.py

# 引用网络分析
python citation_network.py "Quantum sensing with NV centers in diamond"

# 选刊建议
python venue_selector.py "Your paper abstract here" "Your paper title"

# 作者追踪
python author_tracker.py "Ronald Walschap" --days 30

# 个性化推荐
python personalized_recommender.py "NV center quantum magnetometry" --limit 20
```

## 项目结构

```
research_automation/
├── config.py                    # 配置（API Key、关键词、输出目录）
├── semantic_scholar_client.py   # Semantic Scholar API 客户端（核心库）
├── arxiv_client.py              # arXiv 搜索客户端
├── literature_review_pipeline.py # 场景一：文献综述自动化
├── citation_network.py          # 场景二：引用网络分析
├── paper_tracker.py             # 场景三：每日论文追踪
├── research_gap_finder.py       # 场景四：研究 Gap 挖掘
├── related_work_writer.py       # 场景五：Related Work 写作辅助
├── venue_selector.py            # 场景六：选刊助手
├── author_tracker.py            # 作者追踪
└── personalized_recommender.py  # 个性化推荐
```

## API 效率优化

本项目针对 Semantic Scholar API 速率限制（1 req/sec）进行了优化：

| 策略 | 说明 |
|------|------|
| 批量请求 | `search_papers_bulk()` 每次获取 1000 条 |
| 批量 Paper | `batch_get_papers()` 每次最多 500 篇 |
| 布尔查询 | 多关键词合并为一次搜索 |
| 指数退避 | 429 错误时自动重试 (1s → 2s → 4s → 8s → 16s) |
| 缓存机制 | 追踪已处理论文 ID，避免重复 |

## 配置说明

在 `config.py` 或 `.env` 文件中配置：

```python
# API Key
SEMANTIC_SCHOLAR_API_KEY = "your-api-key"

# 论文追踪关键词
WATCH_KEYWORDS = [
    "NV center", "nitrogen vacancy", "diamond quantum",
    "quantum sensing", "magnetometry", "spin defect"
]

# 追踪的作者
WATCH_AUTHORS = ["Author Name 1", "Author Name 2"]

# 输出目录
OUTPUT_DIR = "output/"
DAILY_REPORTS_DIR = "output/daily_reports/"
```

## 输出示例

### 论文追踪日报

```markdown
# 论文追踪日报 2024-01-15

**研究方向**: 金刚石NV色心 · 量子传感

共发现 12 篇相关论文（其中 3 篇具有高影响力引用）

---

## 1. Novel NV Center Magnetometer with Deep Learning
**作者**: Zhang et al. | **年份**: 2024 | **引用**: 45 🔥

> We demonstrate a novel quantum magnetometer...
---
```

### 选刊报告

```markdown
# 投稿选刊分析报告

| 排名 | 期刊/会议 | 匹配分数 | 级别 |
|------|-----------|----------|------|
| 1 | Nature Physics | 85/100 ⭐⭐⭐ | A* |
| 2 | PRX Quantum | 78/100 ⭐⭐⭐ | A* |
| 3 | Science Advances | 72/100 ⭐⭐⭐ | A* |
```

## 相关文档

- [Semantic Scholar API 文档](./docs/README.md)
- [API 速率限制与优化策略](./docs/API_OPTIMIZATION.md)

## 致谢

本项目受 [Semantic Scholar API](https://www.semanticscholar.org/product/api) 和 [Allen AI](https://allenai.org/) 支持。

## License

MIT License
