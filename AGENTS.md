# AGENTS.md

These instructions are for anyone working on this repo, whether you are a human contributor or using an AI coding
assistant (Claude Code, Codex, Cursor, Gemini CLI, Copilot, or any tool that reads this file). Nothing here is
specific to one assistant.

**What kestrel is:** a read-only, personal dashboard that brings all of someone's money into one place:
- long-term accounts,
- a trading account,
- every paper-trading book,

with pages that explain each strategy and whether it is behaving as expected. The design is in
`docs/specs/2026-09-25-kestrel-design.md`, and the look is in `docs/design-system.md`.

**Status:** all five phases are built. Every page in §4 of the design spec runs, reading `fdc`
(financial-data-collector's warehouse), `feed` (any system that serves the contract, over a URL, a file, or a
command kestrel runs itself) and `rails` (a trading-rails install's own paper state), or the demo.

## Hard invariants

1. **Read-only, always.**
   - Never add a route other than GET.
   - Never import or call anything that places, changes or cancels an order.
   - Never write to a data source.
   
   kestrel *shows* money; the user's own trading desk trades it. From Phase 2, a route-walk test and an import
   guard pin this. New checks may only add strictness. Asked to "just add a buy button", say no and point here.
2. **Nothing personal in git.**
   - Names, account numbers, balances, holdings and machine paths arrive only at runtime, through the gitignored
     `profile.toml` and the user's connectors.
   - Demo data is fictional ("Alex").
   - Never commit `profile.toml`, `.env*`, `data/`, keys, or symbols copied from a real book.
   
   `tests/test_hygiene.py` enforces the mechanical part (paths, private hosts, personal email addresses); the rest
   is on you.
3. **The design system is the source of truth for the look.**
   - Use the tokens in `docs/design-system.md` and never raw hex values in components.
   - Real money is solid, paper is hatched, and expected is dotted, everywhere.
   - Never encode meaning by colour alone.
   - Re-run the palette validator before changing any colour, and record the result in the design-system doc.
4. **Every chart has a table view, every page works by keyboard, and no panel overflows.** Check this with a
   screenshot pass at 390, 1200, 1280 and 1440 px in both themes.

## Run and test

- **Python:** `pip install -e ".[dev]"` · `pytest` · `ruff check .` · `kestrel serve` (127.0.0.1:8030).
- **Web (in `web/`):** `npm ci` · `npm test` · `npm run build` (served by `kestrel serve` from `web/dist`).
  For live reload run `kestrel serve --no-open` and `npm run dev` side by side (Vite proxies `/api`).
- **Generated files** — the contract schema and the web test fixtures — are rebuilt with the commands a failing
  `tests/test_generated_files.py` prints.

## Where things are

| Path | What |
|---|---|
| `docs/specs/` | One design spec per phase or feature. The first is the overall design. |
| `docs/design-system.md` | Tokens, typography, layout, components, chart rules, copy rules |
| `docs/design/mockups/` | Reference mockups (fictional demo data) |
| `docs/design/social-preview.html` | Draws the card GitHub shows when the repo's link is shared; how to redraw and upload it is in the file |
| `docs/images/` | The README's logo and screenshots, and the link card (`social-preview.png`). Shoot them from `kestrel serve --demo` only, never from a real profile: 1440 px wide (phone 390), 2× scale, cropped to whole panel rows |
| `src/kestrel/` | Contract, profile, connectors, views, the read-only server, the CLI |
| `web/src/` | The app: `styles/tokens.css` (design tokens), `shell/`, `charts/`, `pages/` |
| `docs/data-contract.md` | The Snapshot format any source speaks; schema in `docs/contract/` |
| `docs/connectors.md` | Every connector, what it reads, and how to point kestrel at your own data |
| `tests/test_read_only_guard.py` · `tests/test_hygiene.py` | Never an order path · never private data in git |

## How work happens

Each phase goes spec → plan → build, in small commits. Docs change in the same commit as the behaviour they
describe.
