# 🔧 ScamGuard AI Developer Guide

## Contents
1. Local development
2. Adding a new scam type
3. Working with the dataset
4. Priority improvements
5. Testing

## 1. Local Development

```bash
# Run API
source venv/bin/activate
PYTHONPATH=. python test_server.py

# Run bot in a separate terminal
PYTHONPATH=. python backend/bot/telegram_bot.py

# View logs
tail -f logs/api.log
tail -f logs/bot.log
```

## 2. Adding a New Scam Type

### Step 1: Add keywords to `rule_engine.py`
Extend the keyword map with new scam-specific phrases and severity scores.

### Step 2: Add combo detection
Add a combo detector when several weaker signals become dangerous together.

### Step 3: Add recommendations in `pipeline.py`
Update `_generate_recommendations()` so the user gets category-specific advice.

### Step 4: Restart and test
Run a quick-check request or send a test message through the bot.

## 3. Working With The Dataset

Useful tools:
```bash
python tools/collect_scam_examples.py --mode manual
python tools/analyze_missed_scams.py
python tools/dataset_to_patterns.py
```

## 4. Priority Improvements

### Critical
- expand rule-engine coverage
- improve Uzbek and English coverage
- increase trusted-domain coverage
- expand pattern database

### Important
- collect real user feedback
- add a simple ML classifier after enough data exists
- cache URL-analysis results

### Nice To Have
- multilingual transformer support
- external phishing feeds
- deeper Telegram channel and account analysis

## 5. Testing

### API Testing
```bash
curl -X POST http://localhost:8000/api/v1/analyze-message-quick \
  -H "Content-Type: application/json" \
  -d '{"text": "TEST MESSAGE", "user_id": 1}'
```

### What To Test
- obvious phishing
- fake prize scams
- loan scams
- suspicious investment offers
- clearly legitimate examples

### Success Criteria
- high-risk samples should score high
- legitimate samples should stay low
- recommendations should match the detected scam type
