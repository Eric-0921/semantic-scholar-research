"""
场景三：每日/每周论文追踪系统 v2
自动监控NV色心 + 量子传感新论文，生成中文摘要
支持：关键词搜索 + 作者追踪 + 指数退避重试
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set
from semantic_scholar_client import SemanticScholarClient
from arxiv_client import search_arxiv
from config import (
    SEMANTIC_SCHOLAR_API_KEY, WATCH_KEYWORDS, CORE_KEYWORDS, WATCH_AUTHORS,
    OUTPUT_DIR, DAILY_REPORTS_DIR, RELEVANCE_THRESHOLD,
    DAYS_BACK, MAX_PAPERS_PER_KEYWORD, MY_RESEARCH_FOCUS
)

CACHE_FILE = OUTPUT_DIR / "tracker_cache.json"

def load_cache() -> set:
    """加载已处理论文 ID 缓存"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return set(json.load(f).get("processed_ids", []))
    return set()

def save_cache(processed_ids: set):
    """保存缓存"""
    with open(CACHE_FILE, "w") as f:
        json.dump({"processed_ids": list(processed_ids), "updated": datetime.now().isoformat()}, f)

def fetch_recent_papers(client: SemanticScholarClient, keywords: List[str], days_back: int) -> list[dict]:
    """用布尔查询合并关键词，一次获取结果"""
    # 合并关键词为布尔查询
    keyword_query = " OR ".join(f'"{kw}"' for kw in keywords)
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    print(f"  🔎 S2检索: {len(keywords)} 个关键词...")
    papers = client.search_papers(
        query=keyword_query,
        limit=MAX_PAPERS_PER_KEYWORD * 2,  # 多取一些，因为去重后会减少
        fields="paperId,title,abstract,tldr,year,citationCount,influentialCitationCount,authors,publicationDate,openAccessPdf,externalIds,fieldsOfStudy",
        year_start=int(date_from[:4])
    )
    return papers

def fetch_author_papers(client: SemanticScholarClient, author_names: List[str], days_back: int) -> list[dict]:
    """追踪特定作者的新论文"""
    all_author_papers = []

    for author_name in author_names:
        if not author_name.strip():
            continue

        print(f"  🔍 搜索作者: {author_name}")
        try:
            # 1. 搜索作者 ID
            authors = client.search_authors(author_name, limit=5)
            if not authors:
                print(f"    未找到作者: {author_name}")
                continue

            # 取第一个匹配结果
            author = authors[0]
            author_id = author.get("authorId")
            print(f"    找到作者: {author.get('name')} (ID: {author_id})")

            # 2. 获取该作者近期论文
            date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            papers = client.get_author_papers(
                author_id,
                limit=20,
                year_start=int(date_from[:4])
            )

            # 3. 过滤日期
            for p in papers:
                pub_date = p.get("year", 0)
                if pub_date and pub_date >= datetime.now().year - (1 if days_back > 365 else 0):
                    all_author_papers.append(p)

            time.sleep(1)  # 遵守速率限制

        except Exception as e:
            print(f"    ⚠️ 搜索作者失败: {e}")

    return all_author_papers

def generate_chinese_summary(papers: list[dict], research_focus: str) -> list[dict]:
    """生成中文摘要（使用 TLDR 或截取摘要）"""
    for p in papers:
        tldr = p.get("tldr", {})
        tldr_text = tldr.get("text", "") if isinstance(tldr, dict) else ""
        if tldr_text:
            p["claude_summary"] = tldr_text
        else:
            abstract = p.get("abstract", "")[:200]
            p["claude_summary"] = f"{abstract}..."
    return papers

def generate_daily_report(all_papers: list[dict], date_str: str) -> str:
    """生成日报 Markdown"""
    papers = sorted(all_papers, key=lambda x: x.get("citationCount", 0), reverse=True)

    # 分类统计
    from collections import Counter
    fields_count = Counter()
    for p in papers:
        for f in p.get("fieldsOfStudy", []):
            fields_count[f] += 1

    lines = [f"# 论文追踪日报 {date_str}\n"]
    lines.append(f"**研究方向**: 金刚石NV色心 · 量子传感\n\n")
    lines.append(f"共发现 **{len(papers)}** 篇相关论文\n")

    # 高影响力论文标记
    high_impact = [p for p in papers if p.get("influentialCitationCount", 0) > 5]
    if high_impact:
        lines.append(f"（其中 **{len(high_impact)}** 篇具有高影响力引用）\n")

    # 领域分布
    if fields_count:
        lines.append(f"\n**领域分布**: {', '.join(f'{k}({v})' for k, v in fields_count.most_common(3))}\n")

    lines.append("\n---\n\n")

    for i, p in enumerate(papers, 1):
        citations = p.get("citationCount", 0)
        influential = p.get("influentialCitationCount", 0)
        stars = "⭐" * min(citations // 10, 5)
        impact_marker = " 🔥" if influential > 5 else ""

        authors = ", ".join([a.get("name", "") for a in p.get("authors", [])[:3]])
        if len(p.get("authors", [])) > 3:
            authors += " et al."

        paper_id = p.get("paperId", "")
        s2_link = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""

        pdf_link = ""
        if p.get("openAccessPdf"):
            pdf_url = p.get("openAccessPdf", {}).get("url", "")
            if pdf_url:
                pdf_link = f" [[PDF]]({pdf_url})"

        lines.append(f"## {i}. {p.get('title', 'N/A')}\n")
        lines.append(f"**作者**: {authors} | **年份**: {p.get('year', 'N/A')} | **引用**: {citations}{impact_marker}\n")
        if s2_link:
            lines.append(f"**链接**: [[Semantic Scholar]]({s2_link}){pdf_link}\n")

        summary = p.get("claude_summary", p.get("abstract", "")[:200])
        lines.append(f"\n> {summary}\n\n")
        lines.append("---\n\n")

    return "".join(lines)

def run_daily_tracker():
    """每日追踪主流程"""
    print(f"🔍 开始论文追踪 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

    client = SemanticScholarClient(SEMANTIC_SCHOLAR_API_KEY)
    processed_ids = load_cache()
    today = datetime.now().strftime("%Y-%m-%d")

    all_new_papers = {}

    # 1. Semantic Scholar 核心关键词搜索（高优先级）
    papers = fetch_recent_papers(client, CORE_KEYWORDS, DAYS_BACK)
    for p in papers:
        pid = p.get("paperId")
        if pid and pid not in processed_ids and pid not in all_new_papers:
            all_new_papers[pid] = p

    # 2. Semantic Scholar 扩展关键词搜索（补充）
    papers = fetch_recent_papers(client, WATCH_KEYWORDS, DAYS_BACK)
    for p in papers:
        pid = p.get("paperId")
        if pid and pid not in processed_ids and pid not in all_new_papers:
            all_new_papers[pid] = p

    # 4. 作者追踪
    if WATCH_AUTHORS:
        author_papers = fetch_author_papers(client, WATCH_AUTHORS, DAYS_BACK)
        for p in author_papers:
            pid = p.get("paperId")
            if pid and pid not in processed_ids and pid not in all_new_papers:
                all_new_papers[pid] = p

    # 5. arXiv 搜索
    for keyword in WATCH_KEYWORDS:
        print(f"  🔎 arXiv检索: {keyword}")
        try:
            arxiv_papers = search_arxiv(keyword, MAX_PAPERS_PER_KEYWORD, DAYS_BACK)
            for p in arxiv_papers:
                aid = p.get("arxiv_id")
                if aid and aid not in processed_ids and aid not in all_new_papers:
                    all_new_papers[f"arxiv:{aid}"] = p
            time.sleep(3)
        except Exception as e:
            print(f"    ⚠️ arXiv 检索失败: {e}")

    papers_list = list(all_new_papers.values())
    print(f"📄 发现 {len(papers_list)} 篇新论文")

    if not papers_list:
        print("今日无新论文")
        return

    # 4. 生成摘要
    papers_list = generate_chinese_summary(papers_list, MY_RESEARCH_FOCUS)

    # 5. 生成报告
    report = generate_daily_report(papers_list, today)
    report_path = DAILY_REPORTS_DIR / f"report_{today}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"📋 日报已保存: {report_path}")

    # 6. 更新缓存
    new_ids = []
    for p in papers_list:
        pid = p.get("paperId")
        if not pid:
            aid = p.get("arxiv_id")
            if aid:
                pid = f"arxiv:{aid}"
        if pid:
            new_ids.append(pid)
    processed_ids.update(new_ids)
    save_cache(processed_ids)

    return report

if __name__ == "__main__":
    run_daily_tracker()