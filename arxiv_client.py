"""
arXiv API Client
搜索arXiv预印本，补充Semantic Scholar
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Optional
import xml.etree.ElementTree as ET

ARXIV_API = "http://export.arxiv.org/api/query"

def search_arxiv(query: str, max_results: int = 20, days_back: int = 1) -> list[dict]:
    """搜索arXiv论文"""
    # 计算日期范围
    if days_back > 0:
        start_date = datetime.now() - timedelta(days=days_back)
        date_from = start_date.strftime("%Y-%m-%d")
        search_query = f"{query}+AND+submittedDate:[{date_from}+TO+*]"
    else:
        search_query = query

    params = {
        "search_query": search_query,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    r = requests.get(ARXIV_API, params=params, timeout=30)
    r.raise_for_status()

    # 解析Atom Feed
    root = ET.fromstring(r.text)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    papers = []
    for entry in root.findall("atom:entry", ns):
        paper = {
            "arxiv_id": entry.find("atom:id", ns).text.split("/")[-1] if entry.find("atom:id", ns) is not None else "",
            "title": entry.find("atom:title", ns).text.replace("\n", " ").strip() if entry.find("atom:title", ns) is not None else "",
            "summary": entry.find("atom:summary", ns).text.replace("\n", " ").strip() if entry.find("atom:summary", ns) is not None else "",
            "published": entry.find("atom:published", ns).text[:10] if entry.find("atom:published", ns) is not None else "",
            "authors": [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns) if a.find("atom:name", ns) is not None],
            "categories": [c.get("term") for c in entry.findall("atom:category", ns)],
            "pdf_url": ""
        }
        # 获取PDF链接
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                paper["pdf_url"] = link.get("href")
                break
        papers.append(paper)

    return papers