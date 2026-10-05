# Transactions — design

- **Date:** 2026-10-05
- **Status:** design; built alongside.
- **Parent spec:** [`2026-09-25-kestrel-design.md`](2026-09-25-kestrel-design.md) (§7 contract, §8 connectors).
  Extends [the Phase 5 spec](2026-09-27-phase-5-one-dashboard-design.md) §3, which added the cash and debt accounts
  and the six research blocks.

## 1. Why

A bank feed knows more than a balance: it posts every charge, payment, deposit and interest line. The Account page
for a cash or debt account shows the balance's history and the money moved per day, but not what moved it. The
owner's bank source (Plaid, through the finance repo's feed) already carries ninety days of posted rows per
account, so the dashboard can show them without any new collection.

## 2. The contract

One more optional block, `transactions`, in the same spirit as the Phase 5 blocks: a list that defaults to empty,
so a document written before it existed still loads, and an older kestrel ignores it.

| Field | Meaning |
|---|---|
| `account_id` | the account it belongs to |
| `date` | the day it posted |
| `amount` | signed: money in positive, money out negative. On a card, a payment is money in and a charge money out, the same convention as the account's `net_flow` |
| `description` | what the bank says it was |
| `counterparty` | optional: the other side, when the source names one |
| `category` | optional: the source's own word for it, shown as text |

Posted rows only: a source leaves pending ones out. A row carries no id of its own; a source sends each posted row
once. A transaction for an account the document doesn't name is kept and simply never shown. When a later source
reuses an account id an earlier one already has, the later account goes with everything that hangs off it, its
transactions included (connectors.md's duplicate rule).

## 3. The feed

investing's `kestrel_feed` gains a `transactions` builder beside `reserves`: it reads the finance file's
`transactions`, keeps the rows whose account the file's `accounts` list names, maps each nickname to the account
id `reserves` builds for it (the same slug), and sets the sign: a depository row passes through (the file already
has outflows negative), a card row is negated (the file keeps the legacy convention of charges positive). Rows with
no date or amount are skipped. The `teller_category` field, when present, becomes `category`.

## 4. The page

The Account page gains a **Transactions** panel, full width, under Holdings, for any account the snapshot has rows
for. A brokerage account, whose source sends none, shows no panel.

- **Title and subtitle:** "Transactions"; "n since 7 Jul · in $4,210.00 · out $3,980.55" (the rows' count, the
  oldest row's day, and the totals in and out over the rows shown).
- **Controls:** a **Show** segmented control (All · In · Out) and a search box that matches the description,
  counterparty and category, case-insensitively.
- **The table:** Date · Description (the counterparty under it, muted, when the source names one that the
  description doesn't already say) · Category · Amount. Newest first. The amount is mono and signed: a plus for
  money in, the minus sign for money out, in the ordinary ink, since a bank row is neither a gain nor a loss. The
  table scrolls inside the panel past about twelve rows, so the page never grows with the feed.
- **Empty:** "No transactions match." when the search or the filter leaves nothing.

## 5. The view

`AccountView.transactions` is `null` when the snapshot has no rows for the account, else: `rows` (newest first,
each with date, amount, description, counterparty and category), `count`, `since` (the oldest day), `money_in`
and `money_out` (both positive, rounded to cents). The view does the sorting and the totals; the page filters and
searches.

## 6. The demo

Alex's checking, savings and card get rows that follow the flows the demo already draws: pay and rent, the
transfers into the other accounts, the card's charges at a handful of fictional merchants and its payments, the
savings deposits. Ninety days of them, so the page looks the way a bank feed makes it look.

## 7. Where the code goes

- `src/kestrel/contract.py`: `Transaction`, `Snapshot.transactions`, `_LIST_FIELDS`.
- `src/kestrel/connectors/__init__.py`: a dropped account takes its transactions with it.
- `src/kestrel/connectors/feed.py`: the source row's detail counts transactions.
- `src/kestrel/connectors/demo.py`: the demo rows.
- `src/kestrel/views/accounts.py`: `TransactionRow`, `Transactions`, `AccountView.transactions`.
- `web/src/pages/account/TransactionsPanel.tsx`; `Account.tsx` mounts it; `lib/api.ts` types.
- `docs/data-contract.md` (a Transactions section), `docs/connectors.md` (the duplicate rule), the schema and the
  web fixtures (regenerated), a `account-checking.json` fixture for the page tests.
- investing: `kestrel_feed/transactions.py`, `build.py`, the contract-shape table, `tests/test_transactions.py`.

## 8. Testing

- **Contract:** the block defaults to empty, round-trips through JSON, and merges across snapshots.
- **Connectors:** a duplicate account's transactions go with it; the feed row's detail counts them.
- **View:** rows newest first; `money_in` and `money_out` from the signs; `since` the oldest day; `null` with no
  rows; the demo's checking has rows and its brokerage accounts none.
- **Feed (investing):** nickname to id, the card sign flip, skipped rows, a missing or unreadable file gives an
  empty block with no crash.
- **Page:** the panel appears for an account with rows and not for one without; newest first; Show narrows to in
  or out; the search matches description, counterparty and category; the empty line; the subtitle's figures.
- The screenshot pass on `/accounts/checking` from the demo at 390 and 1440 px, both themes.
