# Phase 4b — the `feed` connector — design

- **Date:** 2026-09-26
- **Status:** built (plan: [`../plans/2026-09-26-phase-4b-feed.md`](../plans/2026-09-26-phase-4b-feed.md)).
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§7 contract, §8 connectors, §10 safety). Phase 4a ([`2026-09-26-phase-4a-accounts-design.md`](2026-09-26-phase-4a-accounts-design.md)) brought real accounts through `fdc`. This phase adds the generic `feed` connector, through which any private system serves its books, strategies, trades and runs. The private system's own side (what it reads and how it builds the payload) is specified in that system's repo, never here.
- **Deferred from 4a:** duplicate ids across sources (done here, §3).
- **Not in 4b:** `rails` (trading-rails is not running anywhere yet; YAGNI), the Books pages (Phase 3b).

## 1. Why

The Strategy pages and Home's books table only show fictional books so far. A trading system knows its books, rules, backtests, trades and open positions; kestrel should show them without knowing anything about that system. The `feed` connector reads one JSON document in the contract's own format (a Snapshot) from a URL or a file, checks it, and hands it on.

## 2. The connector

### 2.1 Profile

```toml
[[sources]]
id = "desk"
kind = "feed"
label = "Trading desk"
url = "http://127.0.0.1:8000/api/feed"   # or: path = "../desk/feed.json"
token_env = "KESTREL_DESK_TOKEN"          # optional: the NAME of an environment variable holding a bearer token
timeout = 5                               # optional: seconds, 1–60 (default 5)
stale_after = "15m"
```

- Exactly one of `url` and `path`. A `url` must be `http://` or `https://`. A relative `path` is relative to the profile's folder (Phase 4a's rule).
- `token_env` names an environment variable; the token itself never goes in the profile. When `token_env` is set and the variable is empty or missing, the source is an error: "set KESTREL_DESK_TOKEN in the environment (token_env)". The token is sent as `Authorization: Bearer …` to the configured URL only.
- Wrong shapes (both or neither of `url`/`path`, another scheme, a timeout outside 1–60) are profile errors, worded for a person.

### 2.2 Fetching and checking

- **HTTP:** one GET with the timeout, `Accept: application/json`. Redirects are refused (an error naming the target), so a token can never follow a redirect elsewhere. A status other than 200 is an error ("the feed answered 503"). The body is read up to 20 MB; more is an error ("the feed sent more than 20 MB").
- **File:** read up to 20 MB, UTF-8 (a BOM is fine). A missing file is "no feed file at <path>".
- **Parse and validate:** JSON first ("the feed sent something that isn't JSON"), then `Snapshot` validation. A payload of another major contract version is refused with the contract's own message. Any other validation error lists the first three problems as `field.path: message`, then "and N more".
- **What kestrel keeps:** every list the payload carries, and its benchmark. The payload's own `sources` are replaced by ONE source row for this feed: `kind = "feed"`, `last_success` = the payload's `generated_at`, `detail` like "5 books · 4 strategies · 61 trades". The payload's `alerts` pass through (their links are already restricted to kestrel pages by the contract).
- The connector only reads. Nothing is cached: a feed is small and the desk is local.

### 2.3 Safety

- GET only; no cookies; the token (when used) only in the header; never logged, never in an error message.
- Everything a feed sends is data rendered as text (the web app never injects HTML). Links in alerts are already limited to pages inside kestrel.
- A feed that is down, slow, huge or malformed becomes a red source row; the rest of kestrel keeps working (`collect()` already isolates sources).

## 3. Duplicate ids across sources

Two sources can name the same thing (two warehouses with an account called "Brokerage", or the demo left in next to a real feed). `collect()` now keeps the first source's item and drops the later one's, with everything that hangs off it:

| Kind | Dropped with it |
|---|---|
| account id | its holdings and its account history |
| book id | its book history, positions, trades and trade charts |
| strategy id | nothing else (books keep pointing at the first strategy) |

The later source's `detail` gains "ignored duplicate ids: brokerage, rsi2" (ids only, at most five, then "and N more"). Profile order decides which source is first.

## 4. Docs

- `docs/connectors.md`: the `feed` section (profile block, what is checked, the error messages, how to build a payload — `kestrel demo` prints a valid one), and the duplicate-id rule. `rails` stays "later".
- `profile.example.toml`: a commented `feed` block.
- README's "point it at your own data": one line on connecting a private system through `feed`.

## 5. Testing

- **Connector** (`tests/test_feed_connector.py`), with a local HTTP server in a thread and temp files: a valid payload over HTTP and from a file; the token sent when set and the error when its variable is missing; a redirect refused; a timeout; a non-200; more than 20 MB; not JSON; another major version; a validation error listing three problems and "and N more"; the source row replaced (kind, last_success, detail); alerts passed through.
- **Profile:** `url`/`path` exclusivity, the scheme, the timeout range.
- **Duplicates** (`tests/test_connectors.py` or similar): account, book and strategy duplicates dropped with their dependents; the note on the later source; profile order wins.
- **Hygiene and read-only guard:** unchanged, still passing (the connector imports no broker code; `urllib` is the standard library).

## 6. Out of scope

- The private system's feed (its own repo and spec).
- Pushing, streaming, or webhooks: kestrel reads the feed each time a page loads.
- Editing anything; placing anything. kestrel stays read-only.
