#!/usr/bin/env python3
"""
每日科研简报生成与推送
整合 paper_tracker + author_tracker，生成飞书文档 + 消息卡片

用法:
    python daily_report.py                    # 今日报告
    python daily_report.py --days 7           # 近7天报告
    python daily_report.py --dry-run          # 仅生成本地文件，不推送
    python daily_report.py --user-email xxx   # 指定推送用户邮箱
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# 导入项目模块
from paper_tracker import run as run_tracker
from author_tracker import run as run_author_tracker
from citation_network import analyze_citations
import feishu_publisher
from config import OUTPUT_DIR, DAYS_BACK

# 默认推送配置
DEFAULT_USER_EMAIL = None  # 留空表示推送给机器人自身（用于测试）


def parse_args():
    parser = argparse.ArgumentParser(description="每日科研简报生成与推送")
    parser.add_argument("--days", type=int, default=1, help="追溯天数 (默认: 1)")
    parser.add_argument("--dry-run", action="store_true", help="仅生成本地文件，不推送飞书")
    parser.add_argument("--user-email", type=str, default=DEFAULT_USER_EMAIL, help="推送目标邮箱")
    parser.add_argument("--user-open-id", type=str, default=None, help="推送目标 open_id (优先级高于 email)")
    parser.add_argument("--output-only", action="store_true", help="仅输出 Markdown，不创建文档")
    return parser.parse_args()


def generate_report_markdown(date_str: str, days_back: int, papers: List[dict],
                             author_papers: List[dict]) -> str:
    """生成完整的 Markdown 报告"""

    # 统计
    total_papers = len(papers)
    high_impact = sum(1 for p in papers if p.get("influentialCitationCount", 0) > 5)
    author_count = len(author_papers)

    lines = [
        f"# 📚 每日科研简报",
        f"",
        f"**日期**: {date_str}",
        f"**追溯周期**: 最近 {days_back} 天",
        f"",
        f"---",
        f"",
        f"## 📊 统计概览",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 新论文总数 | {total_papers} 篇 |",
        f"| 高影响力论文 | {high_impact} 篇 🔥 |",
        f"| 作者追踪发现 | {author_count} 篇 |",
        f"",
        f"---",
        f"",
    ]

    # 高影响力论文
    if high_impact > 0:
        lines.append("## 🔥 高影响力论文")
        lines.append("")

        high_impact_papers = [p for p in papers if p.get("influentialCitationCount", 0) > 5]
        high_impact_papers.sort(key=lambda x: x.get("influentialCitationCount", 0), reverse=True)

        for i, p in enumerate(high_impact_papers[:10], 1):
            title = p.get("title", "N/A")[:60]
            citations = p.get("citationCount", 0)
            influential = p.get("influentialCitationCount", 0)
            year = p.get("year", "N/A")
            venue = p.get("venue", "arXiv")
            paper_id = p.get("paperId", "")

            lines.append(f"### {i}. {title}")
            lines.append("")
            lines.append(f"- **作者/年份**: {year}")
            lines.append(f"- **期刊/会议**: {venue}")
            lines.append(f"- **引用数**: {citations} (高影响力: {influential}) 🔥")
            lines.append(f"- **链接**: [Semantic Scholar](https://www.semanticscholar.org/paper/{paper_id})")
            lines.append("")

    # 新论文列表
    lines.append("## 📄 最新论文列表")
    lines.append("")

    # 按日期排序
    sorted_papers = sorted(papers, key=lambda x: x.get("publicationDate", ""), reverse=True)

    for i, p in enumerate(sorted_papers[:30], 1):
        title = p.get("title", "N/A")[:60]
        year = p.get("year", "N/A")
        citations = p.get("citationCount", 0)
        influential = p.get("influentialCitationCount", 0)
        venue = p.get("venue", "arXiv")
        paper_id = p.get("paperId", "")
        tldr = p.get("tldr", {})
        tldr_text = tldr.get("text", "")[:150] if isinstance(tldr, dict) and tldr else ""

        lines.append(f"### {i}. {title}")
        lines.append("")

        if tldr_text:
            lines.append(f"> {tldr_text}...")
        else:
            abstract = p.get("abstract", "无摘要")
            lines.append(f"> {abstract[:150]}...")

        lines.append("")
        lines.append(f"- **年份**: {year} | **期刊**: {venue} | **引用**: {citations}", end="")
        if influential > 0:
            lines.append(f" | 🔥 高影响力: {influential}")
        else:
            lines.append("")
        lines.append(f"- **链接**: [Semantic Scholar](https://www.semanticscholar.org/paper/{paper_id})")
        lines.append("")

    # 作者追踪
    if author_papers:
        lines.append("---")
        lines.append("")
        lines.append("## 👤 作者追踪")
        lines.append("")

        # 按作者分组
        author_map = {}
        for p in author_papers:
            authors = p.get("authors", [])
            if authors:
                author_name = authors[0].get("name", "Unknown")
                if author_name not in author_map:
                    author_map[author_name] = []
                author_map[author_name].append(p)

        for author_name, author_papers_list in author_map.items():
            lines.append(f"### {author_name}")
            lines.append("")
            for p in author_papers_list[:5]:
                title = p.get("title", "N/A")[:50]
                year = p.get("year", "N/A")
                citations = p.get("citationCount", 0)
                paper_id = p.get("paperId", "")
                lines.append(f"- [{title}](https://www.semanticscholar.org/paper/{paper_id}) ({year}, cited: {citations})")
            lines.append("")

    # 搜索关键词
    from config import WATCH_KEYWORDS, CORE_KEYWORDS
    lines.append("---")
    lines.append("")
    lines.append("## 🔍 搜索关键词")
    lines.append("")
    lines.append(f"**核心关键词**: {', '.join(CORE_KEYWORDS)}")
    lines.append("")
    lines.append(f"**扩展关键词**: {', '.join(WATCH_KEYWORDS[:10])}...")
    lines.append("")

    # 页脚
    lines.append("---")
    lines.append("")
    lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append(f"*由 Semantic Scholar Research Automation 生成*")

    return "\n".join(lines)


def save_local_report(date_str: str, markdown_content: str) -> Path:
    """保存报告到本地文件"""
    output_dir = OUTPUT_DIR / "daily_reports"
    output_dir.mkdir(exist_ok=True)

    filename = f"daily_report_{date_str}.md"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return filepath


def main():
    args = parse_args()
    days_back = args.days
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"📅 生成每日科研简报: {date_str} (追溯 {days_back} 天)")
    print()

    # 1. 运行 paper_tracker（临时修改 DAYS_BACK）
    print("🔍 正在检索论文...")
    from config import config as cfg

    # 保存原始值
    original_days_back = cfg.DAYS_BACK
    cfg.DAYS_BACK = days_back

    # 运行追踪
    papers = []
    try:
        # paper_tracker 的 run() 会自动运行并保存报告
        # 我们需要捕获它返回/保存的数据
        import paper_tracker
        paper_tracker.DAYS_BACK = days_back

        # 重新运行（使用 paper_tracker 的 run 函数）
        # 由于 paper_tracker.run() 会写入文件，我们直接调用它的逻辑
        from paper_tracker import load_cache, save_cache, fetch_recent_papers, fetch_author_papers
        from semantic_scholar_client import SemanticScholarClient
        from arxiv_client import search_arxiv
        from config import WATCH_KEYWORDS, CORE_KEYWORDS, WATCH_AUTHORS, MAX_PAPERS_PER_KEYWORD

        client = SemanticScholarClient()
        processed_ids = load_cache()

        # 搜索核心关键词
        all_papers = {}
        for kw in CORE_KEYWORDS:
            try:
                results = client.search_papers(kw, limit=MAX_PAPERS_PER_KEYWORD)
                for p in results:
                    pid = p.get("paperId")
                    if pid and pid not in all_papers:
                        all_papers[pid] = p
                time.sleep(1)
            except Exception as e:
                print(f"  ⚠️ 搜索 '{kw}' 失败: {e}")

        # 搜索扩展关键词
        for kw in WATCH_KEYWORDS:
            try:
                results = client.search_papers(kw, limit=MAX_PAPERS_PER_KEYWORD)
                for p in results:
                    pid = p.get("paperId")
                    if pid and pid not in all_papers:
                        all_papers[pid] = p
                time.sleep(1)
            except Exception as e:
                print(f"  ⚠️ 搜索 '{kw}' 失败: {e}")

        papers = list(all_papers.values())
        print(f"✅ 检索到 {len(papers)} 篇论文")

    except Exception as e:
        print(f"❌ paper_tracker 运行失败: {e}")
        papers = []
    finally:
        cfg.DAYS_BACK = original_days_back

    # 2. 运行 author_tracker
    print()
    print("👤 正在追踪作者...")
    author_papers = []
    try:
        if WATCH_AUTHORS:
            for author_name in WATCH_AUTHORS:
                try:
                    results = client.search_authors(author_name, limit=5)
                    if results:
                        author = results[0]
                        author_id = author.get("authorId")
                        if author_id:
                            author_pubs = client.get_author_papers(author_id, limit=20)
                            author_papers.extend(author_pubs)
                            time.sleep(1)
                except Exception as e:
                    print(f"  ⚠️ 追踪 '{author_name}' 失败: {e}")
        print(f"✅ 作者追踪发现 {len(author_papers)} 篇论文")
    except Exception as e:
        print(f"❌ author_tracker 运行失败: {e}")

    # 3. 生成报告
    print()
    print("📝 正在生成报告...")
    markdown_content = generate_report_markdown(date_str, days_back, papers, author_papers)

    # 4. 保存本地
    local_path = save_local_report(date_str, markdown_content)
    print(f"✅ 本地报告: {local_path}")

    # 5. 推送飞书
    if not args.dry_run and not args.output_only:
        print()
        print("📤 正在推送飞书...")

        # 确定推送目标
        receive_id = args.user_open_id
        receive_id_type = "open_id"

        if not receive_id and args.user_email:
            try:
                receive_id = feishu_publisher.get_user_open_id(user_email=args.user_email)
                print(f"✅ 找到用户 open_id: {receive_id}")
            except Exception as e:
                print(f"⚠️ 获取用户 open_id 失败: {e}")
                print("  将使用机器人自身测试...")
                # 使用机器人自身作为测试
                receive_id = None

        # 计算统计
        total_papers = len(papers)
        high_impact = sum(1 for p in papers if p.get("influentialCitationCount", 0) > 5)

        # 创建飞书文档
        doc_title = f"📚 每日科研简报 {date_str}"
        try:
            doc_result = feishu_publisher.create_wiki_node(
                title=doc_title,
                markdown_content=markdown_content
            )
            doc_url = doc_result.get("node_url", doc_result.get("doc_url", ""))
            print(f"✅ 飞书文档: {doc_url}")
        except Exception as e:
            print(f"⚠️ 创建飞书文档失败: {e}")
            doc_url = None

        # 发送消息卡片
        if not receive_id:
            print("⚠️ 未指定推送目标，跳过消息发送")
        else:
            try:
                result = feishu_publisher.send_daily_report_card(
                    receive_id=receive_id,
                    receive_id_type=receive_id_type,
                    date_str=date_str,
                    paper_count=total_papers,
                    high_impact=high_impact,
                    doc_url=doc_url
                )
                print(f"✅ 飞书消息已发送: message_id={result.get('message_id')}")
            except Exception as e:
                print(f"⚠️ 发送飞书消息失败: {e}")

    print()
    print("🎉 完成！")


if __name__ == "__main__":
    main()
