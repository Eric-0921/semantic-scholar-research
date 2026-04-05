"""
场景五：Related Work 章节辅助写作
给定论文草稿或方法描述，自动检索相关文献，生成 Related Work 段落
"""
import re
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List
from semantic_scholar_client import SemanticScholarClient
from config import SEMANTIC_SCHOLAR_API_KEY, OUTPUT_DIR

# Initialize client once at module level
_client = SemanticScholarClient(api_key=SEMANTIC_SCHOLAR_API_KEY) if SEMANTIC_SCHOLAR_API_KEY else SemanticScholarClient()


def extract_keywords_from_draft(draft: str) -> List[str]:
    """从论文草稿中提取搜索关键词（简化版，基于规则）"""
    if not draft:
        return []

    # 常见方法/技术词汇
    tech_patterns = [
        r'\b(NV[ -]?center|nitrogen[ -]?vacancy|diamond quantum)',
        r'\b(quantum sensing|magnetometry|magnetic sensing)',
        r'\b(spin|entanglement|coherence|decoherence)',
        r'\b(magnetometer|optical detection|NMR|MRI)',
        r'\b(microwave|initialization|readout|rabi)',
        r'\b(deep learning|neural network|transformer)',
        r'\b(electron|paramagnetic resonance|EPR|ODMR)',
    ]

    keywords = []
    draft_lower = draft.lower()

    for pattern in tech_patterns:
        matches = re.findall(pattern, draft_lower)
        keywords.extend(matches)

    # 提取连续的技术术语（2-4词）
    multi_word = re.findall(r'\b[a-z]+(?:\s+[a-z]+){1,3}\b', draft_lower)

    # 过滤停用词
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                  'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                  'can', 'need', 'this', 'that', 'these', 'those', 'we', 'our',
                  'they', 'their', 'it', 'its', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'and', 'or', 'but', 'if', 'then'}

    meaningful = [w for w in multi_word if w not in stop_words and len(w) > 8]

    # 合并去重
    all_keywords = list(set(keywords + meaningful))

    # 如果提取太少，用 draft 前100字作为查询
    if len(all_keywords) < 3:
        all_keywords.append(draft[:50].strip())

    return all_keywords[:8]


def search_related_papers(keywords: List[str], limit_per_keyword: int = 15) -> list[dict]:
    """多关键词搜索，使用 search_papers_bulk 高效检索"""
    all_papers = {}

    # Fields for semantic similarity and categorization
    fields = "paperId,title,abstract,year,citationCount,authors,venue,tldr,openAccessPdf,embedding.specter_v2,fieldsOfStudy"

    for kw in keywords:
        if not kw or len(kw) < 3:
            continue

        try:
            # Use bulk search for efficient querying
            results = _client.search_papers_bulk(
                query=kw,
                limit=limit_per_keyword,
                fields=fields
            )
            for p in results:
                all_papers[p["paperId"]] = p
        except Exception as e:
            print(f"  搜索 '{kw}' 失败: {e}")

        time.sleep(1)  # 限速

    # Filter papers with abstracts, sort by citation count
    papers = [p for p in all_papers.values() if p.get("abstract")]
    papers = sorted(papers, key=lambda x: x.get("citationCount", 0), reverse=True)

    return papers[:40]


def categorize_papers(papers: List[dict], user_method_desc: str) -> dict:
    """基于规则对论文分类（简化版，无需 LLM）"""

    categories = {
        "direct_comparison": {
            "name": "Direct Comparisons and Baselines",
            "papers": [],
            "description": "使用相同数据集或任务的论文"
        },
        "method_inspiration": {
            "name": "Method Inspirations",
            "papers": [],
            "description": "提出类似方法或受相同原理启发的论文"
        },
        "background_knowledge": {
            "name": "Background and Fundamentals",
            "papers": [],
            "description": "提供理论基础或背景知识的论文"
        },
        "same_principle": {
            "name": "Same Physical Principle",
            "papers": [],
            "description": "基于相同物理原理的研究"
        }
    }

    user_lower = user_method_desc.lower()
    user_keywords = set(re.findall(r'\b\w+\b', user_lower))

    for p in papers:
        title_lower = p.get("title", "").lower()
        abstract_lower = p.get("abstract", "")[:500].lower()
        year = p.get("year", 0)
        citations = p.get("citationCount", 0)

        paper_text = f"{title_lower} {abstract_lower}"
        paper_keywords = set(re.findall(r'\b\w+\b', paper_text))

        # 计算与用户方法的关键词重叠度
        overlap = len(user_keywords & paper_keywords)

        # 检查是否提到相同数据集/任务
        datasets = ['mnist', 'cifar', 'imagenet', 'benchmark', 'dataset']
        has_same_dataset = any(ds in paper_text for ds in datasets)

        # 检查是否基于相同物理原理
        physics_terms = ['nv center', 'nitrogen vacancy', 'spin', 'quantum', 'diamond', 'magnetometry']
        same_physics = any(term in paper_text for term in physics_terms) and any(term in user_lower for term in physics_terms)

        # 分类逻辑
        if has_same_dataset and overlap > 2:
            categories["direct_comparison"]["papers"].append(p)
        elif same_physics and overlap > 1:
            categories["same_principle"]["papers"].append(p)
        elif overlap > 3:
            categories["method_inspiration"]["papers"].append(p)
        else:
            categories["background_knowledge"]["papers"].append(p)

    # 每个类别按时间排序（早的在前）
    for cat in categories.values():
        cat["papers"] = sorted(cat["papers"], key=lambda x: x.get("year", 0))

    # 只保留有论文的类别
    return {k: v for k, v in categories.items() if v["papers"]}


def generate_related_work_text(categories: dict, user_method_desc: str) -> str:
    """生成 Related Work 正文（简化版，基于模板）"""

    lines = []
    lines.append("## Related Work\n\n")
    lines.append("Our work builds upon a rich literature in quantum sensing and NV center research. ")
    lines.append("We review related work in several categories.\n\n")

    category_names = {
        "direct_comparison": "Direct Comparisons and Baselines",
        "method_inspiration": "Methodological Inspirations",
        "same_principle": "Same Physical Principle",
        "background_knowledge": "Background and Fundamentals"
    }

    for cat_key, cat_data in categories.items():
        papers = cat_data["papers"]
        if not papers:
            continue

        cat_name = category_names.get(cat_key, cat_data["name"])
        lines.append(f"### {cat_name}\n\n")

        for p in papers[:5]:  # 每类最多5篇
            title = p.get("title", "Unknown")
            year = p.get("year", "n.d.")
            authors = p.get("authors", [])
            author_str = ", ".join([a.get("name", "Unknown") for a in authors[:2]])
            if len(authors) > 2:
                author_str += " et al."
            citations = p.get("citationCount", 0)
            venue = p.get("venue", "arXiv")

            lines.append(f"{author_str} ({year}) proposed ")
            lines.append(f"\"{title[:60]}...")
            lines.append(f"\" in {venue} ")
            lines.append(f"(cited by {citations}). ")
            lines.append(f"[[Semantic Scholar]](https://www.semanticscholar.org/paper/{p.get('paperId', '')}).\n\n")

    lines.append("\n---\n")
    lines.append("**Note**: This is an auto-generated Related Work draft. ")
    lines.append("Please review and edit for accuracy and completeness.\n")

    return "".join(lines)


def generate_latex_references(papers: List[dict]) -> str:
    """生成 LaTeX BibTeX 引用"""
    entries = []

    for p in papers:
        first_author = (p.get("authors") or [{}])[0].get("name", "Unknown")
        last_name = first_author.split()[-1] if first_author else "Unknown"
        year = p.get("year", 0)
        paper_id = p.get("paperId", "unknown")[:8]
        key = f"{last_name}{year}"

        authors_list = p.get("authors", [])
        authors_str = " and ".join([a.get("name", "Unknown") for a in authors_list]) if authors_list else "Unknown"

        title = p.get("title", "Unknown Title")
        venue = p.get("venue", "arXiv preprint")

        entry = f"""@article{{{key}{paper_id},
  title     = {{{title}}},
  author    = {{{authors_str}}},
  year      = {{{year}}},
  journal   = {{{venue}}},
  note      = {{Cited by {p.get('citationCount', 0)}}}
}}"""
        entries.append(entry)

    return "\n\n".join(entries)


def run(draft_or_description: str, output_dir: str = None) -> str:
    """主流程"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    print("🔍 提取关键词...")
    keywords = extract_keywords_from_draft(draft_or_description)
    print(f"  提取到关键词: {keywords}")

    if not keywords:
        print("未能提取有效关键词")
        return ""

    print("📚 搜索相关论文...")
    papers = search_related_papers(keywords)
    print(f"  找到 {len(papers)} 篇候选论文")

    if not papers:
        print("未找到相关论文")
        return ""

    print("✍️  生成 Related Work...")
    categories = categorize_papers(papers, draft_or_description)
    related_work = generate_related_work_text(categories, draft_or_description)
    bibtex = generate_latex_references(papers)

    # 保存结果
    output_path = output_dir / "related_work_draft.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Related Work 草稿\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("---\n\n")
        f.write("## 用户方法描述\n\n")
        f.write(f"{draft_or_description[:500]}...\n\n")
        f.write("---\n\n")
        f.write(related_work)
        f.write("\n\n---\n\n## BibTeX References\n\n```bibtex\n")
        f.write(bibtex)
        f.write("\n```")

    print(f"✅ Related Work 草稿已保存: {output_path}")

    # 保存分类后的论文列表
    cat_output = output_dir / "related_papers_categorized.json"
    with open(cat_output, "w", encoding="utf-8") as f:
        json.dump({
            "categories": {k: {**v, "papers": [{"title": p["title"], "paperId": p["paperId"]} for p in v["papers"]]}
                          for k, v in categories.items()},
            "all_papers_count": len(papers)
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ 分类数据已保存: {cat_output}")

    return str(output_path)


if __name__ == "__main__":
    import sys

    # 默认示例：NV量子传感相关
    example_desc = """
    We propose a novel NV center based magnetometer using deep learning
    for noise cancellation and adaptive sensing. Our method achieves
    10x improvement in sensitivity compared to conventional lock-in
    detection methods at room temperature. We demonstrate applications
    in biological imaging and magnetic field mapping.
    """

    # 从命令行参数读取或使用默认
    if len(sys.argv) > 1:
        desc = sys.argv[1]
    else:
        desc = example_desc

    run(desc)