---
name: research_team
description: Multi-agent research team for NV center and quantum sensing paper analysis
metadata:
  {"openclaw": {"requires": {"bins": ["python3"]}}}
---

# Research Team - Multi-Agent Paper Analysis

This team coordinates multiple specialized agents to process academic papers efficiently.

## Team Structure

### Coordinator (Main Agent)
- Orchestrates the workflow
- Splits tasks between sub-agents
- Aggregates results

### Sub-Agents

**PaperSearcher** - Searches Semantic Scholar and arXiv for papers
- Uses `semantic_scholar_client.py`
- Uses `arxiv_client.py`

**PaperAnalyzer** - Analyzes individual papers
- Extracts key information
- Scores relevance
- Generates summaries

**ReportWriter** - Compiles results into reports
- Generates markdown reports
- Formats for Telegram delivery

## Usage

When asked to analyze papers:

1. Coordinator receives the request
2. Spawns PaperSearcher to find relevant papers
3. PaperSearcher returns paper list
4. Coordinator spawns multiple PaperAnalyzer agents in parallel (max 3)
5. PaperAnalyzer agents process individual papers
6. Coordinator aggregates results
7. Spawns ReportWriter to generate final report
8. ReportWriter saves to output directory

## Spawn Command

```
/subagents spawn research PaperAnalyzer "Analyze paper: {title} for NV center relevance"
```

## Output

Reports are saved to:
- `research_automation/output/` - Literature reviews and network analyses
- `research_automation/daily_reports/` - Daily paper tracking
