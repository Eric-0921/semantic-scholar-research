"""
Semantic Scholar API Client
支持搜索、批量获取论文详情、引用网络
带有指数退避重试机制
"""
import requests
import time
import json
from typing import Optional, List

S2_BASE = "https://api.semanticscholar.org/graph/v1"
S2_RECO_BASE = "https://www.semanticscholar.org/recommendations/v1"
RETRIES_MAX = 5

class SemanticScholarClient:
    def __init__(self, api_key: Optional[str] = None):
        self.headers = {"x-api-key": api_key} if api_key else {}

    def _fetch_with_retry(self, url: str, params: dict = None, method: str = "GET", json_body: dict = None) -> dict:
        """带指数退避的请求"""
        for attempt in range(RETRIES_MAX):
            try:
                if method == "POST":
                    r = requests.post(url, params=params, json=json_body, headers=self.headers, timeout=30)
                else:
                    r = requests.get(url, params=params, headers=self.headers, timeout=30)

                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 429:
                    # 速率限制，等待后重试
                    wait_time = 2 ** attempt
                    print(f"  Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif r.status_code == 400:
                    # 可能是字段不支持，尝试简化
                    error = r.json().get("error", "")
                    if "Unrecognized or unsupported fields" in error:
                        raise ValueError(f"API error: {error}")
                    time.sleep(1)
                else:
                    raise Exception(f"API error {r.status_code}: {r.text[:200]}")
            except requests.exceptions.Timeout:
                time.sleep(2 ** attempt)
                continue
        raise Exception("Max retries exceeded")

    def search_papers(
        self,
        query: str,
        limit: int = 20,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        fields: str = "paperId,title,abstract,tldr,year,citationCount,influentialCitationCount,authors,venue,publicationDate,openAccessPdf,externalIds,fieldsOfStudy",
        venue: Optional[str] = None,
        min_citation_count: Optional[int] = None,
    ) -> list[dict]:
        """搜索论文"""
        params = {
            "query": query,
            "limit": min(limit, 100),  # search 最多 100
            "fields": fields,
        }
        if year_start:
            if year_end:
                params["year"] = f"{year_start}-{year_end}"
            else:
                params["publicationDateOrYear"] = f"{year_start}-"
        if venue:
            params["venue"] = venue
        if min_citation_count:
            params["minCitationCount"] = min_citation_count

        data = self._fetch_with_retry(f"{S2_BASE}/paper/search", params)
        return data.get("data", [])

    def search_papers_bulk(
        self,
        query: str,
        limit: int = 1000,
        sort: str = "publicationDate:desc",
        fields: str = "paperId,title,year,citationCount,influentialCitationCount,authors,venue",
    ) -> list[dict]:
        """Bulk 搜索论文（可获取更多结果）"""
        all_papers = []
        next_token = None

        while len(all_papers) < limit:
            batch_size = min(1000, limit - len(all_papers))
            params = {
                "query": query,
                "limit": batch_size,
                "sort": sort,
                "fields": fields,
            }
            if next_token:
                params["token"] = next_token

            data = self._fetch_with_retry(f"{S2_BASE}/paper/search/bulk", params)
            papers = data.get("data", [])
            all_papers.extend(papers)

            next_token = data.get("token")
            if not next_token or not papers:
                break

            time.sleep(1)  # 遵守速率限制

        return all_papers[:limit]

    def get_paper(self, paper_id: str, fields: Optional[str] = None) -> dict:
        """获取单篇论文详情"""
        if fields is None:
            fields = "paperId,title,abstract,tldr,year,citationCount,authors,venue,openAccessPdf,externalIds,references,citations"
        r = requests.get(f"{S2_BASE}/paper/{paper_id}", params={"fields": fields}, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def get_paper_citations(self, paper_id: str, limit: int = 50) -> list[dict]:
        """获取论文引用（谁引用了这篇）"""
        r = requests.get(
            f"{S2_BASE}/paper/{paper_id}/citations",
            params={"fields": "paperId,title,year,citationCount,authors", "limit": limit},
            headers=self.headers
        )
        if r.status_code != 200:
            return []
        return [item.get("citingPaper", {}) for item in r.json().get("data", []) if item.get("citingPaper")]

    def get_paper_references(self, paper_id: str, limit: int = 50) -> list[dict]:
        """获取论文参考文献（这篇引用了谁）"""
        r = requests.get(
            f"{S2_BASE}/paper/{paper_id}/references",
            params={"fields": "paperId,title,year,citationCount,authors", "limit": limit},
            headers=self.headers
        )
        if r.status_code != 200:
            return []
        return [item.get("citedPaper", {}) for item in r.json().get("data", []) if item.get("citedPaper")]

    def batch_get_papers(self, paper_ids: list[str], fields: str = "paperId,title,abstract,tldr,year,citationCount,influentialCitationCount,authors,venue,externalIds") -> list[dict]:
        """批量获取论文（最多500篇/次）"""
        if not paper_ids:
            return []
        if not self.headers.get("x-api-key"):
            return []

        results = []
        batch_size = 500
        for i in range(0, len(paper_ids), batch_size):
            batch = paper_ids[i:i+batch_size]
            data = self._fetch_with_retry(
                f"{S2_BASE}/paper/batch",
                params={"fields": fields},
                method="POST",
                json_body={"ids": batch}
            )
            results.extend(data.get("data", []))
            time.sleep(1)  # 遵守速率限制

        return results

    def get_paper_citations_with_context(
        self,
        paper_id: str,
        limit: int = 100,
        fields: str = "paperId,title,year,citationCount,authors,contexts,isInfluential"
    ) -> list[dict]:
        """获取论文引用，包含引用上下文和影响力标记"""
        all_citations = []
        offset = 0

        while len(all_citations) < limit:
            batch_size = min(1000, limit - len(all_citations))
            params = {
                "fields": fields,
                "limit": batch_size,
                "offset": offset
            }
            data = self._fetch_with_retry(f"{S2_BASE}/paper/{paper_id}/citations", params)
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                citing = item.get("citingPaper", {})
                if citing:
                    citing["contexts"] = item.get("contexts", [])
                    citing["isInfluential"] = item.get("isInfluential", False)
                    all_citations.append(citing)

            offset += len(items)
            if len(items) < batch_size:
                break
            time.sleep(1)

        return all_citations[:limit]

    # ============ Author API ============

    def search_authors(self, query: str, limit: int = 10) -> list[dict]:
        """搜索作者"""
        params = {
            "query": query,
            "limit": min(limit, 1000),
            "fields": "authorId,name,aliases,affiliations,paperCount,citationCount,hIndex"
        }
        data = self._fetch_with_retry(f"{S2_BASE}/author/search", params)
        return data.get("data", [])

    def get_author(self, author_id: str, fields: str = "authorId,name,aliases,affiliations,paperCount,citationCount,hIndex,papers.title,papers.year,papers.citationCount") -> dict:
        """获取作者详情"""
        params = {"fields": fields}
        return self._fetch_with_retry(f"{S2_BASE}/author/{author_id}", params)

    def get_author_papers(
        self,
        author_id: str,
        limit: int = 100,
        year_start: Optional[int] = None,
        fields: str = "paperId,title,year,citationCount,influentialCitationCount,venue,tldr"
    ) -> list[dict]:
        """获取作者的论文列表"""
        params = {
            "limit": min(limit, 1000),
            "fields": fields,
        }
        if year_start:
            params["publicationDateOrYear"] = f"{year_start}-"

        data = self._fetch_with_retry(f"{S2_BASE}/author/{author_id}/papers", params)
        return data.get("data", [])

    def batch_get_authors(self, author_ids: list[str], fields: str = "authorId,name,hIndex,citationCount,paperCount") -> list[dict]:
        """批量获取作者（最多1000个/次）"""
        if not author_ids:
            return []
        if not self.headers.get("x-api-key"):
            return []

        results = []
        batch_size = 1000
        for i in range(0, len(author_ids), batch_size):
            batch = author_ids[i:i+batch_size]
            data = self._fetch_with_retry(
                f"{S2_BASE}/author/batch",
                params={"fields": fields},
                method="POST",
                json_body={"ids": batch}
            )
            results.extend(data.get("data", []))
            time.sleep(1)

        return results

    # ============ Recommendations API ============

    def get_recommendations(
        self,
        positive_paper_ids: list[str],
        negative_paper_ids: list[str] = None,
        fields: str = "paperId,title,abstract,year,citationCount,influentialCitationCount,authors,venue,publicationDate,externalIds",
        limit: int = 20,
    ) -> dict:
        """
        获取个性化论文推荐

        Args:
            positive_paper_ids: 种子论文ID列表（喜欢的/感兴趣的）
            negative_paper_ids: 负样本论文ID列表（不感兴趣的，可选）
            fields: 返回字段
            limit: 推荐数量上限

        Returns:
            包含 recommendedPapers 和 unlabelledPapers 的字典
        """
        if not positive_paper_ids:
            raise ValueError("positive_paper_ids cannot be empty")

        json_body = {
            "positivePaperIds": positive_paper_ids,
            "limit": min(limit, 100),
            "fields": fields,
        }
        if negative_paper_ids:
            json_body["negativePaperIds"] = negative_paper_ids

        return self._fetch_with_retry(
            f"{S2_RECO_BASE}/papers",
            method="POST",
            json_body=json_body,
        )