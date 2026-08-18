# Copilot Instructions — ScamGuard AI

Purpose: Concise, repository-specific guide for future Copilot sessions.

## Build, Run, and Test

### Setup
```bash
# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements-minimal.txt  # Python 3.14 compatible (no compilation)
```

### Running Services
```bash
# Run API server only
./start-simple.sh
curl http://localhost:8000/health  # verify health
curl http://localhost:8000/docs    # SwaggerUI

# Run Telegram bot only (requires TELEGRAM_BOT_TOKEN in .env)
./start-bot.sh
tail -f logs/bot.log  # monitor startup

# Run both (API + bot)
./start.sh

# Stop all services
./stop.sh
```

**Important:** Startup scripts set PYTHONPATH and create `logs/` directory. Always use these instead of running Python directly.

### Testing
```bash
# Run all tests
pytest tests/

# Run single test file
pytest tests/test_api.py
pytest tests/test_bot.py
pytest tests/test_rule_engine.py

# Run single test function
pytest tests/test_api.py::test_analyze_listing
```

**Note:** Tests mock the pipeline by default. If you need full integration, check how `test_api.py` loads the main module.

### Linting & Formatting
No explicit linting configuration exists. Use standard tools (black, ruff, flake8) as needed locally.

---

## Architecture Overview

### High-Level Design
ScamGuard AI is a **parallel fraud-detection pipeline** with 5+ specialized modules:

```
Input (text + optional photos) 
    ↓
Rule Engine (instant, deterministic)
    ↓ (parallel tasks)
├─ Gemini NLP Analyzer (context, manipulation)
├─ Embedding Analyzer (similarity to known scams)
├─ Image Analyzer (Gemini Vision: stock photos, duplicates)
├─ URL Analyzer (heuristic checks)
└─ Context Analyzer (Google Search + Gemini grounding)
    ↓
Weighted Scoring (sum=1.0, weights in pipeline.py)
    ↓
Output: AnalysisResult (score, flags, confidence)
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **Pipeline Orchestrator** | `backend/services/pipeline.py` | Runs 5 modules in parallel, computes final score |
| **Rule Engine** | `backend/services/rule_engine.py` | Deterministic scam patterns (~62KB database) |
| **Gemini NLP** | `backend/services/gemini_analyzer.py` | Context understanding, LLM-based red flags |
| **Image Analysis** | `backend/services/image_analyzer.py` | Stock photo detection, image quality checks |
| **Embeddings** | `backend/services/embedding_analyzer.py` | Scam pattern similarity, pattern training |
| **Context/Grounding** | `backend/services/context_analyzer.py` | Google Search integration, URL legitimacy |
| **FastAPI Server** | `backend/api/main.py` | REST endpoints, auth, database |
| **Telegram Bot** | `backend/bot/telegram_bot.py` | Telegram FSM (aiogram 3.x), user interactions |
| **Database Models** | `backend/models/database.py` | SQLAlchemy models (Analysis, MessageAnalysis) |
| **Config** | `backend/config.py` | Environment-based settings, API key rotation |

### Data Flow
1. **API request** → FastAPI endpoint (`analyze_message` or `analyze_listing`)
2. **Pipeline methods:**
   - `analyze_message()` — full pipeline for Telegram messages (forwarded or direct)
   - `quick_check()` — rules only (instant, no AI cost)
   - `deep_analyze()` — full AI pipeline after quick check
   - `analyze_listing()` — legacy URL-based analysis
3. **Result** → scored AnalysisResult with RedFlags list
4. **Storage** → SQLAlchemy ORM saves to SQLite (`data/scamguard.db`)

### Database
- **Location:** `data/scamguard.db` (SQLite)
- **Tables:** `analysis`, `message_analysis`, `user` (see `backend/models/database.py`)
- **ORM:** SQLAlchemy with async support (`aiosqlite`)
- **Patterns Database:** `data/scam_patterns.json` (in-memory loaded by EmbeddingAnalyzer)

---

## Key Conventions & Quirks

### Python 3.14 Compatibility
- **Use `backend/requirements-minimal.txt` only** — avoids compiling `pydantic-core`, `lxml`
- `test_server.py` hardcodes the project root path: `sys.path.insert(0, '/home/exfiltrix/Projects/ScamGuard-AI')`
- If imports fail, verify PYTHONPATH includes the project root or use the startup scripts

### PYTHONPATH & Entry Points
- **API server:** `test_server.py` (entry point that sets PYTHONPATH correctly)
- **Telegram bot:** `backend/bot/telegram_bot.py` (requires `PYTHONPATH=$(pwd)`)
- **Always use startup scripts** (`./start-simple.sh`, `./start-bot.sh`) to ensure correct environment setup

### AI Provider & Configuration
- **AI Provider:** Controlled by `AI_PROVIDER` env var (options: `gemini`, `openai`, fallback)
- **Default:** Gemini 1.5 Flash (free tier) via `google-generativeai` package
- **Embedding analysis:** Requires optional `OPENAI_API_KEY` (graceful fallback if missing)

### API Key Rotation (Google Gemini)
- **Config format:** `GOOGLE_API_KEYS=key1,key2,key3` (comma-separated) or `GOOGLE_API_KEY_1`, `GOOGLE_API_KEY_2`, etc.
- **Strategy:** Round-robin rotation via `backend/services/api_key_manager.py`
- **Rate limiting:** 65-second cooldown on 429 errors; 5 keys ≈ 300 requests/minute (Gemini free tier)
- **See:** `.env.example` and `FREE_SETUP.md` for detailed setup

### Async-First Design
- **All major modules use `async/await`** — new endpoints should follow this pattern
- **Pipeline runs modules concurrently** via `asyncio.gather()`
- **Database access:** Use async SQLAlchemy (`AsyncSession`, `aiosqlite`)

### Scoring Weights
- **Location:** `backend/services/pipeline.py`, class `FraudDetectionPipeline.__init__`
- **Structure:** `self.weights = { "rule_engine": 0.25, "gemini": 0.35, ... }` (sum = 1.0)
- **To disable a module:** Set weight to 0 or replace method with stub
- **To tune sensitivity:** Adjust weights or modify module thresholds

### Logging
- **Runtime logs:** `logs/api.log`, `logs/bot.log` (created automatically)
- **Logger:** `loguru` (replaces standard `logging`)
- **Debugging:** Use `tail -f logs/*.log` to monitor live activity

### Pattern Training (Recent Addition)
- **Method:** `EmbeddingAnalyzer.train_new_patterns()` in `backend/services/embedding_analyzer.py`
- **Workflow:** Telegram bot UI → collect examples → extract n-grams → save to `data/scam_patterns.json`
- **Current state:** MVP (heuristic-based). For production: compute embeddings, version control, add approval workflow
- **See:** `docs/TRAIN_PATTERNS.md` for detailed guide

---

## Common Tasks

### Adding a New API Endpoint
1. Add method to `backend/api/main.py` (use `@app.post()` decorator)
2. Use `FraudDetectionPipeline` methods (`analyze_message`, `quick_check`, `deep_analyze`)
3. Return `AnalysisResult` (JSON serialization handled by FastAPI)
4. Add database logging via SQLAlchemy ORM if needed

### Modifying Pipeline Weights
Edit `self.weights` in `backend/services/pipeline.py`:
```python
self.weights = {
    "rule_engine": 0.25,
    "gemini": 0.35,
    "embedding": 0.20,
    "image": 0.10,
    "url": 0.05,
    "context": 0.05,
}
```

### Running Integration Tests
```bash
# Use test_server.py as a runner if direct pytest fails
python test_server.py  # validate imports and startup
pytest tests/ -v       # run full test suite
```

### Debugging Gemini API Issues
1. Check `.env` for valid `GOOGLE_API_KEY_*` or `GOOGLE_API_KEYS`
2. Verify quota at https://console.cloud.google.com/apis/
3. Monitor rotation in logs: `grep "API key rotation\|429" logs/api.log`
4. Check cooldown logic in `backend/services/api_key_manager.py`

---

## Important Files & References

- **Quick Start:** `QUICKSTART.md`, `FREE_SETUP.md`
- **Demo Scenarios:** `docs/TEST_EXAMPLES.md`, `TEAM_CHEATSHEET.md`
- **Architecture Deep Dive:** `docs/PIPELINE_ARCHITECTURE.md`, `docs/ARCHITECTURE.md`
- **Pattern Training:** `docs/TRAIN_PATTERNS.md`, `TRAIN_FEATURE_README.md`
- **Environment Setup:** `.env.example`
- **Agent Rules:** `AGENTS.md` (rules for internal helper agents)

---

## Notes for Future Sessions

- **Status as of April 2026:** MVP with production-style architecture; Telegram bot is primary interface
- **Test coverage:** 3 test files cover API, bot, and rule engine; integration tests mock pipeline
- **Documentation:** Extensive markdown docs in repo root and `docs/` for product features, economics, privacy
- **Deployment:** Docker configs exist (`Dockerfile.api`, `Dockerfile.bot`, `docker-compose.yml`) but may need updates for Python 3.14

---

## MCP Servers Available

### GitHub Integration
The GitHub MCP Server is available for working with this repository. You can use it to:

- **List issues, pull requests, and branches** via `list_issues`, `list_pull_requests`, `list_branches`
- **Search code** for patterns, function names, or imports via `search_code`
- **Read files and commits** via `get_file_contents` and `get_commit`
- **Search across issues, PRs, and users** via targeted search tools

**Common workflows:**
```bash
# Find all open issues related to bot
search_issues("bot", state: "open")

# Search for a specific function in code
search_code("def analyze_message")

# Get file contents from a specific path
get_file_contents("backend/services/pipeline.py")

# List recent commits
list_commits(limit: 10)
```

This is especially useful for:
- Understanding PR history and architectural decisions
- Finding related code across modules
- Investigating how similar problems were solved before
- Checking issue discussions for context on features
