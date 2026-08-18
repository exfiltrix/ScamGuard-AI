# ScamGuard AI — Production Readiness Roadmap

**Current State:** Early Production / Advanced MVP (v0.2.0)  
**Goal:** Enterprise-grade production system (v1.0.0)  
**Timeline Estimate:** 4-6 weeks (intensive), 8-10 weeks (balanced)

---

## 📊 Current Code Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Backend Python files | 23 | 25-30 | ✅ OK |
| Backend LOC | 8,268 | 10,000-12,000 | ✅ OK |
| Test LOC | 666 | 5,000-8,000 | ⚠️ LOW |
| Test functions | 15 | 50-70 | ⚠️ LOW |
| API endpoints | 13 | 14-16 | ✅ OK |
| Pipeline modules | 10 | 6-8 | ✅ OK |
| Documented functions | 65/91 (71%) | 95%+ | ⚠️ NEEDS WORK |
| Docstrings | 65/91 functions | 90%+ | ⚠️ NEEDS WORK |
| print() statements | 13 | 0 | ❌ CRITICAL |
| Committed .env | YES | NO | ❌ CRITICAL |
| CI/CD workflows | NO | YES | ❌ CRITICAL |
| Docker Python version | 3.11 | 3.14 | ❌ CRITICAL |
| Test coverage % | ~8% (estimate) | 80%+ | ❌ CRITICAL |
| Database initialized | NO | YES | ❌ NEEDS SETUP |

---

## 🔴 CRITICAL FIXES (Must Do First)

### 1. Security Issues
- [ ] **Remove committed .env file**
  - [ ] Remove .env from git history: `git filter-branch --tree-filter 'rm -f .env'`
  - [ ] Add .env to .gitignore (already there, but file is committed)
  - [ ] Rotate all API keys (keys are exposed in repo)
  - [ ] Create .env.local for development (never commit)
  - [ ] Generate fresh TELEGRAM_BOT_TOKEN

- [ ] **Remove hardcoded paths in code**
  - [ ] `test_server.py` line: `sys.path.insert(0, '/home/exfiltrix/Projects/ScamGuard-AI')`
  - [ ] Replace with dynamic path resolution: `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`

- [ ] **Audit for secrets in code**
  - [ ] Search for API keys in inline test data
  - [ ] Check git history for exposed credentials
  - [ ] Use `git-secrets` pre-commit hook for future prevention

### 2. Code Quality Issues
- [ ] **Replace print() with logging**
  - Found: 13 instances of print()
  - Replace all with logger.info/debug/error
  - Ensure consistent log levels

- [ ] **Remove wildcard imports**
  - Audit `from X import *` usage
  - Replace with explicit imports

### 3. Python Version Compatibility
- [ ] **Update Dockerfiles to Python 3.14**
  - Change `FROM python:3.11-slim` to `FROM python:3.14-slim`
  - Test build process
  - Update docker-compose.yml accordingly

- [ ] **Fix hardcoded Python path in test_server.py**
  - Use relative/dynamic path instead of absolute

### 4. Database Setup
- [ ] **Initialize database on first run**
  - [ ] Currently database is not created: data/scamguard.db missing
  - [ ] Ensure `init_db()` is called properly on app startup
  - [ ] Add migration system (Alembic) for schema versioning
  - [ ] Test database initialization with fresh instance

---

## 🟡 HIGH PRIORITY (Phase 1: Stabilization)

### 5. Testing & Code Coverage
- [ ] **Expand test suite from 666 LOC to 5,000+ LOC**
  - [ ] Goal: 80%+ code coverage
  - Current files: test_api.py, test_bot.py, test_rule_engine.py

  **Phase 1a: API Tests (Priority)**
  - [ ] Add tests for all 13 API endpoints:
    - [ ] `POST /analyze/listing` (existing: basic)
    - [ ] `GET /user/history` (new)
    - [ ] `GET /user/language` (new)
    - [ ] `POST /user/language` (new)
    - [ ] `POST /feedback` (new)
    - [ ] `GET /stats` (new)
    - [ ] `GET /metrics` (new)
    - [ ] `POST /message/analyze` (new)
    - [ ] `POST /message/analyze/quick` (new)
    - [ ] `POST /message/analyze/deep` (new)
    - [ ] `GET /message/{id}` (new)
    - [ ] `GET /health` (new)

  **Phase 1b: Pipeline Tests**
  - [ ] Test pipeline orchestration with real/mocked modules
  - [ ] Test weight calculations
  - [ ] Test parallel execution
  - [ ] Test error handling and graceful degradation

  **Phase 1c: Service Tests**
  - [ ] Rule engine: test all scam patterns
  - [ ] Gemini analyzer: mock Gemini responses
  - [ ] Image analyzer: test with sample images
  - [ ] Embedding analyzer: test pattern matching
  - [ ] Context analyzer: mock Google Search responses
  - [ ] URL analyzer: test malicious URL detection

  **Phase 1d: Edge Cases**
  - [ ] Empty inputs
  - [ ] Malformed requests
  - [ ] Missing API keys
  - [ ] Database connection failures
  - [ ] Timeout scenarios

  **Phase 1e: Integration Tests**
  - [ ] Full pipeline with real Gemini (if quotas allow)
  - [ ] Bot message flow end-to-end
  - [ ] Database CRUD operations
  - [ ] Async operations

- [ ] **Add pytest configuration**
  - [ ] Create pytest.ini or pyproject.toml with pytest config
  - [ ] Add coverage threshold (80%)
  - [ ] Configure test markers (unit, integration, slow)
  - [ ] Set up parallel test execution

- [ ] **Add test fixtures and factories**
  - [ ] Create fixture for mock pipeline
  - [ ] Create factory for test data (messages, images, users)
  - [ ] Mock external services (Gemini, Google Search, OpenAI)

### 6. Documentation of Code
- [ ] **Add docstrings to all 26 undocumented functions**
  - [ ] Use Google-style docstrings (consistent with existing code)
  - [ ] Include Args, Returns, Raises sections
  - [ ] Add usage examples for complex functions

- [ ] **Add module-level docstrings**
  - [ ] Document purpose of each service module
  - [ ] Add examples of how to use each module

- [ ] **Add type hints to all functions**
  - [ ] Use complete type annotations
  - [ ] Install and configure mypy for type checking
  - [ ] Fix any type violations

### 7. Error Handling & Logging
- [ ] **Improve exception handling**
  - [ ] Add custom exception classes (ScamGuardError, PipelineError, etc.)
  - [ ] Replace generic Exception with specific ones
  - [ ] Add proper error logging context

- [ ] **Structured logging**
  - [ ] Use structured logging (JSON format) for production
  - [ ] Add trace IDs for request tracking
  - [ ] Log all external API calls with duration

- [ ] **API error responses**
  - [ ] Consistent error response format
  - [ ] Add error codes (SCAMGUARD_001, etc.)
  - [ ] Include request ID in errors for debugging

### 8. CI/CD Pipeline Setup
- [ ] **Create GitHub Actions workflows**

  **File: .github/workflows/tests.yml**
  - [ ] Run on PR and push to main
  - [ ] Run tests on Python 3.12, 3.13, 3.14
  - [ ] Generate coverage reports
  - [ ] Fail if coverage drops below 80%
  - [ ] Run linting (ruff/flake8)
  - [ ] Run type checking (mypy)

  **File: .github/workflows/lint.yml**
  - [ ] Run black, ruff, flake8
  - [ ] Check import sorting (isort)
  - [ ] Security scanning (bandit)
  - [ ] Dependency scanning (safety)

  **File: .github/workflows/build.yml**
  - [ ] Build Docker images (API and bot)
  - [ ] Push to registry (if needed)
  - [ ] Test Docker images

  **File: .github/workflows/release.yml**
  - [ ] Semantic versioning
  - [ ] Generate changelog from commits
  - [ ] Create GitHub release
  - [ ] Tag Docker images

- [ ] **Code quality gates**
  - [ ] Integration with tools:
    - [ ] Coverage threshold (80%)
    - [ ] Type checking must pass
    - [ ] Linting must pass
  - [ ] Block merge if gates fail

### 9. Dependency Management
- [ ] **Create requirements.txt in project root**
  - [ ] Aggregate backend dependencies
  - [ ] Pin versions with ~= for compatibility
  - [ ] Document why each dependency is needed

- [ ] **Create requirements-dev.txt**
  - [ ] Testing: pytest, pytest-cov, pytest-asyncio, pytest-mock
  - [ ] Linting: black, ruff, flake8, isort
  - [ ] Type checking: mypy
  - [ ] Security: bandit, safety
  - [ ] Documentation: sphinx, sphinx-rtd-theme

- [ ] **Update Docker requirements**
  - [ ] backend/requirements.txt should have exact versions
  - [ ] backend/requirements-minimal.txt should be reviewed for Python 3.14

- [ ] **Add version constraints**
  - [ ] Minimum Python version: 3.12 (drop 3.11)
  - [ ] Document dependency versions in README

---

## 🟡 HIGH PRIORITY (Phase 2: Features & Deployment)

### 10. Database & Migrations
- [ ] **Implement database migrations with Alembic**
  - [ ] Initialize Alembic: `alembic init migrations`
  - [ ] Create initial migration for current schema
  - [ ] Add migration workflow to CI/CD
  - [ ] Document migration process

- [ ] **Improve database initialization**
  - [ ] Auto-run migrations on app startup
  - [ ] Add seed data for development
  - [ ] Create database reset script for testing

- [ ] **Add database connection pooling**
  - [ ] Configure async SQLAlchemy pool settings
  - [ ] Set pool_size and max_overflow
  - [ ] Add health check queries

### 11. Configuration Management
- [ ] **Implement environment-based configuration**
  - [ ] Create config classes: DevelopmentConfig, TestingConfig, ProductionConfig
  - [ ] Use Pydantic settings with @validation
  - [ ] Add config validation on startup
  - [ ] Document all environment variables

- [ ] **Externalize all hardcoded values**
  - [ ] Move thresholds to config (risk score limits, timeouts, etc.)
  - [ ] Move weights to config file or database
  - [ ] Allow runtime adjustment of weights via admin API

- [ ] **Add secrets management**
  - [ ] Use environment variables for secrets
  - [ ] Consider AWS Secrets Manager / Azure Key Vault for production
  - [ ] Implement secret rotation mechanism

### 12. API Enhancements
- [ ] **Add API authentication**
  - [ ] Implement API key management
  - [ ] Add rate limiting per API key
  - [ ] Add request signing for sensitive endpoints

- [ ] **Improve API documentation**
  - [ ] Add request/response examples to OpenAPI docs
  - [ ] Document all error codes
  - [ ] Add authentication examples

- [ ] **Add API versioning**
  - [ ] Version all endpoints: /api/v1/...
  - [ ] Support multiple API versions for backward compatibility
  - [ ] Deprecation policy for old versions

- [ ] **Add new endpoints**
  - [ ] `GET /api/v1/health/detailed` — detailed health check
  - [ ] `GET /api/v1/admin/weights` — get pipeline weights
  - [ ] `POST /api/v1/admin/weights` — update pipeline weights
  - [ ] `GET /api/v1/admin/logs` — get recent logs
  - [ ] `POST /api/v1/patterns/train` — train new patterns programmatically

### 13. Bot Improvements
- [ ] **Add error recovery in bot**
  - [ ] Graceful handling of Gemini quota exceeded
  - [ ] Retry logic with exponential backoff
  - [ ] User-friendly error messages in Russian/multiple languages

- [ ] **Add bot metrics & analytics**
  - [ ] Track messages analyzed per user
  - [ ] Track accuracy feedback
  - [ ] Generate daily/weekly stats

- [ ] **Improve bot UX**
  - [ ] Add inline buttons for quick actions
  - [ ] Add progress indicators for long operations
  - [ ] Add rich formatting (code blocks, bold, etc.)

### 14. Monitoring & Observability
- [ ] **Add structured logging**
  - [ ] JSON-formatted logs for all services
  - [ ] Correlation IDs for request tracing
  - [ ] Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

- [ ] **Add metrics/monitoring**
  - [ ] Prometheus metrics for:
    - [ ] Request latency (API and bot)
    - [ ] Pipeline module execution time
    - [ ] API key rotation events
    - [ ] Error rates
    - [ ] Database connection pool stats
  - [ ] Export metrics endpoint: `/metrics`

- [ ] **Add health check endpoint**
  - [ ] Check database connectivity
  - [ ] Check Gemini API availability
  - [ ] Check Google Search API availability
  - [ ] Check required files (scam_patterns.json)

- [ ] **Add request tracing**
  - [ ] Correlation IDs for all requests
  - [ ] Trace logging through pipeline
  - [ ] OpenTelemetry integration (optional)

---

## 🟠 MEDIUM PRIORITY (Phase 3: Production Hardening)

### 15. Advanced API Key Management
- [ ] **Improve key rotation system**
  - [ ] Automatic key rotation every N requests
  - [ ] Persistent rotation state (not in memory)
  - [ ] Cooldown after quota exceeded (currently 65s, tune if needed)
  - [ ] Key usage statistics

- [ ] **Add multi-provider support**
  - [ ] Support multiple Gemini instances
  - [ ] Fallback to GPT-4 if Gemini fails
  - [ ] Provider-specific rate limiting

### 16. Performance Optimization
- [ ] **Profile and optimize hot paths**
  - [ ] Profile rule engine (likely bottleneck)
  - [ ] Cache rule engine results
  - [ ] Optimize image analyzer (async image loading)

- [ ] **Add caching**
  - [ ] Cache user language preferences
  - [ ] Cache scam patterns in memory
  - [ ] Cache URL reputation checks (24h TTL)
  - [ ] Redis integration (optional)

- [ ] **Database query optimization**
  - [ ] Add indexes on frequently queried columns
  - [ ] Analyze slow queries
  - [ ] Add query logging to find N+1 problems

- [ ] **API response compression**
  - [ ] Enable gzip compression for large responses
  - [ ] Configure FastAPI compression middleware

### 17. Security Hardening
- [ ] **API security**
  - [ ] Add request size limits
  - [ ] Add timeout for all external API calls
  - [ ] Validate all inputs strictly (no injection attacks)
  - [ ] Add CORS restrictions (don't allow *)
  - [ ] Enable HTTPS in production

- [ ] **Database security**
  - [ ] Add SQL injection protection (already using ORM, good)
  - [ ] Encrypt sensitive data at rest (user feedback, etc.)
  - [ ] Add database access logging

- [ ] **API key security**
  - [ ] Rotate API keys regularly
  - [ ] Never log API keys (audit logs)
  - [ ] Use environment variables only

- [ ] **Dependency security**
  - [ ] Run `pip audit` regularly
  - [ ] Pin transitive dependencies
  - [ ] Set up Dependabot for automatic PRs

### 18. Data Validation & Sanitization
- [ ] **Strengthen input validation**
  - [ ] Add regex/pattern validation for text inputs
  - [ ] Validate image formats and sizes
  - [ ] Validate URL formats
  - [ ] Add length limits for all inputs

- [ ] **Add output sanitization**
  - [ ] Sanitize error messages (don't expose internal details)
  - [ ] HTML escape any user-generated content in responses

### 19. Scalability & Deployment
- [ ] **Containerization**
  - [ ] Update Dockerfiles to Python 3.14
  - [ ] Multi-stage builds for smaller images
  - [ ] Test Docker builds in CI

- [ ] **Kubernetes readiness (optional)**
  - [ ] Add health check probes (liveness, readiness)
  - [ ] Add resource requests/limits
  - [ ] Add graceful shutdown handling
  - [ ] Create K8s manifests (optional)

- [ ] **Database scalability**
  - [ ] Plan for database replication
  - [ ] Add read replicas if needed
  - [ ] Document backup/restore procedures

---

## 🟡 MEDIUM PRIORITY (Phase 4: Operational Excellence)

### 20. Documentation
- [ ] **Consolidate documentation**
  - [ ] Create docs/ structure:
    - [ ] docs/SETUP.md — Development setup
    - [ ] docs/DEPLOYMENT.md — Production deployment
    - [ ] docs/API.md — API reference
    - [ ] docs/BOT.md — Bot documentation
    - [ ] docs/ARCHITECTURE.md — System architecture
    - [ ] docs/CONTRIBUTING.md — Contribution guidelines
  - [ ] Remove duplicate status files (30+ files)
  - [ ] Create CHANGELOG.md with semantic versioning

- [ ] **API documentation**
  - [ ] Add examples for all endpoints
  - [ ] Add curl/Python examples
  - [ ] Document all error responses
  - [ ] Add authentication guide

- [ ] **Developer guide**
  - [ ] Setup instructions
  - [ ] How to add new scam patterns
  - [ ] How to extend pipeline modules
  - [ ] Testing guide
  - [ ] Debugging guide

### 21. Release Management
- [ ] **Create release workflow**
  - [ ] Semantic versioning (MAJOR.MINOR.PATCH)
  - [ ] Automated changelog generation
  - [ ] Automated Docker image tagging
  - [ ] Release notes template

- [ ] **Version management**
  - [ ] Consistent version in: setup.py, __version__.py, docker-compose.yml, docs
  - [ ] Tag all releases in git

### 22. Backup & Disaster Recovery
- [ ] **Database backups**
  - [ ] Automated daily backups
  - [ ] Backup retention policy (30 days)
  - [ ] Test restore procedures monthly

- [ ] **Config backups**
  - [ ] Version control for all configurations
  - [ ] Backup scam_patterns.json

### 23. Compliance & Legal
- [ ] **Privacy & Security**
  - [ ] GDPR compliance review
  - [ ] Data retention policies
  - [ ] User consent for data collection
  - [ ] Encryption at rest and in transit

- [ ] **Terms of Service**
  - [ ] API usage terms
  - [ ] Liability limitations
  - [ ] Data usage policy

---

## 🟢 LOW PRIORITY (Phase 5: Enhancement & Optimization)

### 24. Advanced Features
- [ ] **Pattern training enhancements**
  - [ ] Compute real embeddings instead of n-grams
  - [ ] User voting on pattern accuracy
  - [ ] Admin approval workflow for new patterns
  - [ ] Pattern versioning and rollback

- [ ] **Machine learning improvements**
  - [ ] Fine-tune Gemini prompts
  - [ ] A/B testing framework for different prompts
  - [ ] Feedback loop for continuous improvement
  - [ ] Custom model training (if resources allow)

- [ ] **Analytics & insights**
  - [ ] Dashboard for admin users
  - [ ] Trends in scam types
  - [ ] Geographic analysis
  - [ ] User statistics

### 25. Frontend (Optional)
- [ ] **Admin dashboard**
  - [ ] View system health
  - [ ] Manage pipeline weights
  - [ ] View recent analyses
  - [ ] User management

- [ ] **Web interface for text analysis**
  - [ ] Alternative to Telegram bot
  - [ ] File upload for image analysis
  - [ ] Batch analysis support

### 26. Multi-language Support
- [ ] **Expand language support**
  - [ ] Add language detection
  - [ ] Localize bot responses
  - [ ] Support multiple Telegram bot instances
  - [ ] Region-specific scam patterns

---

## 📋 Implementation Order (Recommended)

### Week 1-2: Critical Fixes + Stabilization
```
1. Remove .env from git history (SECURITY)
2. Fix hardcoded paths (SECURITY)
3. Expand test suite to 2,000 LOC (COVERAGE)
4. Add docstrings to all functions (QUALITY)
5. Replace print() with logging (QUALITY)
6. Setup CI/CD: tests.yml + lint.yml (AUTOMATION)
7. Update Dockerfiles to Python 3.14 (COMPATIBILITY)
```

### Week 3-4: Testing & Quality
```
8. Expand tests to 4,000 LOC (80% coverage goal)
9. Add mypy type checking
10. Configure pytest with coverage gates
11. Add Alembic migrations
12. Improve error handling
13. Add structured logging
```

### Week 5-6: Production Readiness
```
14. Add API authentication/rate limiting
15. Add health checks and metrics
16. Improve configuration management
17. Add request tracing
18. Consolidate documentation
19. Setup release workflow
20. Final security audit
```

---

## 🎯 Success Criteria for v1.0.0

- ✅ 80%+ test coverage
- ✅ All functions documented
- ✅ All endpoints authenticated
- ✅ CI/CD pipeline automated
- ✅ 0 security vulnerabilities
- ✅ Docker images tested and working
- ✅ Database migrations in place
- ✅ Monitoring and logging configured
- ✅ Release process automated
- ✅ Documentation complete and up-to-date
- ✅ Zero hardcoded paths/secrets
- ✅ Graceful error handling
- ✅ Scalable and performant

---

## 📊 Effort Estimation

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| Phase 1 (Stabilization) | 1-9 | 2-3 weeks | CRITICAL |
| Phase 2 (Features) | 10-14 | 2-3 weeks | HIGH |
| Phase 3 (Hardening) | 15-19 | 1-2 weeks | MEDIUM |
| Phase 4 (Operations) | 20-23 | 1 week | MEDIUM |
| Phase 5 (Enhancement) | 24-26 | 2-4 weeks | LOW |

**Total:** 6-10 weeks intensive development

---

## 📝 Notes

- **Parallel work:** Phase 2 and 3 can overlap (weeks 3-4)
- **Testing focus:** Don't skip Phase 1 testing — it's foundation for everything else
- **Security first:** Complete security review before any deployment
- **Database:** Initialize and test database early (currently missing)
- **API keys:** Rotate all keys after fixing .env leak
- **Communication:** Document decisions in ADRs (Architecture Decision Records)

---

## Quick Links to Key Files

- Current API: `backend/api/main.py`
- Pipeline: `backend/services/pipeline.py`
- Tests: `tests/`
- Config: `backend/config.py`, `.env.example`
- Docker: `Dockerfile.api`, `Dockerfile.bot`, `docker-compose.yml`
- Instructions: `.github/copilot-instructions.md`
