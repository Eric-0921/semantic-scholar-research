# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.0] - 2026-04-07

### Changed

- **关键词库扩展**: 从 6 个扩展到 30+ 个中英文混合关键词
  - 核心概念: NV center, nitrogen-vacancy, 量子传感, 金刚石量子
  - 物理机制: spin qubit, 相干性, ODMR, Rabi oscillation, 超精细耦合
  - 传感器件: NV磁力计, magnetometry, quantum magnetometer
  - 应用领域: NMR, MRI, 生物成像, 温度传感
  - 制备表征: 离子注入, 电子束, CVD金刚石
  - 前沿技术: 量子纠缠, 量子纠错, 深度学习量子

- **CORE_KEYWORDS**: 新增核心关键词配置，优先搜索高相关度论文
- **paper_tracker.py**: 双层搜索策略（核心关键词 + 扩展关键词）

## [1.0.0] - 2026-04-05

### Added

- **语义 scholar 客户端**: `semantic_scholar_client.py`
  - 支持 Paper Data API、Author API、Snippet API、Academic Graph API、Recommendations API
  - 指数退避重试机制（1s → 2s → 4s → 8s → 16s）
  - 批量请求支持（500 papers/batch, 1000 results/bulk search）

- **场景一 - 文献综述自动化**: `literature_review_pipeline.py`
  - 多查询扩展搜索
  - 高引用/TLDR 论文筛选
  - Markdown 格式综述生成

- **场景二 - 引用网络分析**: `citation_network.py`
  - BFS 递归构建引用图
  - 加权 PageRank 计算
  - Gephi 格式导出 (.gexf)
  - `isInfluential` 高影响力引用标记

- **场景三 - 每日论文追踪**: `paper_tracker.py`
  - 多关键词布尔合并搜索
  - 作者追踪支持 (`WATCH_AUTHORS`)
  - arXiv 同步搜索
  - 论文缓存去重
  - 中文摘要生成
  - 每日/每周报告

- **场景四 - 研究 Gap 挖掘**: `research_gap_finder.py`
  - PDF Future Work 章节提取
  - 摘要局限性推断
  - 关键词聚类分析

- **场景五 - Related Work 写作辅助**: `related_work_writer.py`
  - 论文草稿关键词提取
  - 多类别自动分类（Direct Comparisons, Method Inspirations, Background, Same Principle）
  - BibTeX 引用生成

- **场景六 - 选刊助手**: `venue_selector.py`
  - `publicationVenue` 对象精确匹配
  - 期刊 profile 配置（Nature Physics, PRX, Science Advances 等）
  - 匹配分数计算

- **作者追踪**: `author_tracker.py`
  - 作者搜索与 ID 解析
  - 近期论文时间过滤
  - 缓存机制避免重复

- **个性化推荐**: `personalized_recommender.py`
  - Recommendations API 集成
  - 种子论文正负例支持
  - 多维度过滤（时间、引用、领域）

### API 字段增强

所有脚本均支持以下增强字段：
- `influentialCitationCount` - 高影响力引用数
- `fieldsOfStudy` - 论文领域分类
- `externalIds` - 跨数据库交叉验证（DOI, arXiv, MAG 等）
- `embedding.specter_v2` - 语义相似度计算

## [0.1.0] - 2024-01-10

### Added

- 初始项目结构
- 基础 Semantic Scholar API 集成
- 初步的论文搜索功能
