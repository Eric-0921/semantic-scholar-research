---
name: paper_tracker
description: Track NV center & quantum sensing papers via Semantic Scholar and arXiv, generate Chinese summaries
metadata:
  {"openclaw": {"requires": {"bins": ["python3"], "env": ["SEMANTIC_SCHOLAR_API_KEY"]}}}
---

# Academic Paper Tracker for NV Center & Quantum Sensing Research

This skill tracks new academic papers on diamond NV centers and quantum sensing from Semantic Scholar and arXiv.

## Capabilities

1. **Daily Paper Tracking** - Monitors new papers via cron, generates Chinese summaries
2. **Literature Review** - Generates structured review for a research topic
3. **Citation Network Analysis** - Builds citation graph from seed papers

## Usage

### Daily Tracking

To check for new papers and generate a daily report:

```
Check for new NV center and quantum sensing papers today
```

This runs `paper_tracker.py` which:
1. Queries Semantic Scholar API for papers on NV center, quantum sensing, diamond magnetometry
2. Queries arXiv for preprints in the same domain
3. Generates Chinese summary for each paper
4. Saves report to `daily_reports/report_YYYY-MM-DD.md`

### Literature Review

To generate a literature review:

```
Generate a literature review on NV center quantum sensing
```

### Citation Network

To analyze citation network of key papers:

```
Analyze the citation network of "Quantum sensing with NV centers in diamond"
```

## Manual Execution

```bash
cd ~/.openclaw/manual_function/sematic\ scholar_api/research_automation

# Daily tracking
python3 paper_tracker.py

# Literature review
python3 literature_review_pipeline.py "NV center quantum sensing"

# Citation network
python3 citation_network.py "Quantum sensing with NV centers"
```

## Output Locations

- Daily reports: `research_automation/daily_reports/report_YYYY-MM-DD.md`
- Literature reviews: `research_automation/output/literature_review_*.md`
- Citation reports: `research_automation/output/network_report.md`
- Cache: `research_automation/output/tracker_cache.json`

## Cron Setup

To set up daily tracking at 8 AM:

```bash
openclaw cron add \
  --name "NV Paper Daily Check" \
  --cron "0 8 * * *" \
  --tz "Asia/Shanghai" \
  --session isolated \
  --message "Run paper tracker for NV center and quantum sensing. Check daily_reports output." \
  --announce \
  --channel telegram
```
