"""
Config for NV Center & Quantum Sensing Academic Research Automation
研究领域：金刚石NV色心 / 量子传感
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
ENV_FILE = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_FILE)

# Semantic Scholar API Key
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

# 研究方向配置
MY_RESEARCH_FOCUS = """
主要研究金刚石NV色心量子传感技术，包括：
- NV色心制备与表征
- 量子精密测量与磁力计
- 量子纠缠与量子信息处理
- 室温量子传感应用
"""

# 追踪关键词（NV色心 + 量子传感）- 中英文混合
WATCH_KEYWORDS = [
    # 核心概念
    "NV center", "nitrogen-vacancy", "金刚石NV色心", "NV色心",
    "quantum sensing", "量子传感", "量子精密测量",
    "diamond quantum", "金刚石量子",

    # 物理机制
    "spin qubit", "自旋量子比特", "solid-state spin", "固态自旋",
    "coherence", "相干性", "decoherence", "退相干",
    "ODMR", "光检测磁共振", "Rabi oscillation", "拉比振荡",
    "hyperfine coupling", "超精细耦合", "Zeeman", "塞曼效应",

    # 传感器件
    "NV magnetometer", "NV磁力计", "magnetometry", "磁力测量",
    "quantum magnetometer", "量子磁力计", "magnetic field sensing",

    # 应用领域
    "NMR", "MRI", "核磁共振", "bioimaging", "生物成像",
    "temperature sensing", "温度传感", "electric field sensing",

    # 制备与表征
    "ion implantation", "离子注入", "electron beam", "电子束",
    "CVD diamond", "CVD金刚石", "diamond fabrication",

    # 前沿技术
    "quantum entanglement", "量子纠缠", "quantum error correction",
    "deep learning quantum", "machine learning NV",
]

# 核心关键词（高优先级，每次必搜）
CORE_KEYWORDS = [
    "NV center", "nitrogen-vacancy", "quantum sensing",
    "NV magnetometer", "diamond quantum", "ODMR",
]

# 追踪特定作者（可添加）
WATCH_AUTHORS = [
    # TODO: 添加你感兴趣的作者名字
]

# 输出目录
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DAILY_REPORTS_DIR = BASE_DIR / "daily_reports"
WEEKLY_REPORTS_DIR = BASE_DIR / "weekly_reports"

# 确保目录存在
OUTPUT_DIR.mkdir(exist_ok=True)
DAILY_REPORTS_DIR.mkdir(exist_ok=True)
WEEKLY_REPORTS_DIR.mkdir(exist_ok=True)

# API 配置
S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_HEADERS = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}

# 搜索配置
RELEVANCE_THRESHOLD = 6  # 0-10，低于此分数不收录
MAX_PAPERS_PER_KEYWORD = 20
DAYS_BACK = 1  # 每日运行设1，每周运行设7

# arXiv API
ARXIV_API = "http://export.arxiv.org/api/query"