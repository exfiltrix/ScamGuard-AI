# 🧠 Training New Scam Patterns

## Overview

ScamGuard AI can learn from new scam examples so the system can adapt to new fraud scripts.

## Training Methods

### 1. Telegram Bot

Recommended for normal users.

Flow:
1. Open `@ScamGuardAI_bot`
2. Choose **Train on a New Pattern**
3. Send scam text
4. Choose severity
5. Choose scam category
6. Pattern is added

### 2. Programmatic Training

Developers can train patterns directly:

```python
import asyncio
from backend.services.embedding_analyzer import EmbeddingAnalyzer

async def train_scam_patterns():
    analyzer = EmbeddingAnalyzer()
    scam_examples = [
        "Urgent! 100% card prepayment, no viewing",
        "You won an iPhone! Pay only for delivery",
        "Guaranteed income every month with no investment"
    ]
    patterns = await analyzer.train_new_patterns(
        examples=scam_examples,
        severity=9,
        pattern_type="rental_scam"
    )
    print(f"Trained {len(patterns)} new patterns")

asyncio.run(train_scam_patterns())
```

## Severity Levels
- `5` = low
- `7` = medium
- `9` = high

## Good Training Inputs
- real scam messages
- new scam variants
- repeated scam scripts from actual user reports

## Avoid
- generic spam with no fraud
- legitimate offers
- unverified examples

## Goal

Training should improve:
- scam recall
- scam-type matching
- recommendation quality
- resilience against new scam variants
