# 🏗 ScamGuard AI Architecture v0.4.0

## Overview

```text
User (Telegram / Web UI)
        │
        ▼
   FastAPI Server
   backend/api/main.py
        │
  ┌─────┴─────┐
  ▼           ▼
Quick Check  Deep Analysis
(instant)    (8-15 sec)
  └─────┬─────┘
        ▼
FraudDetectionPipeline
backend/services/pipeline.py
        │
  ┌─────┼─────┬────────┬────────┬────────┐
  ▼     ▼     ▼        ▼        ▼
Rule   URL  Context  Gemini   Image
Engine        Check    NLP     Vision
        │
        ▼
Weighted Score + Floor Protection
        ▼
AnalysisResult
```

## Main Modules

### 1. Rule Engine
- Deterministic checks with no paid API calls
- Keyword patterns and severity weights
- Contact checks
- Payment request patterns
- Link and attachment checks
- Account indicators
- Critical combo detectors

### 2. URL Analyzer
- Trusted domain list
- Suspicious TLD detection
- Brand impersonation signals
- Scam keywords in domains
- DNS resolution
- WHOIS age checks
- HTTPS and domain structure checks

### 3. Context Analyzer
- Gemini + Google Search grounding
- Real-world verification of brands and domains
- Fallback HTTP checks when grounding is unavailable
- Structured verdict for links and message context

### 4. Gemini NLP Analyzer
- Message intent analysis
- Scam-type detection
- Manipulation tactic extraction
- Risk scoring and explanation generation

### 5. Image Analyzer
- Photo quality checks
- Duplicate image signals
- Stock-photo style signals
- Vision-based suspiciousness analysis

## Scoring Model

- `rule_engine`
- `url_analysis`
- `context`
- `nlp_llm`
- `embedding`
- `image_analysis`

The final score is a weighted combination of active modules.

### Floor Protection
If a single module detects a strong fraud signal, the final score cannot be pulled down too much by weaker modules.

Examples:
- very high rule-engine score keeps the final result high
- high URL risk keeps the final result out of the safe range
- high context score can force at least a medium or high alert

## Primary Flows

### Telegram message flow
1. User sends a suspicious message, photo, file, or link
2. Bot calls quick analysis
3. User receives immediate risk score and top findings
4. If needed, bot triggers deep AI analysis
5. Results are saved and shown to the user

### Listing URL flow
1. User sends a listing URL
2. Parser extracts listing data
3. Full fraud pipeline runs
4. Result is returned and stored

## Current Architecture Strengths
- Works end to end with Telegram and HTTP API
- Has both instant and deep analysis flows
- Mixes deterministic and AI-based detection
- Produces user-facing advice, not just raw scores

## Current Gaps
- Some legacy listing-oriented docs still describe older flows
- Multilingual support is still incomplete across all bot messages
- Pattern coverage is stronger in Russian than in English or Uzbek
- Large bot file should eventually be split into smaller modules
