"""
场景一：文献综述自动化 Pipeline
输入关键词，自动检索、筛选、理解论文，生成结构化综述草稿
"""
import json
import time
from datetime import datetime
from pathlib import Path
from semantic_scholar_client import SemanticScholarClient
from config import SEMANTIC_SCHOLAR_API_KEY, OUTPUT_DIR

# Initialize client once
_client = SemanticScholarClient(api_key=SEMANTIC_SCHOLAR_API_KEY) if SEMANTIC_SCHOLAR_API_KEY else SemanticScholarClient()

def search_papers(query: str, limit: int = 20, year_start: int = 2020, min_citation_count: int = 0) -> list[dict]:
    """搜索论文"""
    fields = "paperId,title,abstract,tldr,year,citationCount,openAccessPdf,authors,venue,externalIds,fieldsOfStudy,influentialCitationCount"
    return _client.search_papers_bulk(
        query=query,
        limit=limit,
        fields=fields,
        year_start=year_start,
        min_citation_count=min_citation_count
    )

def filter_papers(papers: list[dict], min_citations: int = 3) -> list[dict]:
    """过滤：保留高引用或有 TLDR 的论文"""
    filtered = []
    for p in papers:
        if p.get("citationCount", 0) >= min_citations or p.get("tldr") or p.get("influentialCitationCount", 0) > 0:
            filtered.append(p)
    return filtered

def format_paper_for_llm(paper: dict) -> str:
    """格式化论文为 LLM 可读格式"""
    tldr = paper.get("tldr", {})
    tldr_text = tldr.get("text", "") if isinstance(tldr, dict) else ""
    authors = ", ".join([a.get("name", "") for a in paper.get("authors", [])[:3]])
    if len(paper.get("authors", [])) > 3:
        authors += " et al."

    external_ids = paper.get("externalIds", {})
    doi = external_ids.get("DOI", "N/A") if external_ids else "N/A"
    fields_of_study = paper.get("fieldsOfStudy", [])
    fields_str = ", ".join(fields_of_study[:3]) if fields_of_study else "N/A"
    influential_cites = paper.get("influentialCitationCount", 0)

    return f"""
---
标题: {paper.get('title', 'N/A')}
作者: {authors}
年份: {paper.get('year', 'N/A')}
发表于: {paper.get('venue', 'N/A')}
DOI: {doi}
研究领域: {fields_str}
引用数: {paper.get('citationCount', 0)}
高影响力引用: {influential_cites}
TLDR: {tldr_text or '无'}
摘要: {(paper.get('abstract') or '无摘要')[:800]}
---"""

def generate_literature_review(topic: str, papers: list[dict], output_dir: Path) -> str:
    """生成文献综述（需要调用 LLM API）"""
    # 注意：这里需要调用 LLM 生成综述
    # 简化版本：生成格式化报告

    papers_text = "\n".join([format_paper_for_llm(p) for p in papers])

    # 综述结构
    review_lines = [
        f"# {topic} 文献综述\n\n",
        f"**生成日期**: {datetime.now().strftime('%Y-%m-%d')}\n\n",
        "## 1. 研究背景与动机\n\n",
        "近年来，金刚石NV色心和量子传感技术快速发展...\n\n",
        "## 2. 主要研究方向\n\n",
    ]

    # 按引用数排序
    top_papers = sorted(papers, key=lambda x: x.get("citationCount", 0), reverse=True)[:20]

    for i, p in enumerate(top_papers[:10], 1):
        title = p.get("title", "N/A")
        year = p.get("year", "N/A")
        citations = p.get("citationCount", 0)
        authors = ", ".join([a.get("name", "") for a in p.get("authors", [])[:2]])
        if len(p.get("authors", [])) > 2:
            authors += " et al."

        review_lines.append(f"### {i}. {title}\n")
        review_lines.append(f"- **作者**: {authors} ({year})\n")
        review_lines.append(f"- **引用**: {citations}次\n")
        review_lines.append(f"- **TLDR**: {p.get('tldr', {}).get('text', 'N/A') if isinstance(p.get('tldr'), dict) else 'N/A'}\n\n")

    review_lines.append("\n## 3. 参考文献\n\n")
    for p in top_papers[:20]:
        authors_bib = " and ".join([a.get("name", "Unknown") for a in p.get("authors", [])])
        review_lines.append(f"- {p.get('title', 'N/A')} — {authors_bib}, {p.get('year', 'N/A')}\n")

    return "".join(review_lines)

def run_literature_review(topic: str, output_dir: str = None):
    """主流程"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"🔍 正在搜索主题：{topic}")

    all_papers = {}
    queries = [topic, f"{topic} survey", f"{topic} review", f"{topic} NV center", f"{topic} quantum sensing"]

    for q in queries:
        papers = search_papers(q, limit=15)
        for p in papers:
            pid = p.get("paperId")
            if pid:
                all_papers[pid] = p
        time.sleep(1)

    papers_list = list(all_papers.values())
    papers_list = filter_papers(papers_list, min_citations=2)
    papers_list = sorted(papers_list, key=lambda x: x.get("citationCount", 0), reverse=True)[:25]

    print(f"✅ 筛选后保留 {len(papers_list)} 篇论文")
    print("📝 正在生成文献综述...")

    review = generate_literature_review(topic, papers_list, output_dir)

    # 保存
    safe_topic = topic.replace(" ", "_").replace("/", "_")
    review_path = output_dir / f"literature_review_{safe_topic}.md"
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(review)

    print(f"✅ 综述已保存：{review_path}")
    return str(review_path)

if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "NV center quantum sensing"
    run_literature_review(topic)