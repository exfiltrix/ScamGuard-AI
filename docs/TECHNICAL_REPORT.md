# 📋 ScamGuard AI - Technical Report

**Version:** 0.4.0  
**Date:** April 15, 2026  
**Status:** Production-ready MVP

## Contents
1. System architecture
2. Technology stack
3. Telegram bot
4. Backend API
5. Analysis pipeline
6. Database
7. Schemas
8. Configuration
9. Parsing
10. File and image handling
11. Localization
12. Logging and monitoring
13. Deployment
14. Error handling
15. Known issues

## 1. System Architecture

Main components:
- Telegram bot
- Web UI
- FastAPI backend
- modular fraud pipeline
- SQLite storage
- Gemini-based AI providers

## 2. Technology Stack

- Python
- FastAPI
- aiogram
- SQLAlchemy
- SQLite
- httpx
- Gemini
- Loguru

## 3. Telegram Bot

Responsibilities:
- receive suspicious content
- run quick and deep analysis flows
- show results and reports
- manage user-facing interactions

## 4. Backend API

Main endpoints:
- `/api/v1/analyze`
- `/api/v1/analyze-message-quick`
- `/api/v1/analyze-message-deep`
- `/api/v1/history/{user_id}`
- `/api/v1/stats`

## 5. Analysis Pipeline

Modules:
- rule engine
- URL analyzer
- context analyzer
- Gemini NLP
- embedding similarity
- image analysis

## 6. Database

Core tables:
- `analyses`
- `message_analyses`
- `users`

## 7. Schemas

Important models:
- `AnalysisRequest`
- `AnalysisResult`
- `MessageAnalysisRequest`
- `QuickCheckRequest`
- `DeepAnalysisRequest`

## 8. Configuration

Important settings:
- Telegram bot token
- AI provider
- Google API keys
- OpenAI key for optional components
- database URL

## 9. Parsing

The project supports:
- URL-based listing parsing
- direct message analysis
- photo payload preparation
- file metadata extraction

## 10. File And Image Handling

- risky file extension detection
- document and archive warnings
- image analysis integration
- optional image payload encoding for deep analysis

## 11. Localization

The bot has translation support and is moving toward fuller multilingual coverage.

## 12. Logging And Monitoring

Log files:
- API logs
- bot logs

Health:
- `/health`
- statistics endpoints
- startup database initialization

## 13. Deployment

Supported approaches:
- local Python runtime
- shell scripts
- Docker images
- docker-compose

## 14. Error Handling

Fallbacks include:
- emergency fallback result
- HTTP fallback for context checks
- graceful handling for timeouts and quota exhaustion

## 15. Known Issues

- some legacy documentation still lags behind the code
- the bot file is larger than ideal
- multilingual coverage is incomplete in some older paths
- pattern coverage should be expanded further
