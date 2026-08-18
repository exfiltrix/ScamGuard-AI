# 🛡 ScamGuard AI - 4-AI Module Architecture

**Version:** 0.3.0  
**Date:** April 11, 2026  
**Status:** Ready for testing

## Concept

ScamGuard AI uses four specialized analysis modules for suspicious message review.

```text
Forwarded message or direct text
        ↓
1. NLP / LLM Analysis (Gemini)
   - context understanding
   - scam type detection
   - manipulation detection

2. Rule Engine
   - deterministic fraud rules
   - prepayment patterns
   - urgency combinations

3. Embedding / Pattern Similarity
   - known scam pattern matching
   - semantic similarity scoring

4. Image Analysis (Gemini Vision)
   - stock photo vs real photo
   - duplicate signals
   - suspicious image quality
```

## Module Weights
- NLP / LLM: 35%
- Rule Engine: 25%
- Embedding Similarity: 20%
- Image Analysis: 20%

## NLP / LLM Module

**File:** `backend/services/gemini_analyzer.py`

Responsibilities:
- understand message meaning
- detect scam category
- identify pressure and manipulation tactics
- extract structured fields
- produce a risk score and explanation

## Rule Engine

**File:** `backend/services/rule_engine.py`

Responsibilities:
- keyword-based red flags
- contact completeness
- payment and urgency combinations
- common phishing and prepayment patterns

## Embedding / Pattern Similarity

**File:** `backend/services/embedding_analyzer.py`

Responsibilities:
- compare input against known scam patterns
- detect repeated or near-duplicate scam scripts
- score similarity against stored examples

## Image Analysis

**File:** `backend/services/image_analyzer.py`

Responsibilities:
- detect suspicious image quality
- detect duplicates or low-information images
- estimate whether images look stock-like or synthetic

## Output

Every module contributes to:
- `risk_score`
- `risk_level`
- `red_flags`
- `recommendations`
- `details`

## Why This Design
- better robustness than using a single model
- explainable output through multiple independent signals
- cheaper quick-path operation
- easier iteration by improving one module at a time
