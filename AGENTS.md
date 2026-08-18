# ScamGuard AI — Agent Instructions

## Quick Start Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements-minimal.txt  # Use minimal for Python 3.14 compatibility

# Run API server
./start-simple.sh  # Uses test_server.py with correct PYTHONPATH
curl http://localhost:8000/health

# Run Telegram bot
./start-bot.sh     # Sets PYTHONPATH=$(pwd), writes .bot.pid
# Bot username: @ScamGuardAI_bot

# Stop services
./stop.sh
pkill -f test_server.py && pkill -f telegram_bot.py

# Run tests
pytest tests/                              # all tests
pytest tests/test_api.py::test_name        # specific test
```

## Architecture

- **Entry point (API):** `test_server.py` — sets PYTHONPATH, imports from `backend/`
- **Entry point (Bot):** `backend/bot/telegram_bot.py` — requires `PYTHONPATH=$(pwd)`
- **Orchestrator:** `backend/services/pipeline.py` — 6 modules run in parallel/asyncio
- **Pipeline modules:** `rule_engine`, `url_analyzer`, `context_analyzer`, `image_analyzer`, `embedding_analyzer`, `gemini_analyzer`
- **Weights:** defined in `pipeline.py` `self.weights` dict, sum=1.0
- **Database:** SQLite at `data/scamguard.db` (SQLAlchemy models in `backend/models/database.py`)

## Critical Quirks

### Python 3.14 Compatibility
- Use `backend/requirements-minimal.txt` only — avoids compilation of `pydantic-core`, `lxml`
- `test_server.py` hardcodes project root: `sys.path.insert(0, '/home/exfiltrix/Projects/ScamGuard-AI')`
- If imports fail, check PYTHONPATH includes project root

### API Key Rotation
- `GOOGLE_API_KEYS=key1,key2,key3` — comma-separated in `.env`
- Or use `GOOGLE_API_KEY_1`, `GOOGLE_API_KEY_2`, etc.
- Round-robin rotation + 65s cooldown on 429 errors (see `backend/services/api_key_manager.py`)
- 5 keys ≈ 300 requests/minute (Gemini free tier)

### AI Provider
- `AI_PROVIDER=gemini` — default, uses Google Gemini 1.5 Flash (free)
- Embedding analysis requires `OPENAI_API_KEY` (optional, graceful fallback)

## Pipeline Methods

```python
# For forwarded Telegram messages (primary bot workflow)
await pipeline.analyze_message(text, photos, is_forwarded, forward_info)

# Quick check (rules only, instant, no AI cost)
await pipeline.quick_check(text, has_photos)

# Deep analysis (full AI pipeline)
await pipeline.deep_analyze(text, photos, is_forwarded, quick_result)

# URL-based analysis (legacy)
await pipeline.analyze_listing(listing)
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/services/pipeline.py` | Main orchestrator, scoring weights |
| `backend/services/rule_engine.py` | 62KB, deterministic scam patterns |
| `backend/services/gemini_analyzer.py` | Gemini NLP analysis |
| `backend/services/context_analyzer.py` | URL grounding via Google Search |
| `backend/bot/telegram_bot.py` | Telegram bot (aiogram 3.x FSM) |
| `.env` | API keys, AI provider, rate limits |

## Logging

- API logs: `logs/api.log`
- Bot logs: `logs/bot.log`
- Use `tail -f logs/*.log` for debugging

## Training New Patterns

```python
# In embedding_analyzer.py
await embedding_analyzer.train_new_patterns(
    examples=["scam text 1", "scam text 2"],
    severity=7,  # 5=low, 7=medium, 9=high
    pattern_type="rental_scam"  # or investment_scam, phishing, etc.
)
# Saves to data/scam_patterns.json
```

## References

- Full launch commands: `QUICKSTART.md`, `FREE_SETUP.md`
- Demo scripts: `docs/TEST_EXAMPLES.md`
- Architecture: `docs/PIPELINE_ARCHITECTURE.md`
- Extended bot/pipeline docs: `.github/copilot-instructions.md`
