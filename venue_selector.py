"""
场景六：论文影响力分析与选刊助手 v2
分析目标期刊/会议特征，与用户研究方向匹配，给出选刊建议
使用 publicationVenue 对象进行精确匹配
"""
import re
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from semantic_scholar_client import SemanticScholarClient
from config import SEMANTIC_SCHOLAR_API_KEY, OUTPUT_DIR

# 期刊/会议配置（NV量子传感相关）
VENUE_PROFILES = {
    "Nature Physics": {
        "query_suffix": "Nature Physics quantum",
        "tier": "A*",
        "focus": "基础物理理论、原创性突破",
        "style": "注重物理原理的深度和原创性"
    },
    "Physical Review X": {
        "query_suffix": "Physical Review X quantum",
        "tier": "A*",
        "focus": "跨学科创新、量化分析",
        "style": "强调物理洞察和理论框架"
    },
    "Science Advances": {
        "query_suffix": "Science Advances quantum sensing",
        "tier": "A*",
        "focus": "广泛学科影响、突破性应用",
        "style": "注重科学影响力和社会意义"
    },
    "Nature Communications": {
        "query_suffix": "Nature Communications quantum sensing NV",
        "tier": "A*",
        "focus": "跨学科研究、创新性强",
        "style": "偏好综合性、高影响力工作"
    },
    "PRX Quantum": {
        "query_suffix": "PRX Quantum NV center",
        "tier": "A*",
        "focus": "量子信息、量子计算",
        "style": "专注量子领域，强调理论深度"
    },
    "Advanced Quantum Technologies": {
        "query_suffix": "Advanced Quantum Technologies magnetometry",
        "tier": "A",
        "focus": "量子技术应用、工程实现",
        "style": "偏重技术实现和实验验证"
    },
    "npj Quantum Information": {
        "query_suffix": "npj Quantum Information NV",
        "tier": "A",
        "focus": "量子信息科学",
        "style": "专注量子信息理论与实验"
    },
    "Physical Review Letters": {
        "query_suffix": "Physical Review Letters quantum sensing",
        "tier": "A*",
        "focus": "重要物理发现、快速传播",
        "style": "注重新颖性和快报性质"
    },
    "Nature Nanotechnology": {
        "query_suffix": "Nature Nanotechnology quantum sensing",
        "tier": "A*",
        "focus": "纳米技术与量子技术结合",
        "style": "偏好实验性、器件导向研究"
    },
    "Scientific Reports": {
        "query_suffix": "Scientific Reports",
        "tier": "B",
        "focus": "开放获取、多学科",
        "style": "开放发表，审稿周期较短",
        "alternate_names": ["Sci. Rep.", "Scientific Reports"]
    }
}


def match_venue_publication(venue_obj: dict, venue_name: str, profile: dict) -> bool:
    """判断论文是否发表于指定期刊/会议（使用 publicationVenue 精确匹配）"""
    if not venue_obj:
        return False

    pub_name = venue_obj.get("name", "")
    alt_names = venue_obj.get("alternate_names", [])
    profile_alts = profile.get("alternate_names", [])
    all_names = [pub_name] + alt_names + profile_alts

    return any(venue_name.lower() in name.lower() or name.lower() in venue_name.lower() for name in all_names if name)


def fetch_venue_papers(client: SemanticScholarClient, venue_name: str, user_topic: str, limit: int = 20) -> List[dict]:
    """搜索某期刊与用户主题相关的论文"""
    profile = VENUE_PROFILES.get(venue_name, {})
    query_suffix = profile.get("query_suffix", venue_name)
    query = f"{user_topic} {query_suffix}"

    try:
        papers = client.search_papers(
            query=query,
            limit=limit,
            fields="paperId,title,abstract,year,citationCount,influentialCitationCount,venue,publicationVenue,authors,tldr,fieldsOfStudy"
        )

        # 过滤确保属于目标期刊
        filtered = []
        for p in papers:
            venue_obj = p.get("publicationVenue", {})
            if match_venue_publication(venue_obj, venue_name, profile):
                filtered.append(p)

        return filtered
    except Exception as e:
        print(f"  搜索失败: {e}")
        return []


def analyze_venue_fit(user_paper: str, venue_name: str, venue_papers: List[dict]) -> dict:
    """分析论文与期刊的匹配度（基于规则简化版）"""

    profile = VENUE_PROFILES.get(venue_name, {})
    tier = profile.get("tier", "Unknown")
    focus = profile.get("focus", "")
    style = profile.get("style", "")

    # 计算匹配分数
    score = 50  # 基础分
    strengths = []
    weaknesses = []

    if not venue_papers:
        return {
            "venue": venue_name,
            "score": 0,
            "tier": tier,
            "focus": focus,
            "style": style,
            "strengths": ["未找到该期刊的相关论文"],
            "weaknesses": ["无法评估匹配度"],
            "suggestions": "请手动搜索该期刊近期论文进行评估"
        }

    # 分析 venue 论文的特征
    avg_citations = sum(p.get("citationCount", 0) for p in venue_papers) / len(venue_papers)
    avg_influential = sum(p.get("influentialCitationCount", 0) for p in venue_papers) / len(venue_papers)
    recent_count = sum(1 for p in venue_papers if p.get("year", 0) >= 2022)
    has_tldr_count = sum(1 for p in venue_papers if p.get("tldr"))

    # 收集领域分布
    from collections import Counter
    fields_count = Counter()
    for p in venue_papers:
        for f in p.get("fieldsOfStudy", []):
            fields_count[f] += 1

    # 用户论文关键词
    user_keywords = set(re.findall(r'\b\w{4,}\b', user_paper.lower()))

    # 检查匹配度
    matched_topics = 0
    for p in venue_papers[:5]:
        paper_text = f"{p.get('title', '')} {p.get('abstract', '')[:300]}".lower()
        paper_keywords = set(re.findall(r'\b\w{4,}\b', paper_text))
        overlap = len(user_keywords & paper_keywords)
        if overlap > 3:
            matched_topics += 1

    # 调整分数
    if matched_topics >= 3:
        score += 25
        strengths.append("研究主题与该期刊近期发表论文高度契合")
    elif matched_topics >= 1:
        score += 10
        strengths.append("研究主题与该期刊部分论文相关")

    if recent_count >= len(venue_papers) * 0.5:
        score += 10
        strengths.append("该期刊近期活跃度高，符合当前研究热点")

    if avg_citations > 50:
        score += 10
        strengths.append(f"该期刊论文平均引用较高({avg_citations:.0f})，影响力大")

    if avg_influential > 10:
        score += 5
        strengths.append(f"高影响力引用论文较多({avg_influential:.1f}篇/篇)")

    # 检查劣势
    if matched_topics == 0:
        score -= 20
        weaknesses.append("研究主题与该期刊近期偏好可能不完全匹配")

    if recent_count < len(venue_papers) * 0.3:
        weaknesses.append("该期刊近期相关论文较少，可能不是首选")

    # 确保分数在合理范围
    score = max(0, min(100, score))

    suggestions = []
    if score >= 75:
        suggestions.append("强烈推荐：该期刊非常适合您的工作")
    elif score >= 50:
        suggestions.append("建议考虑：根据论文定位，可作为候选期刊")
    elif score >= 30:
        suggestions.append("备选期刊：可作为保底选择")
    else:
        suggestions.append("不太推荐：该期刊与您的研究方向匹配度较低")

    if tier == "A*":
        suggestions.append("注意：A*期刊竞争激烈，建议同时准备其他候选")

    return {
        "venue": venue_name,
        "score": score,
        "tier": tier,
        "focus": focus,
        "style": style,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": " ".join(suggestions),
        "stats": {
            "papers_analyzed": len(venue_papers),
            "avg_citations": round(avg_citations, 1),
            "recent_papers": recent_count
        }
    }


def generate_venue_report(analyses: List[dict], user_paper_title: str) -> str:
    """生成选刊建议报告"""

    # 按分数排序
    sorted_venues = sorted(analyses, key=lambda x: x.get("score", 0), reverse=True)

    lines = []
    lines.append(f"# 投稿选刊分析报告\n\n")
    lines.append(f"**论文标题**: {user_paper_title}\n")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    lines.append("---\n\n")

    # 摘要
    lines.append("## 执行摘要\n\n")
    if sorted_venues:
        top = sorted_venues[0]
        lines.append(f"根据分析，**{top['venue']}** 是最佳匹配选择（匹配分数: {top['score']}/100）。\n\n")

    lines.append("## 期刊/会议匹配度排名\n\n")
    lines.append("| 排名 | 期刊/会议 | 匹配分数 | 级别 | 主要特点 |\n")
    lines.append("|------|-----------|----------|------|----------|\n")

    tier_emoji = {"A*": "⭐⭐⭐", "A": "⭐⭐", "B": "⭐", "Unknown": ""}

    for i, v in enumerate(sorted_venues, 1):
        score = v.get("score", 0)
        tier = v.get("tier", "Unknown")
        emoji = tier_emoji.get(tier, "")
        focus = v.get("focus", "")[:20]

        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        lines.append(f"| {i} | {v['venue']} | {score}/100 {bar} | {tier} {emoji} | {focus}... |\n")

    lines.append("\n## 详细分析\n\n")

    for v in sorted_venues[:6]:  # 只展示 Top 6
        score = v.get("score", 0)
        lines.append(f"### {v['venue']} （匹配分数: {score}/100）\n")
        lines.append(f"- **期刊级别**: {v.get('tier', 'Unknown')}\n")
        lines.append(f"- **主要特点**: {v.get('focus', 'Unknown')}\n")
        lines.append(f"- **风格偏好**: {v.get('style', 'Unknown')}\n\n")

        if v.get("strengths"):
            lines.append("**优势:**\n")
            for s in v["strengths"]:
                lines.append(f"- {s}\n")
            lines.append("\n")

        if v.get("weaknesses"):
            lines.append("**风险点:**\n")
            for w in v["weaknesses"]:
                lines.append(f"- {w}\n")
            lines.append("\n")

        if v.get("suggestions"):
            lines.append(f"**建议:** {v['suggestions']}\n")

        if v.get("stats"):
            stats = v["stats"]
            lines.append(f"\n**统计数据:** 分析了 {stats.get('papers_analyzed', 0)} 篇论文，")
            lines.append(f"平均引用 {stats.get('avg_citations', 0)}，")
            lines.append(f"近期论文 {stats.get('recent_papers', 0)} 篇\n")

        lines.append("\n---\n\n")

    # 建议
    lines.append("## 选刊建议\n\n")
    lines.append("### 推荐策略\n\n")

    top3 = sorted_venues[:3]
    if top3:
        lines.append("**首选:** ")
        lines.append(f"{top3[0]['venue']} (匹配度 {top3[0]['score']}%)\n\n")

        if len(top3) > 1:
            lines.append("**备选:** ")
            lines.append(", ".join([f"{v['venue']} ({v['score']}%)" for v in top3[1:3]]))
            lines.append("\n\n")

    lines.append("### 注意事项\n\n")
    lines.append("1. 选刊时应综合考虑论文创新性和期刊审稿周期\n")
    lines.append("2. A*期刊竞争激烈，建议预留充足时间准备\n")
    lines.append("3. 可以先投高目标期刊，根据审稿意见再调整\n")
    lines.append("4. 预印本（如 arXiv）可以同步发布，加快学术交流\n\n")

    lines.append("---\n")
    lines.append(f"*本报告由自动化工具生成，仅供参考。实际选刊决策请结合导师意见和最新期刊信息。*\n")

    return "".join(lines)


def run(user_paper_abstract: str, paper_title: str, target_venues: List[str] = None,
        user_topic: str = "", output_dir: str = None) -> str:
    """主流程"""
    client = SemanticScholarClient(SEMANTIC_SCHOLAR_API_KEY)

    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # 使用默认主题词
    if not user_topic:
        user_topic = user_paper_abstract[:100]

    # 使用指定的期刊或全部
    if target_venues:
        venues_to_analyze = {k: v for k, v in VENUE_PROFILES.items() if k in target_venues}
    else:
        venues_to_analyze = VENUE_PROFILES

    print(f"🔍 分析 {len(venues_to_analyze)} 个目标期刊/会议...")

    analyses = []
    for venue_name in venues_to_analyze.keys():
        print(f"\n📖 分析 {venue_name}...")

        # 搜索该期刊的论文
        venue_papers = fetch_venue_papers(client, venue_name, user_topic, limit=15)
        print(f"  找到 {len(venue_papers)} 篇相关论文")

        # 分析匹配度
        analysis = analyze_venue_fit(user_paper_abstract, venue_name, venue_papers)
        analyses.append(analysis)

        print(f"  匹配分数: {analysis['score']}/100")

        # 限速
        time.sleep(1)

    # 生成报告
    print("\n📝 生成选刊报告...")
    report = generate_venue_report(analyses, paper_title)

    # 保存报告
    output_path = output_dir / "venue_selection_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 报告已保存: {output_path}")

    # 保存 JSON 数据
    json_path = output_dir / "venue_selection_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "paper_title": paper_title,
            "user_abstract": user_paper_abstract[:200],
            "user_topic": user_topic,
            "analyzed_venues": len(analyses),
            "analyses": analyses,
            "timestamp": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ 数据已保存: {json_path}")

    # 打印 Top 3
    sorted_analyses = sorted(analyses, key=lambda x: x.get("score", 0), reverse=True)
    print("\n🏆 推荐 Top 3 投稿目标:")
    for i, v in enumerate(sorted_analyses[:3], 1):
        print(f"  {i}. {v['venue']} - 匹配分数 {v.get('score', 0)}/100")

    return str(output_path)


if __name__ == "__main__":
    import sys

    # 默认示例：NV量子传感论文
    example_abstract = """
    We demonstrate a novel room-temperature quantum magnetometer based on
    nitrogen-vacancy centers in diamond. By combining advanced microwave
    pulse sequences with machine learning-based noise cancellation, we
    achieve magnetic field sensitivity of 0.5 pT/Hz^1/2, representing a
    10-fold improvement over state-of-the-art commercial magnetometers.
    The technique is applied to biological imaging of neural activity
    with millisecond temporal resolution.
    """

    example_title = "NV Center Quantum Magnetometer with Deep Learning Noise Cancellation"

    # 从命令行参数读取
    if len(sys.argv) > 1:
        abstract = sys.argv[1]
        title = sys.argv[2] if len(sys.argv) > 2 else example_title
    else:
        abstract = example_abstract
        title = example_title

    # 可指定特定期刊
    target_venues = ["Nature Physics", "Physical Review X", "Science Advances",
                     "Nature Communications", "PRX Quantum"] if len(sys.argv) <= 1 else None

    run(
        user_paper_abstract=abstract,
        paper_title=title,
        target_venues=target_venues,
        user_topic="NV center quantum sensing magnetometry diamond"
    )