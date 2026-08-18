# ScamGuard AI: Project Deep Dive

**Audit date:** 2026-04-22

This document reflects the actual current codebase, not only legacy presentation material.

## 1. What The Project Is

ScamGuard AI is a fraud-detection system for suspicious messages, links, files, and legacy listing URLs.

Primary operating modes:
1. Telegram bot
2. HTTP API + simple web interface

## 2. What The System Does In Practice

1. User sends text, a forwarded message, a file, a photo, or a link
2. Bot runs quick analysis
3. API evaluates fast fraud signals
4. User gets immediate findings
5. User can trigger deep AI analysis
6. Final result is stored and shown

Outputs include:
- `risk_score`
- `risk_level`
- `red_flags`
- `recommendations`
- `details`

## 3. High-Level Architecture

### Entry points
- `test_server.py`
- `backend/api/main.py`
- `backend/bot/telegram_bot.py`

### Major directories
- `backend/api/`
- `backend/services/`
- `backend/models/`
- `backend/bot/`
- `frontend/`
- `data/`
- `tests/`

## 4. Core Pipeline

Main orchestrator:
- `backend/services/pipeline.py`

Main modules:
- rule engine
- URL analyzer
- context analyzer
- Gemini NLP analyzer
- image analyzer
- embedding analyzer

## 5. Telegram Bot Role

The bot is the primary product interface.

It handles:
- text
- forwarded messages
- files
- photos
- message history and stats
- quick and deep analysis flows

## 6. API Role

FastAPI provides:
- listing analysis
- message quick check
- deep message analysis
- history
- stats
- message retrieval

## 7. Storage

SQLite stores:
- listing analyses
- message analyses
- user metadata

## 8. Product Strengths

- works end to end
- clear quick/deep workflow
- practical risk output
- useful modular architecture
- reasonable MVP economics

## 9. Technical Weaknesses

- large Telegram bot file
- incomplete multilingual coverage
- mixed legacy and current documentation
- uneven pattern coverage across languages
- some naming is older than current behavior

## 10. Recommended Priorities

1. finish documentation cleanup
2. complete multilingual support
3. strengthen link verification
4. expand scam-pattern coverage
5. split the bot into smaller modules

## 11. Key Files

| File | Role |
|------|------|
| `test_server.py` | Local API entry point |
| `backend/api/main.py` | FastAPI app and endpoints |
| `backend/services/pipeline.py` | Main orchestration |
| `backend/services/rule_engine.py` | Deterministic detection |
| `backend/services/gemini_analyzer.py` | NLP analysis |
| `backend/services/context_analyzer.py` | Search-grounded verification |
| `backend/services/url_analyzer.py` | Offline domain checks |
| `backend/services/embedding_analyzer.py` | Pattern similarity |
| `backend/services/image_analyzer.py` | Image checks |
| `backend/bot/telegram_bot.py` | Telegram UX flow |

## 12. Bottom Line

ScamGuard AI is a working anti-fraud MVP with a Telegram-first product flow, a modular backend, and a practical combination of rule-based and AI-assisted detection.

The strongest current direction is suspicious-message analysis, not only legacy listing URL detection.
