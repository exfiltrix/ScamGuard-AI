# 📊 ScamGuard AI Pipeline Architecture

## Multi-Layer Fraud Detection

ScamGuard AI uses a layered detection pipeline to improve accuracy and explainability.

```text
Input
  ├─ listing URL
  ├─ message text
  ├─ forwarded message
  ├─ photo
  └─ file
        ↓
Fraud Detection Pipeline
  ├─ Rule Engine
  ├─ Image Analysis
  ├─ Embedding / Pattern Similarity
  ├─ AI / LLM Analysis
  └─ Context / URL Checks
        ↓
Weighted Scoring Engine
        ↓
AnalysisResult
```

## Module Roles

### Rule Engine
- fast deterministic checks
- keyword and combo logic
- no paid API dependency

### Image Analysis
- photo quality
- duplicate signals
- suspicious visual characteristics

### Embedding / Pattern Similarity
- pattern matching against known scams
- duplicate or near-duplicate message detection

### AI / LLM Analysis
- deep contextual reasoning
- scam-type inference
- explanation generation

### Context / URL Checks
- link legitimacy
- brand and organization verification
- search-grounded or HTTP fallback validation

## Scoring

Each module contributes a score between 0 and 100.

The final result includes:
- weighted score
- risk level
- red flags
- recommendations

### Floor Protection
Strong signals from one module can force the final result to remain elevated.

## Quick vs Deep Analysis

### Quick Check
- fast path
- lower cost
- suitable for immediate user feedback

### Deep Analysis
- slower but more thorough
- uses richer AI reasoning
- combines more modules

## Why This Pipeline Works
- avoids dependence on one model
- balances speed and depth
- keeps explanation quality high
- makes it easier to improve one area without rewriting the whole system
