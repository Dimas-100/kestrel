import datetime as dt
from zoneinfo import ZoneInfo

from kestrel.connectors import collect
from kestrel.connectors.demo import DemoConnector, weekdays_ending
from kestrel.profile import DEMO_PROFILE, Profile, SourceCfg

NY = ZoneInfo("America/New_York")
FRIDAY_EVENING = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)  # 17:08 in New York
SATURDAY = dt.datetime(2026, 9, 26, 15, 0, tzinfo=dt.timezone.utc)


def test_weekdays_ending_skips_weekends():
    days = weekdays_ending(dt.date(2026, 9, 27), 3)  # a Sunday
    assert days == [dt.date(2026, 9, 23), dt.date(2026, 9, 24), dt.date(2026, 9, 25)]


def test_the_demo_is_deterministic():
    a = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    b = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert a == b


def test_the_market_path_stays_put_as_the_dates_move():
    # monthly deposits follow the calendar, so account values shift a little; the market path does not
    today = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    a_week_on = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING + dt.timedelta(days=7))
    paper = lambda snap: next(b.value for b in snap.books if b.id == "rsi2-paper")  # noqa: E731
    assert paper(today) == paper(a_week_on)
    assert [t.return_pct for t in today.trades] == [t.return_pct for t in a_week_on.trades]
    assert a_week_on.account_history[0].points[-1].date == dt.date(2026, 10, 2)


def test_history_ends_today_and_accounts_match_their_last_point():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    history = {s.id: s.points for s in snap.account_history}
    for account in snap.accounts:
        assert history[account.id][-1].date == dt.date(2026, 9, 25)
        assert history[account.id][-1].value == account.value


def test_every_trade_and_position_belongs_to_a_book_and_every_book_to_a_strategy():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    books = {b.id for b in snap.books}
    strategies = {s.id for s in snap.strategies}
    assert {t.book_id for t in snap.trades} <= books
    assert {p.book_id for p in snap.positions} <= books
    assert {b.strategy_id for b in snap.books} <= strategies
    assert all(t.opened <= t.closed for t in snap.trades)


def test_runs_follow_the_clock_and_a_weekend_has_none():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    status = {r.label: r.status for r in snap.runs}
    assert status["Morning run"] == "done" and status["Nightly suite"] == "due"
    assert DemoConnector("demo", NY).snapshot(SATURDAY).runs == []


def test_collect_marks_an_unknown_connector_as_an_error_and_keeps_going():
    profile = Profile(sources=[SourceCfg(id="demo", kind="demo"), SourceCfg(id="paper", kind="rails", label="Paper")])
    snap = collect(profile, FRIDAY_EVENING)
    paper = next(s for s in snap.sources if s.id == "paper")
    assert paper.status == "error" and "not available" in paper.detail
    assert len(snap.accounts) == 6  # the demo still arrived


def test_collect_marks_a_source_stale_after_its_threshold():
    profile = Profile(sources=[SourceCfg(id="demo", kind="demo", stale_after="1m")])
    snap = collect(profile, FRIDAY_EVENING)
    assert {s.label: s.status for s in snap.sources}["Portfolio"] == "stale"  # last success 2 minutes ago


def test_the_demo_profile_greets_alex():
    assert DEMO_PROFILE.you.name == "Alex"


def _trade_for(snap, chart):
    matches = [t for t in snap.trades
               if (t.book_id, t.symbol, t.opened) == (chart.book_id, chart.symbol, chart.opened)]
    assert len(matches) == 1, (chart.book_id, chart.symbol, chart.opened)
    return matches[0]


def test_every_chart_matches_one_trade_and_its_prices_sit_inside_their_bars():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert snap.trade_charts
    for chart in snap.trade_charts:
        trade = _trade_for(snap, chart)
        dates = [b.date for b in chart.bars]
        assert dates == sorted(dates) and trade.opened in dates and trade.closed in dates
        assert all(b.low <= min(b.open, b.close) <= max(b.open, b.close) <= b.high for b in chart.bars)
        entry = chart.bars[dates.index(trade.opened)]
        leave = chart.bars[dates.index(trade.closed)]
        assert entry.open == trade.entry_price
        # bought at an open and sold at a later open; a same-day trade sells at that day's close
        assert (leave.open if trade.closed > trade.opened else leave.close) == trade.exit_price
        assert entry.low <= trade.entry_price <= entry.high and leave.low <= trade.exit_price <= leave.high


def test_each_book_charts_its_eight_most_recent_trades_with_about_thirty_sessions():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    for book in snap.books:
        trades = sorted((t for t in snap.trades if t.book_id == book.id), key=lambda t: (t.closed, t.opened, t.symbol))
        charts = [c for c in snap.trade_charts if c.book_id == book.id]
        assert {(c.symbol, c.opened) for c in charts} == {(t.symbol, t.opened) for t in trades[-8:]}
        assert all(len(c.bars) == 30 for c in charts)


def test_mean_reversion_charts_carry_rsi2_and_an_8_percent_stop():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    strategy_of = {b.id: b.strategy_id for b in snap.books}
    rsi2_charts = 0
    for chart in snap.trade_charts:
        trade = _trade_for(snap, chart)
        if strategy_of[chart.book_id] != "rsi2":
            assert chart.indicator is None and chart.stop is None
            continue
        rsi2_charts += 1
        assert chart.indicator is not None and chart.indicator.label == "RSI(2)"
        assert len(chart.indicator.values) == len(chart.bars) and chart.indicator.values[:2] == [None, None]
        assert all(0 <= v <= 100 for v in chart.indicator.values[2:])
        assert [(line.value, line.label) for line in chart.indicator.lines] == [
            (10, "buy under 10"), (70, "sell over 70")]
        assert chart.stop == round(trade.entry_price * 0.92, 2)
    assert rsi2_charts == 16  # the real and the paper book, 8 each


def test_mean_reversion_has_backtest_figures_and_a_watch_list():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    rsi2 = next(s for s in snap.strategies if s.id == "rsi2")
    assert rsi2.expected is not None and (rsi2.expected.cagr_pct, rsi2.expected.max_drawdown_pct) == (23.4, -11.7)
    assert [(w.symbol, w.label) for w in rsi2.watch] == [("KO", "RSI(2)"), ("ABT", "RSI(2)"), ("UNP", "RSI(2)")]
    assert all(w.value is not None and w.value < 20 for w in rsi2.watch)
    assert all(s.watch == [] for s in snap.strategies if s.id != "rsi2")


def test_every_account_has_a_type_and_its_holdings_and_cash_add_up_to_its_value():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert [(a.id, a.account_type) for a in snap.accounts] == [
        ("roth", "Roth IRA"), ("brokerage", "Brokerage"), ("trading", "Individual"), ("savings", "Savings"),
        ("checking", "Checking"), ("card", "Credit card")]
    for account in snap.accounts:
        if account.category == "debt":  # what is owed: nothing held, no cash
            assert account.cash == 0 and not any(h.account_id == account.id for h in snap.holdings)
            continue
        held = sum(h.value for h in snap.holdings if h.account_id == account.id)
        assert round(held + account.cash, 2) == account.value
        assert 0 <= account.cash <= account.value
    assert {h.account_id for h in snap.holdings} == {"roth", "brokerage", "trading"}  # the bank accounts hold cash


def _band(value, low, high):
    return "under" if low is not None and value < low else "over" if high is not None and value > high else "on"


def test_demo_has_every_new_block():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    today = dt.date(2026, 9, 25)
    accounts = {a.id: a for a in snap.accounts}
    # cash that earns, cash that doesn't, and a card
    assert (accounts["savings"].category, accounts["savings"].rate_pct) == ("cash", 4.1)
    assert (accounts["checking"].category, accounts["checking"].rate_pct) == ("cash", None)
    card = accounts["card"]
    assert (card.category, card.value, card.limit, card.rate_pct, card.cash) == ("debt", 640.0, 5000.0, 24.9, 0.0)

    # 8 targets: 6 percent targets with an aim and a band, a sleeve of two symbols with a band only, a ratio
    assert len(snap.targets) == 8 and len({t.id for t in snap.targets}) == 8
    percent = [t for t in snap.targets if t.unit == "%" and len(t.symbols) == 1]
    sleeve = [t for t in snap.targets if t.unit == "%" and len(t.symbols) == 2]
    ratio = [t for t in snap.targets if t.unit == "x"]
    assert len(percent) == 6 and all(None not in (t.target, t.low, t.high) and t.actual is None for t in percent)
    assert len(sleeve) == 1 and sleeve[0].target is None and None not in (sleeve[0].low, sleeve[0].high)
    assert len(ratio) == 1 and ratio[0].actual is not None
    assert {t.account_id for t in snap.targets} - {None} <= set(accounts)
    status = {}
    for t in percent + sleeve:  # the share of its account, from the holdings, as kestrel works it out
        share = sum(h.value for h in snap.holdings
                    if h.account_id == t.account_id and h.symbol in t.symbols) / accounts[t.account_id].value * 100
        status[t.id] = _band(share, t.low, t.high)
        assert min(abs(share - t.low), abs(share - t.high)) > 0.5  # clear of the band's edges as the values move
    status[ratio[0].id] = _band(ratio[0].actual, ratio[0].low, ratio[0].high)
    assert {"over", "under", "on"} <= set(status.values())

    # a thesis for every holding: 2 ok, 1 watch, 1 alert, the rest not rated; each says what would prove it wrong
    held = {h.symbol for h in snap.holdings}
    assert sorted(t.symbol for t in snap.theses) == sorted(held)
    health = [t.health for t in snap.theses]
    assert (health.count("ok"), health.count("watch"), health.count("alert")) == (2, 1, 1)
    assert health.count("none") == len(held) - 4
    assert all(t.reasons for t in snap.theses if t.health != "none")
    assert all(2 <= len(t.wrong_if) <= 3 for t in snap.theses)
    for t in snap.theses:
        assert set(t.account_ids) == {h.account_id for h in snap.holdings if h.symbol == t.symbol}
        assert t.opened is not None and t.last_reviewed is not None and t.opened <= t.last_reviewed <= today

    # 20 events within 60 days either side: results ahead, filings behind, 2 insider, 1 dividend
    assert len(snap.events) == 20
    assert all(abs((e.date - today).days) <= 60 for e in snap.events)
    kinds = [e.kind for e in snap.events]
    assert (kinds.count("insider"), kinds.count("dividend")) == (2, 1)
    assert all(e.date > today for e in snap.events if e.kind == "earnings") and "earnings" in kinds
    filings = [e for e in snap.events if e.kind == "filing"]
    assert filings and all(e.date < today and e.url.startswith("https://www.sec.gov/") for e in filings)
    assert any(e.symbol not in held for e in snap.events)  # something not held, too

    # a goal for an account, one for a category, one for net worth
    assert len(snap.goals) == 3
    assert sorted((g.account_id is not None, g.category is not None) for g in snap.goals) == [
        (False, False), (False, True), (True, False)]
    assert all(g.account_id is None or g.account_id in accounts for g in snap.goals)

    # exposures: what is held directly plus what the funds hold
    assert snap.exposures and len({e.symbol for e in snap.exposures}) == len(snap.exposures)
    for e in snap.exposures:
        assert e.sector and 0 <= e.direct <= e.value
        assert e.direct == round(sum(h.value for h in snap.holdings if h.symbol == e.symbol), 2)
    assert any(0 < e.direct < e.value for e in snap.exposures)  # held both ways
    assert any(e.direct == 0 < e.value for e in snap.exposures)  # only through a fund

    # 120 backtests over 12 families, develop and confirm: mostly fails, about 15 % passes, 2 refused, 3 pending
    assert len(snap.backtests) == 120 and len({b.id for b in snap.backtests}) == 120
    assert len({b.family for b in snap.backtests}) == 12
    assert {b.window for b in snap.backtests} == {"develop", "confirm"}
    verdicts = [b.verdict for b in snap.backtests]
    assert (verdicts.count("refused"), verdicts.count("pending")) == (2, 3)
    assert 0.12 <= verdicts.count("pass") / 120 <= 0.18 and verdicts.count("fail") > 60
    assert all(b.at <= FRIDAY_EVENING for b in snap.backtests)
    assert {b.strategy_id for b in snap.backtests} - {None} <= {s.id for s in snap.strategies}


def test_the_new_blocks_stay_put_as_the_dates_move():
    today = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    later = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING + dt.timedelta(days=7))
    assert [(b.id, b.verdict, b.t_stat) for b in today.backtests] == [(b.id, b.verdict, b.t_stat)
                                                                      for b in later.backtests]
    assert [(e.kind, e.symbol, e.title) for e in today.events] == [(e.kind, e.symbol, e.title) for e in later.events]
    assert [t.health for t in today.theses] == [t.health for t in later.theses]


def test_the_cash_accounts_move_only_by_what_goes_in_and_out_and_the_card_is_paid_in_full():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    history = {s.id: s.points for s in snap.account_history}
    checking, card = history["checking"], history["card"]
    assert min(p.value for p in checking) > 0
    for series in (checking, card):
        assert len(series) == len(history["roth"]) and series[0].net_flow == 0
    # checking changes by its flows alone; a card's balance moves against them: a payment in lowers what is owed
    assert all(round(b.value - a.value - b.net_flow, 2) == 0 for a, b in zip(checking, checking[1:]))
    assert all(round(b.value - a.value + b.net_flow, 2) == 0 for a, b in zip(card, card[1:]))
    assert min(p.value for p in card) >= 0 and card[-1].value == 640.0


def test_holdings_are_priced_consistently_and_the_trading_account_holds_the_real_books_positions():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert all(h.value == round(h.quantity * h.price, 2) and h.name for h in snap.holdings)
    trading = {h.symbol: h.quantity for h in snap.holdings if h.account_id == "trading"}
    assert trading == {p.symbol: p.quantity for p in snap.positions if p.book_id == "rsi2-real"}
    assert [h.symbol for h in snap.holdings if h.cost_basis is None] == ["KO"]  # a cost the broker never reported
    assert len({h.symbol for h in snap.holdings}) == 13
