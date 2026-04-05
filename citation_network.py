"""
场景二：引用网络分析与关键论文识别 v2
从种子论文出发，递归展开引用网络，识别核心论文
使用 citation context 和 influential flags
"""
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path
import networkx as nx
from semantic_scholar_client import SemanticScholarClient
from config import OUTPUT_DIR

PAPER_FIELDS = "paperId,title,year,citationCount,influentialCitationCount,authors,abstract,tldr"

def get_paper_id_by_title(client: SemanticScholarClient, title: str) -> str:
    """通过标题搜索 Paper ID"""
    results = client.search_papers(title, limit=1, fields="paperId,title")
    if not results:
        raise ValueError(f"未找到论文：{title}")
    paper = results[0]
    print(f"找到论文：{paper['title']} ({paper['paperId']})")
    return paper["paperId"]

def build_citation_graph(seed_ids: list[str], depth: int = 2, max_papers: int = 200, api_key: str = None) -> nx.DiGraph:
    """BFS 构建引用图，使用 SemanticScholarClient"""
    G = nx.DiGraph()
    visited = set()
    queue = deque([(pid, 0) for pid in seed_ids])

    while queue and len(visited) < max_papers:
        paper_id, current_depth = queue.popleft()
        if paper_id in visited:
            continue
        visited.add(paper_id)

        try:
            # 获取论文元数据
            paper_data = client.get_paper(paper_id, fields=PAPER_FIELDS)
            tldr = paper_data.get("tldr", {})
            tldr_text = tldr.get("text", "") if isinstance(tldr, dict) else ""

            G.add_node(paper_id, **{
                "title": paper_data.get("title", "Unknown"),
                "year": paper_data.get("year", 0),
                "citations": paper_data.get("citationCount", 0),
                "influentialCitations": paper_data.get("influentialCitationCount", 0),
                "is_seed": paper_id in seed_ids,
                "tldr": tldr_text
            })

            print(f"  处理 [{len(visited)}/{max_papers}]: {paper_data.get('title', '')[:50]}...")

            if current_depth < depth:
                # 获取引用上下文（包含 influential 标记）
                citations = client.get_paper_citations_with_context(paper_id, limit=100)
                for cite in citations:
                    cite_id = cite.get("paperId")
                    if cite_id:
                        # 边权重：influential 论文权重更高
                        weight = 2.0 if cite.get("isInfluential", False) else 1.0
                        G.add_edge(cite_id, paper_id, weight=weight, isInfluential=cite.get("isInfluential", False))
                        if cite_id not in visited:
                            queue.append((cite_id, current_depth + 1))

                # 获取参考文献
                references = client.get_paper_references(paper_id, limit=100)
                for ref in references:
                    ref_id = ref.get("paperId")
                    if ref_id:
                        G.add_edge(paper_id, ref_id, weight=1.0, isInfluential=False)
                        if ref_id not in visited:
                            queue.append((ref_id, current_depth + 1))

                time.sleep(1)  # 遵守速率限制

        except Exception as e:
            print(f"    ⚠️ 获取论文失败: {e}")
            time.sleep(2)

    return G

def analyze_graph(G: nx.DiGraph) -> dict:
    """计算图分析指标，考虑边权重"""
    # 加权 PageRank
    try:
        pagerank = nx.pagerank(G, alpha=0.85, weight="weight")
    except:
        pagerank = {}

    # 入度中心性
    in_degree = dict(G.in_degree())

    # 高影响力引用数
    influential_counts = {}
    for _, _, data in G.edges(data=True):
        if data.get("isInfluential", False):
            target = G.edges[(_, _)][0] if _ else None  # 简化

    # 合并属性
    for node in G.nodes():
        G.nodes[node]["pagerank"] = pagerank.get(node, 0)
        G.nodes[node]["in_degree"] = in_degree.get(node, 0)

    # Top 论文
    top_papers = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        "total_papers": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "top_papers": top_papers,
        "pagerank": pagerank
    }

def export_for_gephi(G: nx.DiGraph, output_path: Path):
    """导出 GEXF 格式"""
    nx.write_gexf(G, str(output_path))
    print(f"✅ Gephi 文件已保存：{output_path}")

def generate_report(G: nx.DiGraph, analysis: dict, output_dir: Path) -> str:
    """生成核心论文报告"""
    lines = [f"# 引用网络分析报告\n\n"]
    lines.append(f"**生成日期**: {datetime.now().strftime('%Y-%m-%d')}\n\n")
    lines.append(f"**论文总数**: {analysis['total_papers']}\n")
    lines.append(f"**引用关系总数**: {analysis['total_edges']}\n")
    lines.append(f"（包含高影响力引用标记）\n\n")
    lines.append("---\n\n")
    lines.append("## Top 20 核心论文（按 PageRank 排序）\n\n")
    lines.append("| 排名 | 标题 | 年份 | 引用数 | 高影响力 | PageRank |\n")
    lines.append("|------|------|------|--------|----------|----------|\n")

    for rank, (pid, score) in enumerate(analysis["top_papers"], 1):
        node = G.nodes.get(pid, {})
        title = node.get("title", "Unknown")[:45]
        year = node.get("year", "N/A")
        citations = node.get("citations", 0)
        influential = node.get("influentialCitations", 0)
        lines.append(f"| {rank} | {title} | {year} | {citations} | {influential} | {score:.4f} |\n")

    report = "".join(lines)
    report_path = output_dir / "network_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 报告已保存：{report_path}")
    return report

def run(seed_titles: list[str], depth: int = 2, max_papers: int = 150, api_key: str = None, output_dir: str = None):
    """主流程"""
    global client
    client = SemanticScholarClient(api_key)

    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    print("🔍 解析种子论文...")
    seed_ids = []
    for t in seed_titles:
        try:
            pid = get_paper_id_by_title(client, t)
            seed_ids.append(pid)
        except Exception as e:
            print(f"  ⚠️ {e}")

    if not seed_ids:
        print("未找到种子论文")
        return

    print(f"🕸️ 构建引用网络（depth={depth}）...")
    G = build_citation_graph(seed_ids, depth=depth, max_papers=max_papers, api_key=api_key)

    print("📊 分析网络结构...")
    analysis = analyze_graph(G)

    export_for_gephi(G, output_dir / "citation_network.gexf")
    generate_report(G, analysis, output_dir)

    print(f"✅ 分析完成！共 {analysis['total_papers']} 篇论文，{analysis['total_edges']} 条引用关系")

if __name__ == "__main__":
    import sys
    seeds = sys.argv[1:] if len(sys.argv) > 1 else ["Quantum sensing with NV centers in diamond"]
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    run(seeds, depth=2, api_key=api_key)