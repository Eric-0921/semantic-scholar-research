#!/usr/bin/env python3
"""
Personalized Paper Recommender using Semantic Scholar Recommendations API

Usage:
    python personalized_recommender.py "paper_title1" "paper_title2" --limit 20
    python personalized_recommender.py --paper-ids paperId1 paperId2 --negative-ids paperId3
    python personalized_recommender.py "attention is all you need" --filter citations --min-citations 100
"""

import argparse
import sys
import os
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from semantic_scholar_client import SemanticScholarClient


def parse_args():
    parser = argparse.ArgumentParser(
        description="Personalized paper recommendations based on seed papers"
    )
    parser.add_argument(
        "paper_titles",
        nargs="*",
        help="Paper titles to use as seeds (will be searched)"
    )
    parser.add_argument(
        "--paper-ids", "-i",
        nargs="+",
        help="Direct paper IDs to use as seeds"
    )
    parser.add_argument(
        "--negative-ids",
        nargs="+",
        help="Paper IDs to exclude from recommendations"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=20,
        help="Number of recommendations (default: 20)"
    )
    parser.add_argument(
        "--filter",
        choices=["citations", "recency", "none"],
        default="none",
        help="Filter criteria: citations (most cited) or recency (newest)"
    )
    parser.add_argument(
        "--min-year",
        type=int,
        help="Minimum publication year"
    )
    parser.add_argument(
        "--min-citations",
        type=int,
        help="Minimum citation count"
    )
    parser.add_argument(
        "--api-key",
        help="Semantic Scholar API key (or set SEMANTIC_SCHOLAR_API_KEY env)"
    )
    return parser.parse_args()


def find_papers_by_title(client: SemanticScholarClient, titles: list[str]) -> list[str]:
    """Search for papers by title and return their IDs."""
    paper_ids = []
    for title in titles:
        print(f"Searching for: {title}")
        results = client.search_papers(title, limit=1)
        if results:
            paper = results[0]
            print(f"  Found: {paper.get('title', 'Unknown')[:60]}... ({paper.get('paperId', '')})")
            paper_ids.append(paper["paperId"])
        else:
            print(f"  Warning: No paper found for '{title}'")
    return paper_ids


def filter_papers(
    papers: list[dict],
    filter_type: str = "none",
    min_year: Optional[int] = None,
    min_citations: Optional[int] = None,
) -> list[dict]:
    """Filter papers by recency, citations, or specified criteria."""
    filtered = papers

    # Apply year filter
    if min_year:
        filtered = [p for p in filtered if p.get("year") and p["year"] >= min_year]

    # Apply citation filter
    if min_citations:
        filtered = [p for p in filtered if p.get("citationCount", 0) >= min_citations]

    # Apply sorting/filtering
    if filter_type == "citations":
        filtered = sorted(filtered, key=lambda x: x.get("citationCount", 0), reverse=True)
    elif filter_type == "recency":
        filtered = sorted(filtered, key=lambda x: x.get("year", 0) or 0, reverse=True)

    return filtered


def format_author_names(authors: list[dict]) -> str:
    """Format authors list as string."""
    if not authors:
        return "Unknown"
    names = [a.get("name", "Unknown") for a in authors[:3]]
    if len(authors) > 3:
        names.append(f"et al.")
    return ", ".join(names)


def generate_report(
    seed_papers: list[dict],
    recommendations: list[dict],
    filter_type: str,
    min_year: Optional[int],
    min_citations: Optional[int],
) -> str:
    """Generate a formatted recommendation report."""
    lines = []
    lines.append("=" * 80)
    lines.append("PERSONALIZED PAPER RECOMMENDATIONS")
    lines.append("=" * 80)
    lines.append("")

    # Seed papers section
    lines.append("SEED PAPERS")
    lines.append("-" * 40)
    for i, paper in enumerate(seed_papers, 1):
        lines.append(f"  {i}. {paper.get('title', 'Unknown')}")
        lines.append(f"     Authors: {format_author_names(paper.get('authors', []))}")
        lines.append(f"     Year: {paper.get('year', 'N/A')} | Citations: {paper.get('citationCount', 'N/A')}")
        lines.append(f"     ID: {paper.get('paperId', '')}")
        lines.append("")

    # Filter info
    filters_applied = []
    if filter_type != "none":
        filters_applied.append(f"sort by {filter_type}")
    if min_year:
        filters_applied.append(f"year >= {min_year}")
    if min_citations:
        filters_applied.append(f"citations >= {min_citations}")

    lines.append(f"Total recommendations: {len(recommendations)}")
    if filters_applied:
        lines.append(f"Filters: {', '.join(filters_applied)}")
    lines.append("")

    # Recommendations section
    lines.append("RECOMMENDED PAPERS")
    lines.append("-" * 40)
    for i, paper in enumerate(recommendations, 1):
        lines.append(f"  {i}. {paper.get('title', 'Unknown')}")
        lines.append(f"     Authors: {format_author_names(paper.get('authors', []))}")
        lines.append(f"     Year: {paper.get('year', 'N/A')} | Citations: {paper.get('citationCount', 'N/A')}")
        if paper.get("externalIds", {}).get("DOI"):
            lines.append(f"     DOI: {paper['externalIds']['DOI']}")
        lines.append(f"     ID: {paper.get('paperId', '')}")
        lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    args = parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    # Initialize client
    client = SemanticScholarClient(api_key=api_key)

    # Get seed paper IDs
    seed_paper_ids = []

    if args.paper_ids:
        seed_paper_ids = args.paper_ids
        print(f"Using provided paper IDs: {seed_paper_ids}")
    elif args.paper_titles:
        seed_paper_ids = find_papers_by_title(client, args.paper_titles)
    else:
        print("Error: Please provide either paper titles or paper IDs")
        sys.exit(1)

    if not seed_paper_ids:
        print("Error: No valid seed papers found")
        sys.exit(1)

    print(f"\nFetching recommendations based on {len(seed_paper_ids)} seed papers...")

    # Get recommendations
    try:
        result = client.get_recommendations(
            positive_paper_ids=seed_paper_ids,
            negative_paper_ids=args.negative_ids,
            limit=args.limit * 2,  # Request more to account for filtering
        )
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        sys.exit(1)

    # Extract recommended papers (exclude seed papers from results)
    recommended = result.get("recommendedPapers", [])
    recommended = [p for p in recommended if p.get("paperId") not in seed_paper_ids]

    print(f"Received {len(recommended)} recommendations")

    # Filter papers
    filtered = filter_papers(
        recommended,
        filter_type=args.filter,
        min_year=args.min_year,
        min_citations=args.min_citations,
    )

    # Limit results
    filtered = filtered[:args.limit]

    # Get seed paper details for the report
    seed_papers = []
    if args.paper_titles:
        # Search again to get full details for seed papers
        for title in args.paper_titles:
            results = client.search_papers(title, limit=1)
            if results:
                seed_papers.append(results[0])

    # Generate and print report
    report = generate_report(
        seed_papers=seed_papers,
        recommendations=filtered,
        filter_type=args.filter,
        min_year=args.min_year,
        min_citations=args.min_citations,
    )
    print("\n" + report)


if __name__ == "__main__":
    main()
