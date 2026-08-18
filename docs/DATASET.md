# 📊 ScamGuard AI Dataset Guide

This document explains how to collect, label, and use data to improve ScamGuard AI.

## Current State

| Source | Volume | Status |
|--------|--------|--------|
| Rule-engine patterns | 300+ keywords | Working |
| Embedding patterns | 15 examples | Too small, needs expansion |
| `scam_dataset.jsonl` | Growing | In progress |
| Database feedback | Growing | In progress |

## Ways To Expand The Dataset

### 1. Bot Feedback
When users mark an analysis as correct or incorrect, those signals can later be reviewed and exported.

Useful tool:
```bash
python tools/analyze_missed_scams.py
```

### 2. Manual Collection
```bash
python tools/collect_scam_examples.py --mode manual
```

### 3. Import From File
Prepare a text file with alternating message and label sections, then import it with the collection tool.

### 4. Public Sources
English scam examples can be collected from public communities such as Reddit scam-reporting forums.

## Priority Collection Areas

Need more examples for:
- tech support scams
- fake delivery scams
- marketplace scams
- crypto scams
- Uzbek bank phishing
- legitimate messages for balance

## Recommended Labels

Examples of useful categories:
- `bank_phishing`
- `loan_scam`
- `fake_prize`
- `bot_scam`
- `investment_scam`
- `job_scam`
- `romance_scam`
- `family_scam`
- `rental_scam`
- `tech_support_scam`
- `legitimate`

## Data Quality Rules
- Keep the original scam wording where possible
- Preserve links, urgency cues, payment requests, and manipulation wording
- Mark legitimate samples carefully to reduce false positives
- Avoid duplicates unless you are intentionally tracking campaign variants

## Target Size

Short term:
- 20+ examples per important scam class

Medium term:
- 200+ labeled examples overall

Long term:
- 1000+ examples for stronger classical ML or transformer-based models
