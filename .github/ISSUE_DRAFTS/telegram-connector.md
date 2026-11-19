---
title: "Community: Add Telegram Connector for Saved Searches"
labels: good first issue, help wanted
---

## Overview

Add a Telegram connector that answers a saved property search from a Telegram chat. The
user saves a search in the web app, sends `/search <id>` (or a plain question) to the
bot, and the bot answers with the same result the web app shows - through the same
backend, the same agent and the same saved-search store.

This is a **contribution path**, not a new product surface. Everything the connector
needs already exists in the repository: the saved-search store, the chat/agent path, the
MCP connector pattern and its registry. What is missing is the Telegram transport.

## Skills Required

- [x] Python (async, FastAPI)
- [ ] TypeScript/React
- [x] Testing (pytest)

## Architecture Context

This connector follows the `MCPConnector[T]` abstract base class pattern. It should:

1. Extend `MCPConnector` from `apps/api/mcp/base.py` and implement the four abstract
   methods: `connect()`, `disconnect()`, `health_check()`, `execute()`
2. Carry its own config dataclass (the `ScraperTarget` pattern in
   `apps/api/mcp/connectors/web_scraper.py` shows how a connector extends
   `MCPConnectorConfig`)
3. Register with the `@register_mcp_connector` decorator from
   `apps/api/mcp/registry.py` and export the class from
   `apps/api/mcp/connectors/__init__.py`
4. Add an entry to `apps/api/config/mcp_allowlist.yaml` under the `allowlist:` list with
   `edition: community`

Reference implementation: `apps/api/mcp/connectors/web_scraper.py` - it is the only
full connector in the repository today and it shows the whole pattern: the config
dataclass, the rate limiter (`mcp/rate_limiter.py`), the typed result
(`mcp/result.py`), the redacting logger (`core/security_utils.sanitize_for_log`) and
the error types (`mcp/exceptions.py`).

The answer itself is **not** re-implemented. The connector resolves a saved search
through `apps/api/api/routers/saved_searches.py`, reuses the same agent path the web
app uses (`apps/api/api/routers/chat.py`), and only the transport is new. A Telegram
update is received on a small webhook route in `apps/api/api/routers/`, which hands
the resolved query to the connector.

### What this issue does NOT ask for

Stated up front, so nobody builds the wrong thing:

- **No bot that acts as the user.** The bot is a bot - it uses the Bot API with the
  project's own bot token. No userbot, no account automation, no reading or sending
  as a human account.
- **No message storage.** Nothing about a Telegram conversation is persisted beyond
  the saved search the user already has in the product. The message body is used to
  answer and is not kept.
- **No new search engine, no new agent, no new LLM provider.** The existing search
  and the existing agent answer.
- **No change to the plan tiers or the pricing.** The connector is registered in the
  community edition, like the other allowlisted connectors.

## Expected Operations

- `send_message` - Send the answer for a resolved saved search to a Telegram chat
- `send_batch` - Send one answer to several chats at once (a saved search that several
  users watch)
- `verify_connection` - Verify the bot token and the webhook secret are valid

## Acceptance Criteria

- [ ] Connector class extends `MCPConnector` with a Telegram-specific config dataclass
- [ ] `connect()` validates the bot token and the webhook secret and fails cleanly
      when either is missing
- [ ] `execute("send_message", ...)` sends the resolved answer to one chat
- [ ] `execute("send_batch", ...)` sends to several chats with rate limiting
- [ ] `health_check()` verifies the Telegram Bot API is reachable
- [ ] The webhook route resolves the saved search through
      `apps/api/api/routers/saved_searches.py` and reuses the chat/agent path rather
      than re-implementing the answer
- [ ] No Telegram message body is persisted beyond the saved search
- [ ] Registered via `@register_mcp_connector` and exported from
      `apps/api/mcp/connectors/__init__.py`
- [ ] Registered in `mcp_allowlist.yaml` under `allowlist:` with `edition: community`
- [ ] Unit tests in `apps/api/tests/unit/mcp/connectors/test_telegram_connector.py`
- [ ] Handles rate limits and retries gracefully

## Getting Started

1. Fork and clone the repository
2. Review `apps/api/mcp/base.py` for the ABC interface and
   `apps/api/mcp/connectors/web_scraper.py` as the reference implementation
3. Create the first slice - a `TelegramConfig` dataclass and
   `class TelegramConnector(MCPConnector)` with `connect()` validating the bot token
   and the webhook secret - together with a failing unit test at
   `apps/api/tests/unit/mcp/connectors/test_telegram_connector.py`
4. Create branch: `git checkout -b feature/telegram-connector`
5. Implement, test, and open a PR against `dev`

Step 3 is deliberately the smallest useful slice and needs no answer from anyone -
everything it depends on is in the repository already.

## Questions?

Comment on this issue and a maintainer will help you get started.
