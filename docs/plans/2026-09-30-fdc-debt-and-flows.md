# `fdc` reads debt, limits, rates and bank balances — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** kestrel's `fdc` reader files card and loan kinds under `debt` with the value as what is owed, reads a limit and a rate, and counts every balance change of a bank-sourced account as money moved, so Reserves fills from the collector alone.

**Architecture:** All in `src/kestrel/connectors/fdc.py`: the version floor rises to 6, the kind tables grow, `_read` carries four more columns per account and the latest available credit, and `_build` applies the debt sign and the limit once the category is known (the category depends on the profile, and `_read`'s result is cached across profiles). The fixture warehouse gains the version-6 columns so every test runs against the current shape.

**Tech Stack:** Python 3.11, sqlite3, pydantic, pytest.

**Spec:** `docs/specs/2026-09-30-fdc-debt-and-flows-design.md`

## Global Constraints

- Read-only: the warehouse is opened `mode=ro` with `query_only`; nothing writes to it. No new routes.
- Nothing personal in git: the fixture's accounts, symbols and numbers are fictional.
- `MIN_VERSION = 6`; a warehouse below it gets `this warehouse is at schema version N and kestrel needs 6: update financial-data-collector and run \`fdc sync\``.
- A `debt` account's `value` is the amount owed: positive when owed, below zero when in the person's favour. Its history's values follow the same sign; its `net_flow` keeps the contract's meaning (money in, a payment, less money out, a charge) and is not negated. (Corrected after the final review: this plan first said the flows were negated too, which made paying a card read as market growth.)
- A `flows = 'balance'` account's `net_flow` per point is its stored balance less the previous point's; the first point's is 0. Its `transactions` are ignored.
- `limit` is `credit_limit`, else owed plus `available` when the account is a debt and the latest cash row's `available` is above zero, else none. `rate_pct` is the row's.
- Tests run from the worktree root with `PYTHONPATH=src ../../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`; `ruff check .` the same way.

## Review Focus

1. **A debt whose category came from the profile** (`[sources.categories]` says `debt` for a plain account) must get the same sign flip as one whose kind said so. Task 2 tests it.
2. **A card paid past zero** (stored above zero, since the service's sign is "owed below zero") must read as a debt with a value below zero, not as cash. Task 2 tests it.
3. **A balance-only account with one point** must have `net_flow` 0 and no growth, not a crash on "previous point". Task 2 tests it.
4. **A version-5 warehouse from before the collector's migration** must be refused with the message that names the fix, not fail on a missing column. Task 1 tests it.
5. **Cached loads across profiles:** `_read`'s result is cached by path; the sign flip must live in `_build`, or a second profile that files the same account differently would see a stale sign. Task 2's profile-category test runs two connectors on one warehouse.

---

### Task 1: The fixture grows to version 6, and the reader asks for it

**Files:**
- Modify: `tests/fdc_fixture.py`
- Modify: `src/kestrel/connectors/fdc.py:30` (`MIN_VERSION`)
- Test: `tests/test_fdc_connector.py`

**Interfaces:**
- Produces: `Warehouse.account(label, institution="fidelity", account_type="brokerage", *, flows="transactions", credit_limit=None, rate_pct=None, origin="file")`; `Warehouse.snapshot(account_id, day, positions=(), cash=None, available=None)`; `Warehouse(version=6)` by default.

- [ ] **Step 1: Write the failing test.** In `tests/test_fdc_connector.py`, replace `test_an_old_schema_version_is_refused` (line 44) with:

```python
def test_an_old_schema_version_is_refused(tmp_path):
    path = Warehouse(tmp_path / "old.db", version=5).close()
    with pytest.raises(ConnectorError) as e:
        connector(path).snapshot(NOW)
    assert str(e.value) == (f"this warehouse is at schema version 5 and kestrel needs 6: {fdc.UPDATE}")


def test_the_fixture_is_the_collectors_current_shape(tmp_path):
    with connect(Warehouse(tmp_path / "w.db").close()) as conn:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 6
        columns = {r[1] for r in conn.execute("PRAGMA table_info(accounts)")}
        assert {"external_key", "origin", "kind_confirmed", "credit_limit", "rate_pct", "flows"} <= columns
        assert "available" in {r[1] for r in conn.execute("PRAGMA table_info(cash_balances)")}
        assert "connections" in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
```

  (Read the old test first: it builds a version-3-or-lower warehouse and checks the message names `3`; the new one names `5` and `6`.)

- [ ] **Step 2: Run it to see it fail.** `PYTHONPATH=src ../../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_fdc_connector.py -k "old_schema or current_shape"` — expected: FAIL (`version=5` is accepted; no `external_key` column).

- [ ] **Step 3: Grow the fixture.** In `tests/fdc_fixture.py`:
  1. In `SCHEMA["accounts"]`, after `first_seen    TEXT NOT NULL` add the six columns from the collector's migration 0006:

```sql
  first_seen    TEXT NOT NULL,
  external_key  TEXT,
  origin        TEXT NOT NULL DEFAULT 'file',
  kind_confirmed INTEGER NOT NULL DEFAULT 1,
  credit_limit  REAL,
  rate_pct      REAL,
  flows         TEXT NOT NULL DEFAULT 'transactions'
```

  2. In `SCHEMA["cash_balances"]`, after `amount      REAL NOT NULL,` add `  available   REAL,`.
  3. Add to `SCHEMA`, after `"sync_runs"`:

```python
    # 0006_connections.sql
    "connections": """CREATE TABLE connections (
  name           TEXT PRIMARY KEY,
  key_ref        TEXT NOT NULL,
  created_at     TEXT NOT NULL,
  removed_at     TEXT,
  last_fetch_at  TEXT,
  last_ok_at     TEXT,
  last_error     TEXT NOT NULL DEFAULT ''
)""",
```

  4. Change the docstring's citation to `..., 0003_derived.sql and 0006_connections.sql)`.
  5. `Warehouse.__init__`: `version: int = 6`.
  6. Replace `account` and `snapshot` with:

```python
    def account(self, label: str, institution: str = "fidelity", account_type: str = "brokerage", *,
                flows: str = "transactions", credit_limit: float | None = None, rate_pct: float | None = None,
                origin: str = "file") -> int:
        cur = self.conn.execute(
            "INSERT INTO accounts (label, institution, account_type, first_seen, flows, credit_limit, rate_pct, origin) "
            "VALUES (?, ?, ?, '2026-01-02', ?, ?, ?, ?)",
            (label, institution, account_type, flows, credit_limit, rate_pct, origin))
        return int(cur.lastrowid)

    def snapshot(self, account_id: int, day: Day, positions=(), cash: float | None = None,
                 available: float | None = None) -> None:
        """A broker snapshot: positions as (symbol, description, quantity, price, market_value, cost_basis_total);
        `available` is a card's remaining credit as the bank reported it."""
        for symbol, description, quantity, price, value, cost in positions:
            self.conn.execute("INSERT OR IGNORE INTO securities (symbol, description, first_seen) "
                              "VALUES (?, ?, '2026-01-02')", (symbol, description))
            self.conn.execute("INSERT INTO position_snapshots (as_of_date, account_id, symbol, quantity, price, "
                              "market_value, cost_basis_total, source) VALUES (?, ?, ?, ?, ?, ?, ?, 'fixture')",
                              (_iso(day), account_id, symbol, quantity, price, value, cost))
        if cash is not None:
            self.conn.execute("INSERT INTO cash_balances (as_of_date, account_id, amount, available, source) "
                              "VALUES (?, ?, ?, ?, 'fixture')", (_iso(day), account_id, cash, available))
```

- [ ] **Step 4: Raise the floor.** In `src/kestrel/connectors/fdc.py` change line 30 to:

```python
MIN_VERSION = 6  # accounts.flows, credit_limit and rate_pct, and cash_balances.available, arrived in migration 6
```

- [ ] **Step 5: Run the connector tests.** `PYTHONPATH=src ../../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_fdc_connector.py` — expected: PASS (the fixture defaults keep every existing test as it was).

- [ ] **Step 6: Commit.**

```bash
git add tests/fdc_fixture.py src/kestrel/connectors/fdc.py tests/test_fdc_connector.py
git commit -m "fdc: the fixture warehouse is the collector's version 6, and the reader asks for it"
```

---

### Task 2: Debt, limit, rate and balance flows

**Files:**
- Modify: `src/kestrel/connectors/fdc.py`
- Test: `tests/test_fdc_connector.py`

**Interfaces:**
- Consumes: the fixture from Task 1.
- Produces: `DEBT: set[str]`; `category_of(kind)` returning `"debt"` for it; `Account.limit`, `Account.rate_pct` filled; debt sign and balance flows in the snapshot.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_fdc_connector.py`:

```python
def _bank(folder):
    """Alex's bank through a connection: a card owing 640 (below zero, as the bank reports it) with a rate and a
    limit set by hand, a checking account whose balance moved three days running, and a card paid past zero."""
    w = Warehouse(folder / "bank.db")
    card = w.account("Example Bank Visa", "example_bank", "credit_card", flows="balance", rate_pct=24.9,
                     credit_limit=5000.0, origin="simplefin")
    unset = w.account("Example Bank Platinum", "example_bank", "credit_card", flows="balance", origin="simplefin")
    checking = w.account("Example Bank Checking", "example_bank", "checking", flows="balance", rate_pct=0.1,
                         origin="simplefin")
    overpaid = w.account("Example Bank Store Card", "example_bank", "credit_card", flows="balance", origin="simplefin")
    roth = w.account("Alex Roth IRA", "fidelity", "roth_ira")
    for day, owed in {23: -700.0, 24: -640.0}.items():
        w.day(card, d(day), {}, cash=owed)
    w.snapshot(card, d(24), [], cash=-640.0, available=0.0)
    w.day(unset, d(24), {}, cash=-1000.0)
    w.snapshot(unset, d(24), [], cash=-1000.0, available=4000.0)
    for day, balance in {23: 100.0, 24: 250.0, 25: 200.0}.items():
        w.day(checking, d(day), {}, cash=balance)
    w.snapshot(checking, d(25), [], cash=200.0, available=200.0)
    w.day(overpaid, d(24), {}, cash=25.0)
    w.snapshot(overpaid, d(24), [], cash=25.0, available=0.0)
    w.day(roth, d(24), {"SPY": 6000.0}, cash=150.0)
    w.day(roth, d(25), {"SPY": 6100.0}, cash=150.0)
    w.flow(roth, d(25), "contribution", 100.0)
    w.flow(checking, d(24), "contribution", 999.0)   # a balance account's transactions are ignored
    w.prices("SPY", {d(24): 600.0, d(25): 610.0})
    w.run("derive", "ok", "2026-09-25T12:05:00Z")
    return w.close()


def test_a_card_is_a_debt_worth_what_it_owes_with_its_rate_and_limit(tmp_path):
    accounts = {a.id: a for a in connector(_bank(tmp_path)).snapshot(NOW).accounts}
    visa = accounts["example-bank-visa"]
    assert (visa.category, visa.value, visa.cash, visa.rate_pct, visa.limit) == ("debt", 640.0, 640.0, 24.9, 5000.0)
    assert visa.account_type == "Credit card" and visa.institution == "Example Bank"
    assert [category_of(k) for k in ["credit_card", "loan", "mortgage", "line_of_credit"]] == ["debt"] * 4
    assert [type_text(k) for k in ["loan", "line_of_credit", "checking", "money_market"]] == [
        "Loan", "Line of credit", "Checking", "Money market"]


def test_a_limit_comes_from_available_credit_when_none_was_set(tmp_path):
    accounts = {a.id: a for a in connector(_bank(tmp_path)).snapshot(NOW).accounts}
    assert accounts["example-bank-platinum"].limit == 5000.0          # owed 1000 + available 4000
    assert accounts["example-bank-visa"].limit == 5000.0              # set by hand wins over available 0
    assert accounts["example-bank-checking"].limit is None            # not a debt: available means nothing here
    assert accounts["example-bank-store-card"].limit is None          # available 0: no limit


def test_a_card_paid_past_zero_is_a_debt_below_zero(tmp_path):
    accounts = {a.id: a for a in connector(_bank(tmp_path)).snapshot(NOW).accounts}
    store = accounts["example-bank-store-card"]
    assert (store.category, store.value) == ("debt", -25.0)


def test_a_balance_accounts_changes_are_money_moved_in_its_own_sign(tmp_path):
    snap = connector(_bank(tmp_path)).snapshot(NOW)
    history = {s.id: s.points for s in snap.account_history}
    assert [(p.date.day, p.value, p.net_flow) for p in history["example-bank-checking"]] == [
        (23, 100.0, 0.0), (24, 250.0, 150.0), (25, 200.0, -50.0)]          # the 999 contribution is ignored
    assert [(p.date.day, p.value, p.net_flow) for p in history["example-bank-visa"]] == [
        (23, 700.0, 0.0), (24, 640.0, -60.0)]                              # owed went down by 60
    assert [(p.date.day, p.value, p.net_flow) for p in history["example-bank-store-card"]] == [(24, -25.0, 0.0)]
    assert [(p.date.day, p.net_flow) for p in history["alex-roth-ira"]] == [(24, 0.0), (25, 100.0)]  # unchanged
    accounts = {a.id: a for a in snap.accounts}
    assert accounts["example-bank-checking"].category == "cash" and accounts["example-bank-checking"].rate_pct == 0.1


def test_the_profile_can_file_a_collector_account_under_debt_and_the_sign_follows(tmp_path):
    path = _bank(tmp_path)
    plain = connector(path).snapshot(NOW)
    filed = connector(path, categories={"alex-roth-ira": "debt"}).snapshot(NOW)   # the same cached load
    before = {a.id: a for a in plain.accounts}["alex-roth-ira"]
    after = {a.id: a for a in filed.accounts}["alex-roth-ira"]
    assert (before.category, before.value) == ("long_term", 6250.0)
    assert (after.category, after.value, after.cash) == ("debt", -6250.0, -150.0)
    assert [p.value for p in {s.id: s.points for s in filed.account_history}["alex-roth-ira"]] == [-6150.0, -6250.0]
    again = {a.id: a for a in connector(path).snapshot(NOW).accounts}["alex-roth-ira"]
    assert (again.category, again.value) == ("long_term", 6250.0)
```

- [ ] **Step 2: Run them to see them fail.** `PYTHONPATH=src ../../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_fdc_connector.py -k "card or balance_accounts or file_a_collector or limit_comes"` — expected: FAIL (`category` is `other`, value −640, `limit` None, flows 999).

- [ ] **Step 3: Teach the reader.** In `src/kestrel/connectors/fdc.py`:
  1. Replace the `TYPES`, `LONG_TERM`, `CASH` block and `category_of` with:

```python
TYPES = {"roth_ira": "Roth IRA", "traditional_ira": "Traditional IRA", "brokerage": "Brokerage", "crypto": "Crypto",
         "401k": "401(k)", "403b": "403(b)", "457b": "457(b)", "ira": "IRA", "rollover_ira": "Rollover IRA",
         "sep_ira": "SEP IRA", "simple_ira": "SIMPLE IRA", "hsa": "HSA", "checking": "Checking", "savings": "Savings",
         "money_market": "Money market", "credit_card": "Credit card", "loan": "Loan", "mortgage": "Mortgage",
         "line_of_credit": "Line of credit"}
LONG_TERM = {"roth_ira", "traditional_ira", "ira", "rollover_ira", "sep_ira", "simple_ira", "401k", "403b", "457b",
             "hsa", "pension", "brokerage"}
CASH = {"checking", "savings", "cash", "money_market"}
DEBT = {"credit_card", "loan", "mortgage", "line_of_credit"}  # the collector stores what these owe below zero
```

```python
def category_of(account_type: str) -> Category:
    if account_type in LONG_TERM:
        return "long_term"
    if account_type in CASH:
        return "cash"
    return "debt" if account_type in DEBT else "other"
```

     (Keep `HISTORY`, `FLOWS` and the `_words` helpers as they are.)

  2. `_LoadedAccount` gains four fields after `day`:

```python
    flows: str  # 'balance': no transactions explain its changes, so every change is money moved
    credit_limit: float | None
    rate_pct: float | None
    available: float | None  # the latest cash row's remaining credit, when the bank reported one
```

  3. In `_read`, the first statement becomes:

```python
        rows = conn.execute("SELECT id, label, institution, account_type, flows, credit_limit, rate_pct "
                            "FROM accounts ORDER BY id").fetchall()
```

     and after `latest = {...}` add:

```python
        # the latest cash row's available credit per account (days ascending, so the last one wins)
        available: dict[int, float | None] = {}
        for account, value in conn.execute(
                "SELECT account_id, available FROM cash_balances ORDER BY as_of_date"):
            available[account] = value
```

     Replace the `moved = flows(...)` statement and the loop with:

```python
        moved = flows(conn, {account: [day for day, _, _ in points] for account, points in days.items()
                             if replayed.get(account)})
        for warehouse_id, _, _, _, flow_kind, _, _ in rows:
            if flow_kind == "balance":  # every change is money moved; the first point moves nothing
                points = days[warehouse_id]
                moved[warehouse_id] = {day: (value - points[i - 1][1] if i else 0.0)
                                       for i, (day, value, _) in enumerate(points)}

        accounts: list[_LoadedAccount] = []
        series: list[Series] = []
        for warehouse_id, label, institution, kind, flow_kind, credit_limit, rate_pct in rows:
            points = days[warehouse_id]
            if points:
                series.append(Series(id=ids[warehouse_id], points=[
                    ValuePoint(date=date.fromisoformat(day), value=round(value, 2),
                               net_flow=round(moved[warehouse_id].get(day, 0.0), 2))
                    for day, value, _ in points]))
            day, value, cash = points[-1] if points else (None, 0.0, 0.0)
            accounts.append(_LoadedAccount(
                id=ids[warehouse_id], label=label, institution=institution_text(institution),
                type_code=kind, type_display=type_text(kind), value=round(value, 2), cash=round(cash, 2), day=day,
                flows=flow_kind, credit_limit=credit_limit, rate_pct=rate_pct, available=available.get(warehouse_id),
            ))
```

     (`rows` is unpacked with seven names in both loops; `ids`, `by_label` and `latest` still read `r[0]`/`r[1]`.)

  4. In `_build`, replace the `accounts = [...]` statement with:

```python
        accounts: list[Account] = []
        debt_ids: set[str] = set()
        for a in data.accounts:
            category = self._category(a.id, a.label, a.type_code)
            value, cash = a.value, a.cash
            limit = a.credit_limit
            if category == "debt":  # the collector stores what a debt owes below zero; the contract wants it owed
                debt_ids.add(a.id)
                value, cash = -value, -cash
                if limit is None and a.available:  # a card's remaining credit tells what its line is
                    limit = round(value + a.available, 2)
            accounts.append(Account(
                id=a.id, name=a.label, institution=a.institution, account_type=a.type_display, category=category,
                value=value, cash=cash, as_of=_close(a.day) if a.day else now, rate_pct=a.rate_pct, limit=limit))
        # a debt's history and flows follow its value: what it owed each day, and how that moved
        history = [Series(id=s.id, points=[ValuePoint(date=p.date, value=-p.value, net_flow=p.net_flow)
                                            for p in s.points]) if s.id in debt_ids else s
                   for s in data.series]
```

     and pass `account_history=history` (instead of `data.series`) to the returned `Snapshot`.

- [ ] **Step 4: Run the tests.** `PYTHONPATH=src ../../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_fdc_connector.py` — expected: PASS. Then `PYTHONPATH=src ../../.venv/Scripts/python.exe -m ruff check src tests` — expected: clean.

- [ ] **Step 5: Commit.**

```bash
git add src/kestrel/connectors/fdc.py tests/test_fdc_connector.py
git commit -m "fdc: a card or a loan is a debt worth what it owes, with its limit and rate; a bank balance's changes are money moved"
```

---

### Task 3: Reserves from the collector alone, and the docs

**Files:**
- Test: `tests/test_reserves_view.py`
- Modify: `docs/connectors.md`, `README.md`, `profile.example.toml`

- [ ] **Step 1: Write the failing test.** Append to `tests/test_reserves_view.py`:

```python
def test_reserves_fills_from_the_collector_alone(tmp_path):
    from fdc_fixture import Warehouse, d
    from kestrel.connectors.fdc import FdcConnector

    w = Warehouse(tmp_path / "bank.db")
    card = w.account("Example Bank Visa", "example_bank", "credit_card", flows="balance", rate_pct=24.9,
                     credit_limit=5000.0, origin="simplefin")
    savings = w.account("Example Bank Savings", "example_bank", "savings", flows="balance", rate_pct=4.1,
                        origin="simplefin")
    w.day(card, d(24), {}, cash=-640.0)
    w.snapshot(card, d(24), [], cash=-640.0, available=0.0)
    w.day(savings, d(24), {}, cash=24243.44)
    w.snapshot(savings, d(24), [], cash=24243.44)
    w.run("derive", "ok", "2026-09-24T22:00:00Z")
    snapshot = FdcConnector("bank", "Bank", w.close()).snapshot(NOW)
    view = reserves_view(snapshot, DEMO_PROFILE, NOW)
    debt = {line.name: line for line in view.debts}
    assert debt["Example Bank Visa"].owed == 640.0 and debt["Example Bank Visa"].limit == 5000.0
    assert debt["Example Bank Visa"].utilization_pct == 12.8 and debt["Example Bank Visa"].rate_pct == 24.9
    assert {line.name: line.rate_pct for line in view.cash} == {"Example Bank Savings": 4.1}
```

  Read the view's dataclass names first (`tests/test_reserves_view.py:31-60` and `src/kestrel/views/reserves.py`): the collections may be called `debts` and `cash`; use the names the view actually has.

- [ ] **Step 2: Run it to see it fail.** `PYTHONPATH=src ../../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_reserves_view.py -k collector` — expected: FAIL only if Task 2 is missing; with Task 2 in place it should PASS. If it passes at once, that is the point: it pins the end-to-end path. Keep it either way.

- [ ] **Step 3: Docs.**
  1. `docs/connectors.md`, the `category` row of the `fdc` table (line 63): append to the end of the cell: `; \`credit_card\`, \`loan\`, \`mortgage\` and \`line_of_credit\` are debt`.
  2. Same file, after the "Value and cash" bullet (line 73–75) add:

```markdown
- **A debt is what it owes.** The collector stores a card's or a loan's balance below zero, as the bank reports it;
  kestrel shows it as the amount owed, positive when owed and below zero when the balance is in your favour, and
  its history the same way. Its `limit` is the one set with `fdc accounts set --limit`, else what it owes plus the
  remaining credit the bank reported, when it reported one above zero.
- **A rate** (`rate_pct`: what cash earns, what a debt costs) is the one set with `fdc accounts set --rate`.
- **A bank account has no transactions in the warehouse** (`flows = 'balance'`), so every change in its balance
  counts as money moved, never as growth: money in is positive and money out is negative, and for a card or a
  loan a payment is money in and a charge is money out, as the contract says. Paying a card from checking nets to
  nothing; a paycheck never shows as market growth; interest doesn't show as growth either.
```

  3. Same file, replace the paragraph at lines 118–123 (from `An unknown category is a profile error` to `data-contract.md)).`) with:

```markdown
An unknown category is a profile error, not a line under the source: `kestrel check` stops before reading any source
with `profile problem: <path>: sources.0: Value error, unknown category 'trade' for 'Brokerage' (use long_term,
trading, cash, debt or other)` and exits with status 2. A card or a loan comes from the collector when it was
connected there (`fdc connect simplefin`) or filed under `debt` in `[sources.categories]`; a feed can still send one
as an account with `category: "debt"` whose `value` is what it owes (see [the data contract](data-contract.md)).
The reader needs a warehouse at schema version 6 or later; an older one reads `this warehouse is at schema
version 5 and kestrel needs 6: update financial-data-collector and run fdc sync`.
```

     and in the Troubleshooting table change the `schema version 2` row's first cell to `` `this warehouse is at schema version 5 …` or `this warehouse is missing holdings_daily …` `` (the same fix applies).
  4. `README.md` step 2 (lines 107–111): replace `A card or a loan doesn't come from the collector (its values are what an account holds): it arrives from a feed as a \`debt\` account (step 5).` with `Banks and cards you connected in the collector arrive with it, as \`cash\` and \`debt\` accounts; \`debt\` is also a valid category to file a collector account under.`
  5. `profile.example.toml` line 42–43: `# [sources.categories]         # optional: account id or exact label = long_term | trading | cash | debt | other` and `# "brokerage-2" = "trading"    # (a card or a loan the collector knows arrives as debt by itself)`.

- [ ] **Step 4: Run everything.** `PYTHONPATH=src ../../.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` — expected: PASS (including `test_hygiene.py` and `test_generated_files.py`; the contract didn't change, so no generated file changes). `PYTHONPATH=src ../../.venv/Scripts/python.exe -m ruff check src tests` — expected: clean.

- [ ] **Step 5: Commit.**

```bash
git add tests/test_reserves_view.py docs/connectors.md README.md profile.example.toml
git commit -m "docs: a card or a loan comes from the collector; Reserves fills from it alone"
```

---

## Self-review

- **Spec coverage:** §2 version → Task 1; kinds, sign, limit and rate, balance flows → Task 2; §3 docs → Task 3; §4 tests → Tasks 1–3 (the screenshot pass is a manual step, run after the build with a warehouse that holds a card, and noted in the final report).
- **Placeholders:** none.
- **Type consistency:** `_LoadedAccount.flows/credit_limit/rate_pct/available` are set in `_read` and read in `_build`; `Account.rate_pct`/`limit` exist in the contract (`src/kestrel/contract.py:43-44`).
- **Review Focus:** (1) `test_the_profile_can_file_a_collector_account_under_debt_and_the_sign_follows`; (2) `test_a_card_paid_past_zero_is_a_debt_below_zero`; (3) the store card in `test_a_balance_accounts_changes_are_money_moved_in_its_own_sign` (one point, flow 0); (4) `test_an_old_schema_version_is_refused`; (5) the same test as (1), which runs three connectors on one warehouse and checks the plain one again last.
