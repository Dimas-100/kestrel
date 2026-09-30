# `fdc` reads debt, limits, rates and bank balances — design

- **Date:** 2026-09-30
- **Status:** design; awaiting review.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§7 contract, §8 connectors). Phase 4a ([`2026-09-26-phase-4a-accounts-design.md`](2026-09-26-phase-4a-accounts-design.md)) built the `fdc` connector; Phase 5 ([`2026-09-27-phase-5-one-dashboard-design.md`](2026-09-27-phase-5-one-dashboard-design.md)) added the `debt` category and the Reserves page, filled only by a feed.
- **Companion:** financial-data-collector's connections spec (its `docs/superpowers/specs/2026-09-29-connections-design.md`, §14 names this follow-up). Since its migration 6 the warehouse holds bank, card and loan accounts, what the person set about them, and a card's available credit.

## 1. Why

A person who connects a bank through the collector has their cards and loans in the warehouse, but kestrel's `fdc` reader files every account under `long_term`, `cash` or `other` and treats its balance as something held. So a credit card counts as money owned, and Reserves stays empty unless a feed also runs. After this change, Reserves fills from the collector alone, and a bank account's balance changes never read as market growth.

## 2. What the reader learns

All of it in `src/kestrel/connectors/fdc.py`; the contract and the pages don't change.

- **Version.** `MIN_VERSION` becomes 6 (`external_key`, `origin`, `kind_confirmed`, `credit_limit`, `rate_pct`, `flows` on `accounts`; `available` on `cash_balances`). An older warehouse gets today's message: `this warehouse is at schema version 5 and kestrel needs 6: update financial-data-collector and run fdc sync`.
- **Kinds.** `DEBT = {"credit_card", "loan", "mortgage", "line_of_credit"}` maps to the `debt` category; `TYPES` gains their display names (`Credit card`, `Loan`, `Mortgage`, `Line of credit`) and `checking`, `savings`, `money_market` (`Checking`, `Savings`, `Money market`). The profile's `[sources.categories]` may now file a collector account under `debt` as well; the rule below applies to whichever way the category was reached.
- **A debt's value is what it owes.** The warehouse stores a debt below zero (the service's own sign). For an account whose category is `debt`, the reader negates the value, the cash and every history point, so `value` is the amount owed, positive when owed and below zero when the balance is in the person's favour, as the contract says. The views already handle that sign (`home.owed_points`, `accounts`, `reserves`).
- **Limit and rate.** `Account.rate_pct` is `accounts.rate_pct`. `Account.limit` is `accounts.credit_limit`; when that is unset, the account is a debt, and the latest `cash_balances` row for it carries an `available` above zero, the limit is owed plus available (the card's remaining credit tells what the line is). Otherwise no limit.
- **Bank-sourced flows.** For an account with `flows = 'balance'`, every change in its history is money moved: each point's `net_flow` is its value less the previous point's (the first point's is 0), in the account's own value convention (for a debt, owed). The `transactions`-based flows are ignored for such accounts (there are none). Growth then reads 0 for these accounts, and a paycheck never shows as market growth; interest isn't shown as growth either, which the collector's spec accepts.
- **Nothing else changes** for a `flows = 'transactions'` account: value, history and flows come from the replay and the transactions as today.

## 3. Docs

- `docs/connectors.md`, the `fdc` section: a table row for `category` gains the debt kinds; "Values, history and money moved" gains the debt sign and the balance-flow rule; the Troubleshooting paragraph that says a debt can only come from a feed is replaced by: a card or a loan comes from the collector when it was connected there (`fdc connect simplefin`) or filed under `debt` in `[sources.categories]`; a feed still works.
- `README.md` "Point it at your own data", step 2: the sentence saying a card or a loan doesn't come from the collector goes; it now says the collector's connected banks and cards arrive with it, and that `debt` is a valid category for a collector account.
- `profile.example.toml`: the comment on `[sources.categories]` lists `debt`.

## 4. Testing

`tests/fdc_fixture.py` gains the version-6 columns and the `connections` table (copied from the collector's migration 0006), with `version` defaulting to 6, so every existing test runs against the current shape. New tests in `tests/test_fdc_connector.py`:

- A version-5 warehouse is refused with the message naming 5 and 6.
- A `credit_card` account stored at −640 is a `debt` account worth 640, with `rate_pct` 24.9 from the row and `limit` 5000 from `credit_limit`; its history points are what it owed each day.
- A debt with no `credit_limit` and `available` 4360 on its latest balance has `limit` 5000; one with `available` 0 or none has no limit.
- A `checking` account with `flows = 'balance'` and balances 100, 250, 200 on three days has `net_flow` 0, 150, −50 and reads as `cash`; a `credit_card` with `flows = 'balance'` owing 640 then 600 has `net_flow` 0, −40.
- A `flows = 'transactions'` account is unchanged: its flows still come from `transactions`.
- `[sources.categories]` filing a collector account under `debt` negates its value the same way.
- A Reserves view built from an `fdc` snapshot alone lists the card with its utilization and rate (`tests/test_reserves.py`, or wherever the Reserves view is tested today).
- The screenshot pass on Reserves and Home with a warehouse that holds a card and a checking account (demo profile untouched).

## 5. Out of scope

Reading the `connections` table into the Settings page's source detail (a later polish); interest on a balance-only account as growth; a closed connected account's last balance lingering (the collector's later "closed" flag); anything in the web app.
