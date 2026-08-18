# Bot Runtime And UX

## Scope

This document describes the current Telegram bot state after the latest runtime and UX pass.

It covers:
- runtime behavior,
- PID management,
- bot testing,
- current user-facing message style,
- next recommended steps.

## Current Runtime Model

The Telegram bot is started with:

```bash
./start-bot.sh
```

The API is started with:

```bash
./start-simple.sh
```

The bot and API are stopped with:

```bash
./stop.sh
```

### PID ownership

The bot now uses a single PID file:

```text
.bot.pid
```

Important details:
- `backend/bot/telegram_bot.py` owns bot PID-file creation and cleanup.
- `start-bot.sh` no longer races with the bot by writing a competing PID first.
- `stop.sh` removes stale PID files cleanly.
- duplicate start attempts are handled more safely.

## Bot Interaction Flow

### Main user flow

1. User sends or forwards a suspicious message.
2. Bot runs a quick check through `/api/v1/analyze-message-quick`.
3. Bot returns a compact quick-result card.
4. User can trigger deeper analysis with the `Deep AI analysis` button.
5. Bot fetches the saved message via `/api/v1/message/{message_id}`.
6. Bot runs `/api/v1/analyze-message-deep`.
7. Bot returns a more detailed result card with findings and recommendations.

### Supported inputs

- plain text,
- forwarded messages,
- photos,
- files,
- listing URLs.

## UX Copy Direction

The bot message style was updated to be:

- shorter,
- easier to scan,
- less repetitive,
- more structured,
- more suitable for mobile chat UX.

### Updated result patterns

#### Quick result

The quick result now focuses on:
- one risk badge,
- one short risk bar,
- a small number of top findings,
- one short recommendation,
- one clear next action.

#### Detailed result

The detailed result now focuses on:
- verdict,
- why,
- key findings,
- what to do next.

#### File analysis

The file-analysis output was reduced to:
- file summary,
- top risks,
- actions,
- basic safety rules.

## Language Direction

The groundwork for multilingual UI has been added.

Current state:
- Russian remains the default UI language.
- English detection is based on Telegram `language_code`.
- shared translation helpers and menu label translation support are now in place.

This is not yet full bot-wide localization. It is a base layer for finishing English coverage in the remaining commands and callbacks.

## Test Coverage Added

The following bot behaviors are now covered by tests:

- history rendering for message records,
- quick-check request payload and deep-analysis CTA,
- deep-analysis callback flow,
- dangerous file handling.

Run tests with:

```bash
./venv/bin/python -m unittest tests.test_rule_engine tests.test_api tests.test_bot
```

## Verified State

Verified in the current repo state:
- API tests pass,
- rule engine tests pass,
- bot-flow tests pass,
- bot startup script behavior improved,
- stale PID handling improved,
- main result formatting improved.

## Known Gaps

Still pending:
- full English coverage across all bot replies,
- cleanup of `/start`, `/help`, `/stats`, `/logs`, `/history` copy into the same shorter style,
- dispatcher-level integration tests,
- Docker validation,
- broader end-to-end runtime checks with live Telegram interaction.

## Recommended Next Steps

1. Finish English UI coverage for all remaining handlers.
2. Rewrite the remaining command texts in the same compact style.
3. Add tests for `/start`, `/stats`, `/logs`, `/cancel`, and menu callbacks.
4. Add a simple service status script for bot + API runtime inspection.
