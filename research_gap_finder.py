"""
场景四：研究 Gap 挖掘器
分析领域"已解决"和"未解决"问题，从 Future Work 章节提取研究空白
"""
import requests
import re
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List
from semantic_scholar_client import SemanticScholarClient
from config import SEMANTIC_SCHOLAR_API_KEY, OUTPUT_DIR

# Initialize client (uses built-in retry mechanism)
client = SemanticScholarClient(api_key=SEMANTIC_SCHOLAR_API_KEY)


def fetch_top_papers(query: str, n: int = 50) -> List[dict]:
    """获取领域 Top N 高引论文（使用 influentialCitationCount 优先级排序）"""
    fields = "paperId,title,abstract,citationCount,openAccessPdf,year,authors,tldr,fieldsOfStudy,externalIds,influentialCitationCount"
    try:
        papers = client.search_papers_bulk(query, limit=n, fields=fields)
        # Sort by influentialCitationCount for better prioritization
        return sorted(papers, key=lambda x: x.get("influentialCitationCount", 0), reverse=True)
    except Exception as e:
        print(f"  搜索失败: {e}")
        return []


def download_pdf_text(pdf_url: str) -> str:
    """下载并提取 PDF 文本（需要 pdfplumber）"""
    try:
        import pdfplumber
        import io

        r = requests.get(pdf_url, timeout=30)
        if r.status_code != 200:
            return ""

        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        return text
    except ImportError:
        print("  pdfplumber 未安装，无法解析 PDF")
        return ""
    except Exception as e:
        print(f"  PDF 下载失败: {e}")
        return ""


def extract_future_work_section(text: str) -> str:
    """用正则提取 Future Work / Limitations 章节"""
    if not text:
        return ""

    # 多种模式匹配 Future Work / Limitations / Conclusion 章节
    patterns = [
        # 标准格式：Future Work 或 Limitations 标题后跟内容
        r"(?:^|\n)(?:IV\s*\.?\s*)?(?:Future\s*Work|Future\s*Directions?|Limitations?|Concluding\s*Remarks?|Conclusions?)(?:\s*[:\.]?\s*\n)(.*?)(?=\n\s*(?:IV|V|VI|VII|IX|X|\d+\.|References|BIBLIOGRAPHY|$))",
        # 编号格式：7. Future Work 或 8. Limitations
        r"(?:^|\n)(?:7|8|9|10)\.\s*(?:Future|Conclusion|Limitation)(?:s)?\s*\n(.*?)(?=\n\s*\d+\.|References|$)",
        # 冒号分隔
        r"(?:Future\s*Work|Limitations?)[:\s]+(.*?)(?=\n\s*\n[A-Z][a-z]+|\n\s*References|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            section = match.group(1).strip()
            # 清理多余空白
            section = re.sub(r'\n{3,}', '\n\n', section)
            section = re.sub(r'\s+', ' ', section)
            return section[:2000]  # 限制长度

    return ""


def extract_gaps_from_abstract(abstract: str, title: str, year: int, citations: int) -> str:
    """从摘要推断研究局限（当无法获取 PDF 时的备选方案）"""
    # 简化版本：基于规则提取可能的 gap
    # 完整版本需要调用 LLM

    if not abstract:
        return ""

    gaps = []

    # 检测常见的研究局限表述
    limitation_patterns = [
        (r'future\s*work\s*(?:is\s*)?(?:needed|required|suggested)', '需要进一步探索未来方向'),
        (r'limitation\s*(?:s)?(?:\s*include)?', '存在一定局限性'),
        (r'(?:we\s*(?:plan|intend|will)\s+\w+|future\s+studies?\s+(?:will|may|should))', '计划在未来研究中改进'),
        (r'only\s+(?:tested|evaluated|validated)\s+(?:on|in)', '仅在某方面验证'),
        (r'(?:does\s+not|not\s+yet|have\s+not)\s+\w+', '尚未完全解决'),
    ]

    abstract_lower = abstract.lower()
    for pattern, description in limitation_patterns:
        if re.search(pattern, abstract_lower):
            gaps.append(f"- {description}")

    # 如果没有检测到明确表述，生成通用推断
    if not gaps:
        gaps.append(f"- 基于{year}年的研究水平，可能存在技术扩展的空间")
        gaps.append(f"- 方法的泛化性需要进一步验证")
        gaps.append(f"- 计算效率或实验规模可能有限制")

    return "\n".join(gaps[:3])


def cluster_and_prioritize_gaps(all_gaps: List[dict]) -> str:
    """聚类分析所有 gap，输出优先级报告"""
    if not all_gaps:
        return "未找到足够的研究 gap 信息"

    # 按引用数排序
    sorted_gaps = sorted(all_gaps, key=lambda x: x.get("citations", 0), reverse=True)

    # 简单聚类：基于关键词共现
    gap_keywords = {}
    for gap_info in all_gaps:
        title = gap_info.get("title", "").lower()
        gaps_text = gap_info.get("gaps", "")

        # 提取关键词
        keywords = re.findall(r'\b(?:future|limit|extension|scalab|robust|generaliz|noise|efficiency|accuracy|performance)\w*', gaps_text.lower())
        for kw in keywords:
            if kw not in gap_keywords:
                gap_keywords[kw] = []
            gap_keywords[kw].append(gap_info)

    # 统计高频主题
    topic_counts = {kw: len(papers) for kw, papers in gap_keywords.items()}
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # 构建报告
    lines = []
    lines.append("## 研究 Gap 聚类分析\n\n")

    lines.append("### 高频研究主题（跨论文共现）\n\n")
    for topic, count in top_topics:
        lines.append(f"- **{topic}** ({count} 篇论文提及)\n")
    lines.append("\n")

    lines.append("### Top 10 高影响力论文的研究空白\n\n")
    for i, gap_info in enumerate(sorted_gaps[:10], 1):
        title = gap_info.get("title", "Unknown")[:60]
        citations = gap_info.get("citations", 0)
        gaps = gap_info.get("gaps", "未检测到明确 gap")

        lines.append(f"**{i}. {title}**\n")
        lines.append(f"- 引用数: {citations}\n")
        lines.append(f"- 研究空白:\n{gaps}\n\n")

    lines.append("\n## 优先研究建议\n\n")
    lines.append("基于以上分析，建议关注以下研究空白：\n\n")

    priority_gaps = []
    for topic, count in top_topics[:3]:
        priority_gaps.append(f"- **{topic}** 相关研究（被 {count} 篇高引论文提及）")

    lines.extend(priority_gaps)

    lines.append("\n\n---\n")
    lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    return "".join(lines)


def run(field: str, top_n: int = 50, output_dir: str = None):
    """主流程"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"🔍 搜索领域: {field}，Top {top_n} 篇论文")

    # 获取高引论文
    papers = fetch_top_papers(field, top_n)
    if not papers:
        print("未找到相关论文")
        return

    print(f"✅ 获取到 {len(papers)} 篇论文，开始分析...")

    all_gaps = []
    for i, paper in enumerate(papers):
        paper_id = paper.get("paperId", "")
        title = paper.get("title", "Unknown")[:60]
        citations = paper.get("citationCount", 0)
        year = paper.get("year", 0)

        print(f"[{i+1}/{len(papers)}] 处理: {title}... (引用:{citations})")

        gaps = ""
        pdf_url = ""

        # 优先尝试从 PDF 提取
        pdf_info = paper.get("openAccessPdf")
        if pdf_info and isinstance(pdf_info, dict):
            pdf_url = pdf_info.get("url", "")

        if pdf_url:
            text = download_pdf_text(pdf_url)
            if text:
                section = extract_future_work_section(text)
                if section:
                    gaps = section
                    print(f"    ✓ 从 PDF 提取到 Future Work ({len(section)} 字符)")

        # 备选：从摘要推断
        if not gaps:
            abstract = paper.get("abstract", "")
            if abstract:
                gaps = extract_gaps_from_abstract(abstract, title, year, citations)
                print(f"    ~ 从摘要推断 Gap")

        if gaps:
            all_gaps.append({
                "paper_id": paper_id,
                "title": paper.get("title", "Unknown"),
                "year": year,
                "citations": citations,
                "gaps": gaps,
                "source": "pdf" if pdf_url else "abstract"
            })

        # 限速
        time.sleep(1)

    print(f"\n✅ 成功提取 {len(all_gaps)} 篇论文的 gap 信息")

    if not all_gaps:
        print("未能提取有效的研究 gap 信息")
        return

    # 聚类分析
    print("📊 正在进行聚类分析...")
    report = cluster_and_prioritize_gaps(all_gaps)

    # 保存报告
    safe_field = re.sub(r'[^\w\s-]', '', field).replace(' ', '_')[:30]
    report_header = f"# {field} 研究 Gap 分析报告\n\n"
    report_header += f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    report_header += f"**分析论文数**: {len(papers)} 篇\n"
    report_header += f"**成功提取 Gap**: {len(all_gaps)} 篇\n\n"
    report_header += "---\n\n"

    output_path = output_dir / f"research_gaps_{safe_field}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_header)
        f.write(report)

    print(f"✅ 报告已保存: {output_path}")

    # 同时保存 JSON 格式的原始数据
    json_path = output_dir / f"research_gaps_{safe_field}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "field": field,
            "analyzed_papers": len(papers),
            "extracted_gaps": len(all_gaps),
            "gaps": all_gaps,
            "timestamp": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON 数据已保存: {json_path}")

    return str(output_path)


if __name__ == "__main__":
    import sys
    field = sys.argv[1] if len(sys.argv) > 1 else "NV center quantum sensing"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    run(field, n)