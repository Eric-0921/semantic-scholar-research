"""
Author Tracker for Semantic Scholar
Track specific authors' new papers and generate reports
Usage: python author_tracker.py "Author Name" --days 30
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from semantic_scholar_client import SemanticScholarClient
from config import (
    SEMANTIC_SCHOLAR_API_KEY,
    WATCH_AUTHORS as DEFAULT_AUTHORS,
    OUTPUT_DIR,
    DAILY_REPORTS_DIR,
    DAYS_BACK as DEFAULT_DAYS_BACK,
)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Track specific authors' papers from Semantic Scholar"
    )
    parser.add_argument(
        "authors",
        nargs="*",
        help="Author names to track (if not provided, uses WATCH_AUTHORS from config)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS_BACK,
        help=f"Number of days back to search (default: {DEFAULT_DAYS_BACK})"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )
    return parser.parse_args()


def load_cache(cache_file: Path) -> dict:
    """Load processed papers cache"""
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    return {"processed_papers": {}, "last_run": None}


def save_cache(cache_file: Path, cache_data: dict):
    """Save processed papers cache"""
    cache_data["last_run"] = datetime.now().isoformat()
    with open(cache_file, "w") as f:
        json.dump(cache_data, f, indent=2)


def search_author(client: SemanticScholarClient, author_name: str) -> Optional[dict]:
    """Search for an author by name"""
    print(f"  Searching for author: {author_name}")
    try:
        authors = client.search_authors(author_name, limit=5)
        if not authors:
            print(f"    No author found: {author_name}")
            return None

        # Return the first/best match
        author = authors[0]
        print(f"    Found: {author.get('name')} (ID: {author.get('authorId')})")
        return author
    except Exception as e:
        print(f"    Error searching author {author_name}: {e}")
        return None


def get_author_recent_papers(
    client: SemanticScholarClient,
    author_id: str,
    author_name: str,
    days_back: int
) -> List[dict]:
    """Get recent papers for an author within specified days"""
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    year_start = int(date_from[:4])

    print(f"    Fetching papers from {year_start} onwards...")
    try:
        papers = client.get_author_papers(
            author_id,
            limit=50,
            year_start=year_start,
            fields="paperId,title,abstract,tldr,year,citationCount,influentialCitationCount,authors,publicationDate,openAccessPdf,externalIds,fieldsOfStudy,venue"
        )

        # Filter by actual date if available
        filtered_papers = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        for p in papers:
            pub_date_str = p.get("publicationDate", "")
            if pub_date_str:
                try:
                    pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d")
                    if pub_date >= cutoff_date:
                        filtered_papers.append(p)
                except ValueError:
                    # If date parsing fails, include the paper based on year
                    paper_year = p.get("year", 0)
                    if paper_year and paper_year >= cutoff_date.year:
                        filtered_papers.append(p)
            else:
                # No date info, rely on year filter
                filtered_papers.append(p)

        print(f"    Found {len(filtered_papers)} recent papers")
        return filtered_papers

    except Exception as e:
        print(f"    Error fetching papers for {author_name}: {e}")
        return []


def generate_markdown_report(
    all_papers: List[dict],
    authors: List[str],
    days_back: int,
    date_str: str
) -> str:
    """Generate markdown report of tracked papers"""
    # Sort by citation count
    papers = sorted(all_papers, key=lambda x: x.get("citationCount", 0), reverse=True)

    lines = [
        f"# Author Tracking Report\n",
        f"**Date**: {date_str}\n",
        f"**Authors Tracked**: {', '.join(authors)}\n",
        f"**Time Window**: Last {days_back} days\n",
        f"**Total Papers**: {len(papers)}\n",
        "\n---\n\n"
    ]

    if not papers:
        lines.append("*No new papers found in the specified time window.*\n")
        return "".join(lines)

    # Group by author for better organization
    author_papers = {}
    for p in papers:
        paper_authors = p.get("authors", [])
        if paper_authors:
            first_author = paper_authors[0].get("name", "Unknown")
        else:
            first_author = "Unknown"

        if first_author not in author_papers:
            author_papers[first_author] = []
        author_papers[first_author].append(p)

    # Report per author
    for author_name, author_paper_list in author_papers.items():
        lines.append(f"## {author_name}\n")
        lines.append(f"*Total: {len(author_paper_list)} papers*\n\n")

        for i, p in enumerate(author_paper_list, 1):
            citations = p.get("citationCount", 0)
            influential = p.get("influentialCitationCount", 0)
            impact_marker = " [HIGH IMPACT]" if influential > 5 else ""

            title = p.get("title", "N/A")
            year = p.get("year", "N/A")
            venue = p.get("venue", "")
            paper_id = p.get("paperId", "")
            s2_link = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""

            pdf_link = ""
            if p.get("openAccessPdf"):
                pdf_url = p.get("openAccessPdf", {}).get("url", "")
                if pdf_url:
                    pdf_link = f" [[PDF]]({pdf_url})"

            # Get summary
            tldr = p.get("tldr", {})
            tldr_text = tldr.get("text", "") if isinstance(tldr, dict) else ""
            if tldr_text:
                summary = tldr_text
            else:
                abstract = p.get("abstract", "")
                summary = f"{abstract[:300]}..." if abstract else "No abstract available."

            lines.append(f"### {i}. {title}\n")
            lines.append(f"**Year**: {year}")
            if venue:
                lines.append(f" | **Venue**: {venue}")
            lines.append(f" | **Citations**: {citations}{impact_marker}\n\n")

            if s2_link:
                lines.append(f"**Link**: [[Semantic Scholar]]({s2_link}){pdf_link}\n")

            lines.append(f"\n>{summary}\n\n")
            lines.append("---\n\n")

    return "".join(lines)


def track_authors(
    client: SemanticScholarClient,
    author_names: List[str],
    days_back: int,
    output_dir: Path
) -> tuple[List[dict], dict]:
    """Track authors and return papers and cache data"""
    all_papers = []
    cache_data = load_cache(output_dir / "author_tracker_cache.json")
    processed_papers = cache_data.get("processed_papers", {})

    for author_name in author_names:
        if not author_name.strip():
            continue

        print(f"\n[Tracking: {author_name}]")

        # Search for author
        author = search_author(client, author_name)
        if not author:
            continue

        author_id = author.get("authorId")
        if not author_id:
            continue

        # Get recent papers
        papers = get_author_recent_papers(client, author_id, author_name, days_back)

        # Filter out already processed papers
        new_papers = []
        for p in papers:
            paper_id = p.get("paperId")
            if paper_id and paper_id not in processed_papers:
                new_papers.append(p)
                processed_papers[paper_id] = {
                    "title": p.get("title", ""),
                    "author": author_name,
                    "tracked_at": datetime.now().isoformat()
                }

        if new_papers:
            print(f"    {len(new_papers)} new papers found")
            all_papers.extend(new_papers)
        else:
            print(f"    No new papers")

        # Rate limiting
        time.sleep(1)

    return all_papers, cache_data


def main():
    """Main entry point"""
    args = parse_args()

    # Determine authors to track
    authors = args.authors if args.authors else DEFAULT_AUTHORS
    if not authors:
        print("Error: No authors specified and WATCH_AUTHORS is empty in config.py")
        print("Usage: python author_tracker.py \"Author Name\" --days 30")
        sys.exit(1)

    days_back = args.days
    output_dir = args.output_dir

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=" * 60)
    print(f"Author Tracker")
    print(f"=" * 60)
    print(f"Authors: {', '.join(authors)}")
    print(f"Days back: {days_back}")
    print(f"Output directory: {output_dir}")
    print(f"=" * 60)

    # Initialize client
    client = SemanticScholarClient(SEMANTIC_SCHOLAR_API_KEY)

    # Track authors
    all_papers, cache_data = track_authors(client, authors, days_back, output_dir)

    print(f"\n{'=' * 60}")
    print(f"Results: Found {len(all_papers)} new papers")
    print(f"{'=' * 60}")

    if not all_papers:
        print("\nNo new papers found.")
        # Still save cache to mark processed papers
        save_cache(output_dir / "author_tracker_cache.json", cache_data)
        return

    # Generate and save markdown report
    date_str = datetime.now().strftime("%Y-%m-%d")
    report = generate_markdown_report(all_papers, authors, days_back, date_str)

    report_path = output_dir / f"author_report_{date_str}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved: {report_path}")

    # Save JSON data
    json_path = output_dir / f"author_data_{date_str}.json"
    json_data = {
        "date": date_str,
        "authors_tracked": authors,
        "days_back": days_back,
        "papers": all_papers
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, f, indent=2)
    print(f"JSON data saved: {json_path}")

    # Update cache
    save_cache(output_dir / "author_tracker_cache.json", cache_data)
    print(f"Cache updated")


if __name__ == "__main__":
    main()
