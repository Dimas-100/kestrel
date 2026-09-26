# The kestrel data contract

Every source kestrel reads speaks one format: a **Snapshot**. The built-in connectors produce one, and so can any
system of your own — serve a Snapshot as JSON and the `feed` connector (Phase 4) plugs it in without a line of your
system's code entering this repo.

- **Schema:** [`contract/snapshot.schema.json`](contract/snapshot.schema.json), generated from
  `src/kestrel/contract.py` (`kestrel schema`); a test fails if the two drift.
- **A complete example:** `kestrel demo` prints the demo Snapshot — a year of fictional accounts, books, trades and runs.
- **Entities and fields:** the table in the [design spec](specs/2026-09-25-kestrel-design.md#7-data-contract-v1).

## Rules

- `contract_version` is `"1"`. Within a major version changes are **additive only**; kestrel ignores fields it does
  not know, and refuses an unknown major version (the source shows as `error` with the reason).
- Every timestamp carries an offset (`2026-09-25T17:08:00-04:00`); dates are `YYYY-MM-DD`.
- Money is in the profile's currency. `net_flow` on a value point is that day's deposits minus withdrawals, so
  performance is measured net of money moving in and out.
- `status` on a source is `ok`, `stale` or `error`; kestrel also marks a source stale once its `last_success` is older
  than the profile's `stale_after` for it.
- An alert's `link` is a page inside kestrel (`/books`) or empty. A link to another site (`https://…`, `//host`) fails
  validation, so the payload is dropped and the source shows as `error`.
- A connector only reads. Nothing in the contract asks a source to change anything.
