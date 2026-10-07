"""Fictional demo data: a believable year for "Alex".

Deterministic for a seed: the numbers never change, only the dates move so the last point is today.
Nothing here is anyone's real account; the tickers are ordinary large caps and sector funds, and what the demo says
about them (theses, events, fund weights, research results) is invented for the example.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..contract import (
    Account,
    Backtest,
    Bar,
    Benchmark,
    Book,
    Criterion,
    Decision,
    Event,
    Expected,
    Exposure,
    Goal,
    Holding,
    Indicator,
    IndicatorLine,
    Position,
    Review,
    RuleVersion,
    Run,
    Series,
    Snapshot,
    Source,
    Step,
    Strategy,
    Target,
    Thesis,
    Trade,
    TradeChart,
    Transaction,
    ValuePoint,
    WatchItem,
)
from ..metrics import rsi

DAYS = 262  # about a year of weekdays
MARKET_DRIFT, MARKET_VOL = 0.00022, 0.0085  # a daily market factor every account leans on
STOCKS = ["HD", "LOW", "MRK", "PEP", "WMT", "TXN", "MCD", "KO", "ABT", "UNP", "ORCL", "COST", "UNH", "CSCO", "HON"]
FUNDS = ["XLE", "XLK", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "SPY"]
# backtest share of trades (%) per 1-point bucket from -10% to +10%; sums to 100
RSI2_DISTRIBUTION = [
    0.2, 3.1, 1.2, 0.3, 0.6, 1.1, 2.0, 4.9, 9.2, 10.9, 11.8, 14.6, 17.3, 12.1, 6.4, 2.6, 1.0, 0.4, 0.2, 0.1,
]
CHARTED = 8  # each book's most recent closed trades that get a chart
CHART_BARS = 30  # sessions of daily bars per chart
RSI2_LINES = [IndicatorLine(value=10, label="buy under 10"), IndicatorLine(value=70, label="sell over 70")]
# what the long-term accounts hold: (symbol, name, share of the account, cost as a share of today's value, or None
# when the broker never reported it); what is left over is cash
LONG_TERM_HOLDINGS = {
    "roth": [("SPY", "S&P 500 index fund", 0.62, 0.78), ("XLV", "Health care sector fund", 0.21, 0.93),
             ("XLP", "Consumer staples sector fund", 0.16, 1.04)],
    "brokerage": [("SPY", "S&P 500 index fund", 0.38, 0.81), ("XLK", "Technology sector fund", 0.22, 0.74),
                  ("COST", "Costco", 0.12, 0.66), ("HD", "Home Depot", 0.10, 0.97),
                  ("XLE", "Energy sector fund", 0.08, 1.12), ("KO", "Coca-Cola", 0.05, None),
                  ("XLI", "Industrials sector fund", 0.04, 0.90)],
}
PRICES = {"SPY": 661.20, "XLV": 142.35, "XLP": 79.10, "XLK": 281.40, "COST": 912.55, "HD": 404.66, "XLE": 88.25,
          "KO": 69.90, "XLI": 151.30}
NAMES = {"MSFT": "Microsoft", "CAT": "Caterpillar", "PG": "Procter & Gamble", "JPM": "JPMorgan Chase"}

# The bank: pay lands in checking every other Friday; on each month's first weekday it pays the rent and the monthly
# deposits into the other accounts; every CARD_CYCLE weekdays it pays the card in full, the last time CARD_PAID
# weekdays ago, so what the card owes today is the charges since then: CARD_OWED.
CHECKING_START, PAY, RENT = 6200.0, 2250.0, 2200.0
CARD_CYCLE, CARD_PAID, CARD_OWED = 21, 9, 640.0
MONTHLY_SPEND = 3500.0  # rent and a month of card charges, for the cash runway

# What the plan says the long-term accounts should hold, in percent of each account (the demo's holdings sit well
# inside or well outside each band, so a target's status doesn't flip as the dates move)
TARGETS = [
    Target(id="roth-spy", account_id="roth", label="SPY", symbols=["SPY"], target=60, low=55, high=65,
           note="The core: the whole market"),
    Target(id="roth-xlv", account_id="roth", label="XLV", symbols=["XLV"], target=15, low=12, high=18,
           note="A health care tilt"),
    Target(id="roth-xlp", account_id="roth", label="XLP", symbols=["XLP"], target=20, low=18, high=22,
           note="Staples to soften the drops"),
    Target(id="brokerage-spy", account_id="brokerage", label="SPY", symbols=["SPY"], target=40, low=35, high=45,
           note="The core: the whole market"),
    Target(id="brokerage-xlk", account_id="brokerage", label="XLK", symbols=["XLK"], target=20, low=15, high=25,
           note="Technology, capped"),
    Target(id="brokerage-ko", account_id="brokerage", label="KO", symbols=["KO"], target=5, low=3, high=7,
           note="A dividend holding"),
    Target(id="brokerage-stocks", account_id="brokerage", label="Single stocks", symbols=["COST", "HD"], low=15,
           high=25, note="Two companies held for the long run"),
]

# Why each holding is owned: symbol → (health, conviction, reasons, wrong if, days since opened, days since the last
# review). The real book's trades share one thesis (THESIS_TRADE), dated from the day the position opened.
THESES = {
    "SPY": ("ok", "high", ["The index core: its only risk is the market's own"],
            ["It trails a world index fund by 20 points over five years", "Its yearly cost rises above 0.10 %"],
            880, 14),
    "COST": ("ok", "high", ["Membership renewals held above 90 %", "Margins steady for four quarters"],
             ["The renewal rate falls below 88 %", "Comparable sales shrink for two quarters",
              "It costs more than 60 times earnings while growing under 8 % a year"], 1020, 21),
    "XLE": ("watch", "low", ["Oil fell for three months in a row", "Two large holdings cut their buyback plans"],
            ["Oil stays under 60 a barrel for six months", "The fund's dividend is cut"], 430, 30),
    "HD": ("alert", "medium",
           ["Comparable sales fell for a third quarter", "The price closed below its 200-day average"],
           ["Comparable sales fall for a fourth quarter", "Home sales stay near their lows for another year"], 760, 7),
    "XLV": ("none", "medium", [], ["Drug-price rules cut the sector's earnings by a fifth",
                                   "It trails the S&P 500 by 15 points over three years"], 610, 120),
    "XLP": ("none", "medium", [], ["It falls as far as the market in the next 10 % drop", "Its dividend is cut"],
            540, 95),
    "XLK": ("none", "medium", [], ["Its five largest names pass 60 % of the fund",
                                   "Its holdings' earnings grow slower than the market's for a year"], 700, 60),
    "KO": ("none", "high", [], ["Volumes shrink for a year", "The dividend grows slower than prices for three years",
                                "It pays out more than it earns"], 1200, 180),
    "XLI": ("none", "low", [], ["Factory orders shrink for two quarters",
                                "It trails the S&P 500 by 10 points over two years"], 300, 75),
}
THESIS_TRADE = ["It closes under its stop", "It falls below its 200-day average before the bounce"]

# Dated things about the companies, as days from today: (days, symbol, kind, title, detail, SEC form or "")
EVENTS = [
    (8, "COST", "earnings", "Quarterly results", "After the close", ""),
    (11, "KO", "dividend", "Ex-dividend date", "Own it the day before to receive the quarterly dividend", ""),
    (12, "JPM", "earnings", "Quarterly results", "Before the open", ""),
    (16, "KO", "earnings", "Quarterly results", "Before the open", ""),
    (19, "PG", "earnings", "Quarterly results", "Before the open", ""),
    (26, "MSFT", "earnings", "Quarterly results", "After the close", ""),
    (33, "CAT", "earnings", "Quarterly results", "Before the open", ""),
    (41, "ORCL", "earnings", "Quarterly results", "After the close", ""),  # watched, not held
    (52, "HD", "earnings", "Quarterly results", "Before the open", ""),
    (-3, "MSFT", "filing", "Form 8-K", "Current report", "8-K"),
    (-6, "CAT", "insider", "A director bought shares", "Form 4", "4"),
    (-9, "KO", "filing", "Form 8-K", "Current report", "8-K"),
    (-14, "COST", "filing", "Form 10-K", "Annual report", "10-K"),
    (-18, "HD", "insider", "An officer sold shares", "Form 4", "4"),
    (-20, "JPM", "filing", "Form 8-K", "Current report", "8-K"),
    (-27, "HD", "filing", "Form 10-Q", "Quarterly report", "10-Q"),
    (-34, "PG", "filing", "Form 10-K", "Annual report", "10-K"),
    (-41, "CAT", "filing", "Form 10-Q", "Quarterly report", "10-Q"),
    (-48, "MSFT", "filing", "Form 10-K", "Annual report", "10-K"),
    (-55, "JPM", "filing", "Form 10-Q", "Quarterly report", "10-Q"),
]
EDGAR = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={symbol}&type={form}"

# Looking through the funds: an illustrative share (%) of a few companies inside each fund the demo holds
LOOK_THROUGH = {
    "SPY": {"MSFT": 6.6, "JPM": 1.5, "COST": 0.9, "HD": 0.8, "PG": 0.8, "KO": 0.6, "CAT": 0.4, "ABT": 0.4, "UNP": 0.3},
    "XLK": {"MSFT": 13.5},
    "XLV": {"ABT": 5.4},
    "XLP": {"COST": 9.8, "PG": 8.9, "KO": 6.1},
    "XLI": {"CAT": 4.6, "UNP": 3.1},
}
COMPANIES = {  # symbol → (name, sector)
    "MSFT": ("Microsoft", "Technology"), "JPM": ("JPMorgan Chase", "Financials"),
    "COST": ("Costco", "Consumer staples"), "HD": ("Home Depot", "Consumer discretionary"),
    "PG": ("Procter & Gamble", "Consumer staples"),
    "KO": ("Coca-Cola", "Consumer staples"), "CAT": ("Caterpillar", "Industrials"),
    "ABT": ("Abbott Laboratories", "Health care"), "UNP": ("Union Pacific", "Industrials"),
}

# The research record: nine candidates a family tried in the develop window; the passes went on to confirm
FAMILIES = ["Dip buy", "Close strength", "Opening range", "Gap fade", "Trend pullback", "Breakout", "Overnight hold",
            "Momentum rank", "Volatility squeeze", "Pairs spread", "Turn of the month", "Weekly reversal"]
CANDIDATES = 9
DEVELOP_PASSES = [3, 3, 0, 1, 2, 0, 1, 2, 0, 1, 1, 0]
DEVELOP_PENDING = {11: 2}  # the newest family's last two are still running
# what each family's develop passes met in the confirm window, oldest first; a pass without one still waits for it
CONFIRMS = {0: ["pass", "fail", "fail"], 1: ["pass", "fail", "refused"], 3: ["fail"], 4: ["pass", "fail"],
            6: ["refused"], 7: ["pass", "pending"]}
REFUSED = {1: "refused: the confirm window is already spent for this family",
           6: "refused: too few trades in the develop window to judge"}
# the confirmed passes that became the demo's strategies, with the figures their strategy page quotes
LIVE = {0: ("rsi2", 240, 0.84, 3.4, 2.0, -11.7), 1: ("ibs", 188, 0.41, 2.6, 1.4, -8.2)}
# what each confirmed pass rests on: the configuration, sizing, costs, sample and the caveats that travel with it
LIVE_BASIS = {
    "rsi2": {"config": "15 large US stocks above their 200-day average; RSI(2) < 10 in, > 70 out; next-open fills",
             "sizing": "$6,000 fixed lots, 6 slots, in a $100,000 book", "costs": "None modelled: commission-free; "
             "the next-open fill is the live model", "sample": "240 trades, 2006–2020", "cagr_pct": 23.4,
             "caveats": ["Fixed $6,000 lots keep about a fifth of the book working; the live book sizes at the "
                         "account ÷ 6", "Today's names tested back to 2006: survivors by construction"]},
    "ibs": {"config": "9 sector funds; IBS < 0.2 at the close in, own IBS > 0.8 out; fills at the close",
            "sizing": "A $3,200 book, 4 slots, each lot equity at cost ÷ 4", "costs": "1¢ a side (about 5 bp)",
            "sample": "188 trades, 2021–2024, after a develop window of 2000–2020", "cagr_pct": 12.5,
            "caveats": ["Chosen from six develop configurations: a real pass with an inflated false-positive rate",
                        "Two partial years in the confirm window, one of them weak",
                        "Buys and sells at the official close; the runner reads a few minutes before it",
                        "A lot exits only on its own strength: a fund in a long slide can hold a slot for weeks"]},
}
# Sessions old a mark can be before a page says so; the demo marks everything at the last session
REVIEW_TRADES = 20


def weekdays_ending(end: date, count: int) -> list[date]:
    """The `count` weekdays up to and including `end` (or the Friday before, on a weekend), oldest first."""
    days: list[date] = []
    day = end
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return days[::-1]


def _next_weekday_at(now: datetime, at: time) -> datetime:
    candidate = datetime.combine(now.date(), at, tzinfo=now.tzinfo)
    while candidate <= now or candidate.weekday() >= 5:
        candidate = datetime.combine(candidate.date() + timedelta(days=1), at, tzinfo=now.tzinfo)
    return candidate


def _monthly(days: list[date], amount: float) -> list[float]:
    return [amount if i > 0 and days[i].month != days[i - 1].month else 0.0 for i in range(len(days))]


def _walk(rng: random.Random, start: float, market: list[float], beta: float, drift: float, vol: float,
          flows: list[float]) -> list[float]:
    values = [start]
    for i in range(1, len(market)):
        step = drift + beta * market[i] + rng.gauss(0.0, vol)
        values.append(round(values[-1] * (1.0 + step) + flows[i], 2))
    return values


def _points(days: list[date], values: list[float], flows: list[float]) -> list[ValuePoint]:
    return [ValuePoint(date=d, value=v, net_flow=f) for d, v, f in zip(days, values, flows)]


def _holdings(account_id: str, value: float) -> list[Holding]:
    """Whole thousandths of a share, so the cash left over is never negative."""
    out = []
    for symbol, name, share, cost in LONG_TERM_HOLDINGS[account_id]:
        price = PRICES[symbol]
        quantity = math.floor(value * share / price * 1000) / 1000
        worth = round(quantity * price, 2)
        out.append(Holding(account_id=account_id, symbol=symbol, name=name, quantity=quantity, price=price,
                           value=worth, cost_basis=round(worth * cost, 2) if cost is not None else None))
    return out


def _cash(holdings: list[Holding], account_id: str, value: float) -> float:
    return round(value - sum(h.value for h in holdings if h.account_id == account_id), 2)


def _trades(rng: random.Random, book_id: str, days: list[date], count: int, *, win_p: float, win_mu: float,
            loss_mu: float, stop_every: int = 0, stop_pct: float | None = None, hold: tuple[int, int] = (1, 6),
            lot: float = 3000.0, pool: list[str] = STOCKS) -> list[Trade]:
    trades: list[Trade] = []
    span = max(1, len(days) - 8)
    for k in range(count):
        opened_i = min(len(days) - 2, 2 + (k * span) // count + rng.randint(0, 2))
        closed_i = min(opened_i + rng.randint(*hold), len(days) - 2)
        if stop_every and k % stop_every == stop_every - 1:
            ret, reason = -(stop_pct or 8.0) - rng.random() * 0.4, "stop"
        elif rng.random() < win_p:
            ret, reason = win_mu * (0.3 + rng.random() * 1.4), "signal"
        else:
            ret, reason = loss_mu * (0.3 + rng.random() * 1.4), "signal"
        entry = round(40 + rng.random() * 460, 2)
        quantity = max(1, int(lot // entry))
        exit_price = round(entry * (1 + ret / 100), 2)
        trades.append(Trade(
            book_id=book_id, symbol=pool[rng.randrange(len(pool))], opened=days[opened_i], closed=days[closed_i],
            entry_price=entry, exit_price=exit_price, quantity=quantity, pnl=round((exit_price - entry) * quantity, 2),
            return_pct=round(ret, 2), r_multiple=round(ret / stop_pct, 2) if stop_pct else None, exit_reason=reason,
        ))
    return trades


def _chart(trade: Trade, days: list[date], seed: str, rsi2: bool) -> TradeChart:
    """About 30 sessions of bars around a trade: the entry bar opens at the entry price and the exit bar at the exit
    price (a same-day trade closes at it). Mean reversion adds RSI(2) and its 8% stop."""
    rng = random.Random(seed)
    e, x = days.index(trade.opened), days.index(trade.closed)
    end = min(len(days) - 1, x + 5)
    start = max(0, end - CHART_BARS + 1)
    opens: dict[int, float] = {e: trade.entry_price}
    gaps = {i: rng.gauss(0.0, 0.002) for i in range(start, end + 1)}  # each close to the next open
    if x > e:
        opens[x] = trade.exit_price
        for i in range(e + 1, x):
            t = (i - e) / (x - e)
            wobble = rng.gauss(0.0, 0.012) * (t * (1 - t)) ** 0.5
            opens[i] = trade.entry_price + (trade.exit_price - trade.entry_price) * t + trade.entry_price * wobble
    else:
        opens[e + 1] = trade.exit_price  # sold at the close: the entry bar closes at the exit price
        gaps[e] = 0.0
    for i in range(e - 1, start - 1, -1):  # back from the entry: a slide into the signal, an uptrend before it
        move = -0.008 - rng.random() * 0.012 if i >= e - 2 else rng.gauss(0.002, 0.012)
        opens[i] = opens[i + 1] / (1 + move)
    for i in range(max(opens) + 1, end + 1):
        opens[i] = opens[i - 1] * (1 + rng.gauss(0.001, 0.012))
    bars: list[Bar] = []
    for i in range(start, end + 1):
        o = round(opens[i], 2)
        c = round(opens[i + 1] * (1 + gaps[i]) if i < end else o * (1 + rng.gauss(0.0, 0.01)), 2)
        high = round(max(o, c) * (1 + abs(rng.gauss(0.0, 0.005))), 2)
        low = round(min(o, c) * (1 - abs(rng.gauss(0.0, 0.005))), 2)
        bars.append(Bar(date=days[i], open=o, high=high, low=low, close=c))
    indicator = stop = None
    if rsi2:
        values = [None if v is None else round(v, 1) for v in rsi([b.close for b in bars])]
        indicator = Indicator(label="RSI(2)", values=values, lines=RSI2_LINES)
        stop = round(trade.entry_price * 0.92, 2)
    return TradeChart(book_id=trade.book_id, symbol=trade.symbol, opened=trade.opened, bars=bars,
                      indicator=indicator, stop=stop)


def _charts(book: Book, trades: list[Trade], days: list[date], seed: int) -> list[TradeChart]:
    own = [t for t in trades if t.book_id == book.id]
    recent = sorted(range(len(own)), key=lambda k: (own[k].closed, own[k].opened, own[k].symbol))[-CHARTED:]
    # seeded by the trade's place in its book, so a chart keeps its shape as the dates move
    return [_chart(own[k], days, f"{seed}:{book.id}:{k}", book.strategy_id == "rsi2") for k in recent]


def _card(days: list[date], seed: int) -> tuple[list[float], list[float], list[float]]:
    """What the card owes each day, its flows (a payment in, a charge out) and each day's payment. Paid in full every
    CARD_CYCLE weekdays counted back from today, so it owes CARD_OWED today whatever the date; the charges since the
    last payment are scaled to add up to it."""
    rng = random.Random(f"{seed}:card")
    n = len(days)
    charges = [round(rng.uniform(10.0, 110.0), 2) for _ in range(n)]
    last_paid = n - 1 - CARD_PAID
    since = charges[last_paid:]
    scaled = [round(c * CARD_OWED / sum(since), 2) for c in since[:-1]]
    charges[last_paid:] = [*scaled, round(CARD_OWED - sum(scaled), 2)]
    owed, flows, payments = [round(rng.uniform(300.0, 900.0), 2)], [0.0], [0.0]
    for i in range(1, n):
        paid = owed[-1] if (n - 1 - i) % CARD_CYCLE == CARD_PAID else 0.0
        owed.append(round(owed[-1] - paid + charges[i], 2))
        flows.append(round(paid - charges[i], 2))
        payments.append(paid)
    return owed, flows, payments


TRANSACTION_DAYS = 90  # what a bank feed carries
MERCHANTS = (("Grocery Mart", "groceries"), ("Coffee Bar", "dining"), ("Fuel Stop", "transport"),
             ("Streaming Service", "subscriptions"), ("Pharmacy", "health"), ("Bookshop", "shopping"),
             ("Hardware Store", "home"))


def _transactions(days: list[date], seed: int, *, card_flows: list[float], card_payments: list[float],
                  savings_flows: list[float], deposits: list[tuple[str, list[float]]]) -> list[Transaction]:
    """Ninety days of posted rows for the bank accounts. Each day's rows add up to the account's flow that day (the
    demo's bank moves by its flows alone, so the rows and the history can't disagree): checking's pay, rent, the
    transfers into the other accounts and the card's payment; the card's charges at fictional merchants and its
    payments; savings' deposits."""
    rng = random.Random(f"{seed}:transactions")
    first = days[-1] - timedelta(days=TRANSACTION_DAYS)
    rows: list[Transaction] = []
    for i, day in enumerate(days):
        if i == 0 or day < first:
            continue
        pay = PAY if day.weekday() == 4 and day.toordinal() // 7 % 2 == 0 else 0.0
        rent = RENT if day.month != days[i - 1].month else 0.0
        if pay:
            rows.append(Transaction(account_id="checking", date=day, amount=pay, description="Payroll deposit",
                                    counterparty="Employer", category="income"))
        if rent:
            rows.append(Transaction(account_id="checking", date=day, amount=-rent, description="Rent",
                                    counterparty="Landlord", category="housing"))
        for label, flows in deposits:
            if flows[i]:
                rows.append(Transaction(account_id="checking", date=day, amount=-flows[i],
                                        description=f"Transfer to {label}", category="transfer"))
        if card_payments[i]:
            rows.append(Transaction(account_id="checking", date=day, amount=-card_payments[i],
                                    description="Card payment", counterparty="Bank D", category="transfer"))
            rows.append(Transaction(account_id="card", date=day, amount=card_payments[i],
                                    description="Payment from checking", counterparty="Bank C", category="payment"))
        charge = round(card_payments[i] - card_flows[i], 2)
        if charge:
            merchant, category = rng.choice(MERCHANTS)
            rows.append(Transaction(account_id="card", date=day, amount=-charge, description=merchant.upper(),
                                    counterparty=merchant, category=category))
        if savings_flows[i]:
            rows.append(Transaction(account_id="savings", date=day, amount=savings_flows[i],
                                    description="Transfer from checking", category="transfer"))
    return rows


def _checking(days: list[date], transfers: list[float], card_payments: list[float]) -> tuple[list[float], list[float]]:
    """Checking's balance and flows. Pay comes in every other Friday; out go the rent and `transfers` (the deposits
    into the other accounts, which count as money in there) and the card's payments. It earns nothing, so it moves by
    its flows alone, and money moved between Alex's own accounts nets to nothing in the net worth."""
    flows = [0.0]
    for i in range(1, len(days)):
        pay = PAY if days[i].weekday() == 4 and days[i].toordinal() // 7 % 2 == 0 else 0.0
        rent = RENT if days[i].month != days[i - 1].month else 0.0
        flows.append(round(pay - rent - transfers[i] - card_payments[i], 2))
    values = [CHECKING_START]
    for flow in flows[1:]:
        values.append(round(values[-1] + flow, 2))
    return values, flows


def _theses(holdings: list[Holding], positions: list[Position], today: date) -> list[Thesis]:
    """One thesis per symbol held, in the order the holdings list them."""
    accounts: dict[str, list[str]] = {}
    names: dict[str, str] = {}
    for h in holdings:
        accounts.setdefault(h.symbol, [])
        if h.account_id not in accounts[h.symbol]:
            accounts[h.symbol].append(h.account_id)
        names.setdefault(h.symbol, h.name)
    opened = {p.symbol: p.opened for p in positions if p.book_id == "rsi2-real"}
    out = []
    for symbol, held_in in accounts.items():
        if symbol in THESES:
            health, conviction, reasons, wrong_if, since, reviewed = THESES[symbol]
            out.append(Thesis(symbol=symbol, name=names[symbol], health=health, reasons=reasons,
                              conviction=conviction, opened=today - timedelta(days=since),
                              last_reviewed=today - timedelta(days=reviewed), wrong_if=wrong_if, account_ids=held_in))
        else:  # a trade the real book holds: a short-term thesis, written the day it opened
            out.append(Thesis(symbol=symbol, name=names[symbol], conviction="low", opened=opened[symbol],
                              last_reviewed=opened[symbol], wrong_if=THESIS_TRADE, account_ids=held_in))
    return out


def _events(today: date) -> list[Event]:
    """EVENTS on weekdays: one due on a weekend moves on to the Monday ahead, or back to the Friday behind."""
    out = []
    for days_away, symbol, kind, title, detail, form in EVENTS:
        day = today + timedelta(days=days_away)
        while day.weekday() >= 5:
            day += timedelta(days=1 if days_away > 0 else -1)
        out.append(Event(date=day, symbol=symbol, kind=kind, title=title, detail=detail,
                         url=EDGAR.format(symbol=symbol, form=form) if form else ""))
    return out


def _goals(today: date) -> list[Goal]:
    return [
        Goal(id="roth-grow", label="Grow the Roth IRA", target=100000.0, account_id="roth",
             by=date(today.year + 4, 12, 31), note="The monthly deposit, and time"),
        Goal(id="cash-year", label="A year of spending in cash", target=12 * MONTHLY_SPEND, category="cash",
             by=date(today.year + 1, 12, 31), note="Twelve months of rent and card spending"),
        Goal(id="net-worth", label="Net worth milestone", target=250000.0, by=date(today.year + 3, 6, 30),
             note="Everything owned, less what is owed"),
        Goal(id="long-term-together", label="Long-term accounts combined", target=200000.0,
             account_ids=["roth", "brokerage"], by=date(today.year + 5, 12, 31),
             note="Roth IRA and brokerage together"),
        Goal(id="save-this-year", label="Save into savings this year", target=12 * 150.0, account_id="savings",
             measure="deposits", by=date(today.year, 12, 31), note="What goes into savings each month"),
    ]


def _exposures(holdings: list[Holding]) -> list[Exposure]:
    """Each company in COMPANIES: what is held of it directly plus its share of each fund held; largest first."""
    direct: dict[str, float] = {}
    through: dict[str, float] = {}
    for h in holdings:
        if h.symbol in COMPANIES:
            direct[h.symbol] = direct.get(h.symbol, 0.0) + h.value
        for symbol, weight in LOOK_THROUGH.get(h.symbol, {}).items():
            through[symbol] = through.get(symbol, 0.0) + h.value * weight / 100
    out = [Exposure(symbol=symbol, name=name, sector=sector, direct=round(direct.get(symbol, 0.0), 2),
                    value=round(direct.get(symbol, 0.0) + through.get(symbol, 0.0), 2))
           for symbol, (name, sector) in COMPANIES.items()]
    return sorted(out, key=lambda e: (-e.value, e.symbol))


def _measured(rng: random.Random, verdict: str, window: str) -> dict[str, float | int]:
    """A result's figures: a pass clears t 2 with a positive average trade; a fail doesn't."""
    develop = window == "develop"
    if verdict == "pass":
        avg = rng.uniform(0.2, 0.9 if develop else 0.7)
        t = rng.uniform(2.05, 4.2 if develop else 3.3)
        trades = rng.randint(80, 420) if develop else rng.randint(40, 160)
        calmar, drop = rng.uniform(0.6, 2.2), rng.uniform(5.0, 18.0)
    else:
        avg = rng.uniform(-0.45, 0.3)
        t = math.copysign(rng.uniform(0.05, 1.95), avg)
        trades = rng.randint(15, 520) if develop else rng.randint(30, 160)
        calmar, drop = math.copysign(rng.uniform(0.02, 0.7), avg), rng.uniform(6.0, 38.0)
    return {"trades": trades, "avg_trade_pct": round(avg, 2), "t_stat": round(t, 2), "calmar": round(calmar, 2),
            "max_drawdown_pct": round(-drop, 1)}


def _backtests(now: datetime, seed: int) -> list[Backtest]:
    """FAMILIES × CANDIDATES develop results about three days apart over the past year, then each pass's confirm
    result a few days later (CONFIRMS); oldest first. Seeded apart from the market, so the record never moves."""
    rng = random.Random(f"{seed}:backtests")
    out: list[Backtest] = []
    k = 0
    for f, family in enumerate(FAMILIES):
        slug = family.lower().replace(" ", "-")
        running = DEVELOP_PENDING.get(f, 0)
        passes = set(rng.sample(range(CANDIDATES - running), DEVELOP_PASSES[f]))
        confirms = iter(CONFIRMS.get(f, []))
        live = LIVE.get(f)
        for c in range(CANDIDATES):
            letter = chr(ord("A") + c)
            name, ident = f"{family} {letter}", f"{slug}-{letter.lower()}"
            at = now - timedelta(days=330 - 3 * k, hours=rng.randint(0, 8))
            k += 1
            if c >= CANDIDATES - running:
                out.append(Backtest(id=f"{ident}-develop", name=name, family=family, window="develop",
                                    verdict="pending", at=now - timedelta(hours=CANDIDATES - c), note="running"))
                continue
            verdict = "pass" if c in passes else "fail"
            out.append(Backtest(id=f"{ident}-develop", name=name, family=family, window="develop", verdict=verdict,
                                at=at, **_measured(rng, verdict, "develop")))
            outcome = next(confirms, None) if verdict == "pass" else None
            if outcome is None:
                continue
            confirm = {"id": f"{ident}-confirm", "name": name, "family": family, "window": "confirm",
                       "verdict": outcome}
            if outcome == "pending":
                out.append(Backtest(**confirm, at=now - timedelta(hours=3), note="running"))
            elif outcome == "refused":
                out.append(Backtest(**confirm, at=at + timedelta(days=1), note=REFUSED[f]))
            elif outcome == "pass" and live is not None:
                strategy_id, trades, avg, t, calmar, drop = live
                live = None  # the family's first confirmed pass is the one that runs
                out.append(Backtest(**confirm, at=at + timedelta(days=rng.randint(2, 6)), strategy_id=strategy_id,
                                    trades=trades, avg_trade_pct=avg, t_stat=t, calmar=calmar, max_drawdown_pct=drop,
                                    **LIVE_BASIS[strategy_id]))
            else:
                out.append(Backtest(**confirm, at=at + timedelta(days=rng.randint(2, 6)),
                                    **_measured(rng, outcome, "confirm")))
    return sorted(out, key=lambda b: (b.at, b.id))


def _rsi2_rules(days: list[date]) -> tuple[list[RuleVersion], date]:
    """The real book's written rules, dated against the demo's calendar: by hand first, then the system, then a
    sizing change. The second is the day the system took over the entries."""
    system_from = days[-60]
    return [
        RuleVersion(version="v1.0", effective=days[0] - timedelta(days=5), placed_by="hand",
                    summary="The RSI(2) rules run by hand each evening: entries and exits placed by Alex"),
        RuleVersion(version="v2.0", effective=system_from, placed_by="system",
                    summary="The rules written down as the system runs them; the runner queues, the autopilot places; "
                    "held through earnings"),
        RuleVersion(version="v2.1", effective=days[-5], placed_by="system",
                    summary="Sizing floats with the account: a lot is the account value ÷ 6, at most $1,000 an order"),
    ], system_from


def _strategies(days: list[date], ibs_days: list[date]) -> list[Strategy]:
    rules, system_from = _rsi2_rules(days)
    review_from = days[-20]  # the last review, four weeks ago; the next is due after 20 trades or in 45 days
    return [
    Strategy(
        id="rsi2", name="Mean reversion", summary="Buys large, liquid stocks after a sharp short-term drop inside an "
        "uptrend, and sells into the bounce — usually within a week.",
        steps=[
            Step(label="Universe", title="Large US stocks", text="Only while the stock sits above its 200-day average",
                 params=["200-day filter"]),
            Step(label="Entry", title="Buy after a sharp drop",
                 text="RSI(2) closes under 10 → a buy limit 1% over the close, good for the next session; the lowest "
                 "RSI first when signals outnumber slots",
                 params=["RSI(2) < 10", "limit = close × 1.01", "next session"]),
            Step(label="Protect", title="A stop rests at the broker", text="8% under the buy price — never lowered",
                 params=["−8% stop", "GTC"]),
            Step(label="Exit", title="Sell into the bounce",
                 text="RSI(2) closes over 70 → sold at the next open, underwater too; the stop or a −8% / +20% "
                 "backstop otherwise. No time stop; held through earnings",
                 params=["RSI(2) > 70", "next open", "or stop"]),
            Step(kind="gate", label="Regime", title="No new entries risk-off",
                 text="While SPY is under its 200-day average no entry is placed; exits and stops still run",
                 params=["SPY < 200-day"]),
            Step(kind="gate", label="Daily loss", title="Buying stops after a $40 day",
                 text="Once the day's realized loss reaches $40 no new buy is placed until tomorrow",
                 params=["−$40 halt"]),
            Step(kind="gate", label="Caps", title="Five lots, $1,000 an order",
                 text="At most 5 open lots, $1,000 per order, 10 orders and 6 decisions a day",
                 params=["5 lots", "$1,000 / order", "10 orders / day"]),
            Step(kind="gate", label="Kill file", title="One file halts all new risk",
                 text="A kill file, placed from the phone too, stops every new order; open lots keep their stops",
                 params=["kill file"]),
        ],
        sizing="Each position is the account value ÷ 6, at most 5 open.",
        expected=Expected(win_rate=66, avg_trade_pct=0.84, avg_win_pct=2.45, avg_loss_pct=-2.28, trades_per_month=3.1,
                          sd_trade_pct=3.0, distribution=RSI2_DISTRIBUTION, source="backtest", window="2006–2020",
                          max_drawdown_pct=-11.7, stage="confirm, production configuration",
                          **LIVE_BASIS["rsi2"]),
        review_at_trades=REVIEW_TRADES,
        rules_version=rules[-1].version, rules_effective=rules[-1].effective, rules_history=rules,
        review=Review(label="System review", at_trades=REVIEW_TRADES, counted_since=review_from,
                      by=review_from + timedelta(days=45), last_at=review_from,
                      last_note="The rules were written down as v2.0. 16 trades scored, 15 followed the plan: too few "
                      "for a verdict on the edge.",
                      doc="Swing plan v2.1 §9",
                      criteria=[
                          Criterion(key="followed", label="Plan followed", measure="Scored trades since the review",
                                    target="≥ 90%", value="100% of 8", status="pass"),
                          Criterion(key="system", label="Entries placed by the system",
                                    measure="System entries ÷ entries", target="100%", value="100%", status="pass"),
                          Criterion(key="expectancy", label="Expectancy", measure="Average return per trade",
                                    target="Read against +0.84% over 30–50 trades", value="+0.79%", status="info"),
                          Criterion(key="drawdown", label="Worst drop", measure="From the book's peak",
                                    target="Halt everything at −15%", value="−2.1%", status="pass"),
                      ]),
        watch=[WatchItem(symbol="KO", label="RSI(2)", value=12.4), WatchItem(symbol="ABT", label="RSI(2)", value=16.8),
               WatchItem(symbol="UNP", label="RSI(2)", value=19.1)],
    ),
    Strategy(
        id="ibs", name="ETF close strength",
        summary="Buys a sector fund that closes near the bottom of its day's range and holds until it closes near "
        "the top.",
        steps=[
            Step(label="Universe", title="Nine sector funds", text="Broad sector funds, none of them in the stock book",
                 params=["9 funds"]),
            Step(label="Entry", title="Buy a weak close",
                 text="IBS under 0.2 a few minutes before the close → a marketable limit at the close, deepest first "
                 "into free slots", params=["IBS < 0.2", "at the close"]),
            Step(label="Exit", title="Sell a strong close", text="Held until the fund's own IBS closes over 0.8",
                 params=["IBS > 0.8"]),
            Step(kind="gate", label="Slots", title="Four slots, whole shares",
                 text="A lot is equity at cost ÷ 4; a buy that can't afford a share is skipped",
                 params=["4 slots"]),
            Step(kind="gate", label="Session", title="One run a day, 15:50–16:00",
                 text="Outside the window nothing is placed; an early-close day is skipped entirely",
                 params=["15:56", "no early closes"]),
        ],
        sizing="Each lot is the book's equity at cost ÷ 4, whole shares.",
        expected=Expected(win_rate=62, avg_trade_pct=0.35, avg_win_pct=1.3, avg_loss_pct=-1.2, trades_per_month=6.0,
                          sd_trade_pct=1.6, source="backtest", window="2000–2020", stage="develop",
                          **LIVE_BASIS["ibs"] | {"cagr_pct": None}),
        review_at_trades=None,
        rules_version="paper v1", rules_effective=ibs_days[0],
        rules_history=[RuleVersion(version="paper v1", effective=ibs_days[0],
                                   summary="The confirmed candidate, run on paper in the sandbox")],
        review=Review(label="Decision review", counted_since=ibs_days[0], by=days[-1] + timedelta(days=18),
                      doc="IBS paper evaluation plan",
                      last_note="Ready to write the real-money spec when rows 1–5 pass; the edge evidence stays "
                      "the backtest",
                      criteria=[
                          Criterion(key="ops", label="Runs every session", measure="Sessions with a summary row",
                                    target="≤ 1 miss in 20", value="12 of 12", status="pass"),
                          Criterion(key="gate", label="Paper gate", measure="Lifetime sessions and round trips",
                                    target="≥ 20 sessions, ≥ 10 round trips", value="12 sessions, 7 round trips",
                                    status="pending"),
                          Criterion(key="fidelity", label="Live signal matches research",
                                    measure="15:55 reading vs the official close, classified",
                                    target="≥ 80% agreement", value="86% of 21", status="pass"),
                          Criterion(key="runner", label="Runner agrees with the snapshot",
                                    measure="Median gap between the two IBS readings", target="≤ 0.05",
                                    value="0.03", status="pass"),
                          Criterion(key="cost", label="Real orders would be cheap",
                                    measure="Median half-spread at 15:55", target="≤ 3 bp", value="4.1 bp",
                                    status="fail"),
                          Criterion(key="drift", label="Decision-to-close drift", measure="|15:55 last − close|",
                                    target="Reported", value="6 bp median", status="info"),
                          Criterion(key="shadow", label="Cost-honest shadow book",
                                    measure="Buy the ask, sell the bid", target="Reported", value="7 trades, +12 bp",
                                    status="info"),
                      ]),
    ),
    Strategy(
        id="leader", name="Opening leader", summary="Buys the strongest name of the first fifteen minutes and is flat "
        "before lunch.",
        expected=Expected(win_rate=52, avg_trade_pct=0.10, avg_win_pct=1.0, avg_loss_pct=-0.9, trades_per_month=15.0,
                          sd_trade_pct=1.2, source="backtest", window="2021–2024"),
        review_at_trades=30,
    ),
    Strategy(
        id="verticals", name="Options verticals", summary="Expresses swing signals as debit spreads.",
        expected=Expected(win_rate=55, avg_trade_pct=4.0, avg_win_pct=38.0, avg_loss_pct=-40.0, trades_per_month=4.0,
                          sd_trade_pct=35.0, source="backtest", window="2015–2020"),
        review_at_trades=30,
    ),
    ]


def _judged(trades: list[Trade], rules: list[RuleVersion], system_from: date | None, seed: str) -> list[Trade]:
    """Each trade with who placed it, the rules in force when it was entered and the desk's scoring. Before
    `system_from` entries and exits were by hand (the rules of the time); from it on the system placed them, but
    for one hand exit (a deviation) and the newest trade, not scored yet. With no `system_from` the origin isn't
    reported. Every ninth hand trade broke its plan."""
    rng = random.Random(seed)
    out = []
    ordered = sorted(trades, key=lambda t: (t.closed, t.opened, t.symbol))
    newest = ordered[-1] if ordered else None
    deviation = next((t for t in ordered if system_from and t.opened >= system_from and t is not newest), None)
    for k, t in enumerate(ordered):
        version = next((r.version for r in reversed(rules) if r.effective <= t.opened), "")
        if system_from is None:
            out.append(t)
            continue
        by_hand = t.opened < system_from
        broke = by_hand and k % 9 == 8
        fields = {"entry_by": "hand" if by_hand else "system", "exit_by": "hand" if by_hand else "system",
                  "rules_version": version, "plan_followed": not broke,
                  "note": "Held through a print" if broke else ""}
        if t is deviation:
            fields.update(exit_by="hand", plan_followed=False, note="Sold by hand ahead of a print")
        elif t is newest:
            fields.update(plan_followed=None)
        rng.random()  # keeps the seed's draw order stable if a rule above changes
        out.append(t.model_copy(update=fields))
    return out


def _decisions(days: list[date], tz: ZoneInfo, positions: list[Position]) -> list[Decision]:
    """The last session's decision cycle for the real RSI2 book and the IBS book, as their runners would record it:
    signals read the evening before, the gate's answers, what was placed at the open, what filled and what expired."""
    last, prior = days[-1], days[-2]
    at = lambda day, hh, mm: datetime.combine(day, time(hh, mm), tzinfo=tz)  # noqa: E731
    rsi2 = [
        Decision(book_id="rsi2-real", time=at(prior, 17, 30), kind="signal", symbol="MSFT", side="buy", value=6.5,
                 label="RSI(2)", detail="Closed under 10"),
        Decision(book_id="rsi2-real", time=at(prior, 17, 30), kind="signal", symbol="ORCL", side="buy", value=8.9,
                 label="RSI(2)", detail="Closed under 10"),
        Decision(book_id="rsi2-real", time=at(prior, 17, 30), kind="queued", symbol="MSFT", side="buy", value=6.5,
                 label="RSI(2)", detail="Buy 6 limit 513.28, good for the next session"),
        Decision(book_id="rsi2-real", time=at(prior, 17, 30), kind="queued", symbol="ORCL", side="buy", value=8.9,
                 label="RSI(2)", detail="Buy 12 limit 246.10, good for the next session"),
        Decision(book_id="rsi2-real", time=at(prior, 17, 45), kind="blocked", symbol="ORCL", side="buy",
                 detail="Caps: 5 lots would be open with MSFT; held for the morning run"),
        Decision(book_id="rsi2-real", time=at(last, 9, 31), kind="placed", symbol="MSFT", side="buy",
                 detail="Limit 513.28 at the open"),
        Decision(book_id="rsi2-real", time=at(last, 9, 31), kind="filled", symbol="MSFT", side="buy",
                 detail="6 at 508.20; stop 467.54 placed"),
        Decision(book_id="rsi2-real", time=at(last, 9, 31), kind="blocked", symbol="ORCL", side="buy",
                 detail="Caps: 5 lots already open"),
        Decision(book_id="rsi2-real", time=at(last, 16, 0), kind="expired", symbol="ORCL", side="buy",
                 detail="Unfilled by the close; re-checked this evening"),
    ]
    for p in positions:
        if p.book_id == "rsi2-real":
            reading = {"CAT": 36.3, "JPM": 54.8, "MSFT": 12.1}.get(p.symbol, 61.0)
            rsi2.append(Decision(book_id="rsi2-real", time=at(last, 9, 31), kind="blocked", symbol=p.symbol,
                                 side="sell", value=reading, label="RSI(2)",
                                 detail=f"Exit waits: RSI(2) {reading} ≤ 70"))
    ibs = [
        Decision(book_id="ibs-paper", time=at(last, 15, 56), kind="signal", symbol="XLF", side="buy",
                 value=0.12, label="IBS", detail="Closed in the bottom fifth of its range"),
        Decision(book_id="ibs-paper", time=at(last, 15, 56), kind="signal", symbol="XLE", side="sell", value=0.84,
                 label="IBS", detail="Held lot closed strong"),
        Decision(book_id="ibs-paper", time=at(last, 15, 56), kind="signal", symbol="XLU", side="buy", value=0.18,
                 label="IBS", detail="Closed in the bottom fifth of its range"),
        Decision(book_id="ibs-paper", time=at(last, 15, 56), kind="queued", symbol="XLE", side="sell",
                 detail="Sell 11 limit 88.16"),
        Decision(book_id="ibs-paper", time=at(last, 15, 56), kind="placed", symbol="XLE", side="sell",
                 detail="Limit 88.16, day"),
        Decision(book_id="ibs-paper", time=at(last, 15, 57), kind="filled", symbol="XLE", side="sell",
                 detail="11 at 88.19"),
        Decision(book_id="ibs-paper", time=at(last, 15, 57), kind="queued", symbol="XLF", side="buy", value=0.12,
                 label="IBS", detail="Buy 17 limit 51.25, deepest first"),
        Decision(book_id="ibs-paper", time=at(last, 15, 57), kind="blocked", symbol="XLU", side="buy", value=0.18,
                 label="IBS", detail="Slots full"),
        Decision(book_id="ibs-paper", time=at(last, 15, 57), kind="placed", symbol="XLF", side="buy",
                 detail="Limit 51.25, day"),
        Decision(book_id="ibs-paper", time=at(last, 15, 58), kind="filled", symbol="XLF", side="buy",
                 detail="17 at 51.20"),
    ]
    return [*rsi2, *ibs]


class DemoConnector:
    """Serves the same fictional year to anyone who runs kestrel without a profile."""

    def __init__(self, source_id: str, tz: ZoneInfo, seed: int = 340) -> None:
        self.source_id = source_id
        self.tz = tz
        self.seed = seed

    def snapshot(self, now: datetime) -> Snapshot:
        local = now.astimezone(self.tz)
        days = weekdays_ending(local.date(), DAYS)
        rng = random.Random(self.seed)
        market = [0.0] + [rng.gauss(MARKET_DRIFT, MARKET_VOL) for _ in range(DAYS - 1)]
        zero = [0.0] * DAYS

        roth_flows, brokerage_flows, savings_flows = _monthly(days, 500), _monthly(days, 550), _monthly(days, 150)
        trading_flows = zero.copy()
        trading_flows[DAYS // 3] = 1500.0
        roth = _walk(rng, 50200.0, market, 0.95, 0.0001, 0.0015, roth_flows)
        brokerage = _walk(rng, 37400.0, market, 1.0, 0.0001, 0.0018, brokerage_flows)
        trading = _walk(rng, 14200.0, market, 0.45, 0.0006, 0.0045, trading_flows)
        savings = [21500.0]
        for i in range(1, DAYS):
            savings.append(round(savings[-1] * (1 + 0.041 / 260) + savings_flows[i], 2))
        # the bank has its own seeds, so the market above never moves; every deposit above comes out of checking
        card, card_flows, card_payments = _card(days, self.seed)
        transfers = [sum(f) for f in zip(roth_flows, brokerage_flows, savings_flows, trading_flows)]
        checking, checking_flows = _checking(days, transfers, card_payments)
        spx = _walk(rng, 560.0, market, 1.0, 0.0, 0.0015, zero)
        paper = _walk(rng, 100000.0, market, 0.5, 0.0005, 0.004, zero)
        options = _walk(rng, 100000.0, market, 0.8, -0.0002, 0.012, zero)
        paused_at = DAYS - 20
        options = options[:paused_at] + [options[paused_at - 1]] * (DAYS - paused_at)
        ibs_days, leader_days = days[-12:], days[-10:]
        ibs = _walk(rng, 3200.0, market[-12:], 0.4, 0.0012, 0.004, zero[:12])
        leader = _walk(rng, 25000.0, market[-10:], 0.2, -0.0015, 0.003, zero[:10])

        positions = [
            # a protective stop rests at the broker, but the desk feed that reports this book doesn't carry its
            # level: stop_resting says so, so kestrel doesn't raise a false "no resting stop" alarm on it
            Position(book_id="rsi2-real", symbol="MSFT", quantity=6, entry_price=508.20, last_price=512.40,
                     stop_resting=True, opened=days[-1]),
            Position(book_id="rsi2-real", symbol="CAT", quantity=6, entry_price=468.30, last_price=474.95,
                     stop_price=430.84, opened=days[-3]),
            Position(book_id="rsi2-real", symbol="PG", quantity=20, entry_price=152.40, last_price=155.08,
                     stop_price=140.21, opened=days[-4]),
            Position(book_id="rsi2-real", symbol="JPM", quantity=10, entry_price=301.10, last_price=297.85,
                     stop_price=277.01, opened=days[-2]),
            Position(book_id="rsi2-paper", symbol="HD", quantity=45, entry_price=398.10, last_price=404.66,
                     stop_price=366.25, opened=days[-3]),
            Position(book_id="rsi2-paper", symbol="TXN", quantity=95, entry_price=190.20, last_price=188.70,
                     stop_price=174.98, opened=days[-2]),
            Position(book_id="rsi2-paper", symbol="KO", quantity=260, entry_price=69.05, last_price=69.90,
                     stop_price=63.53, opened=days[-5]),
            Position(book_id="rsi2-paper", symbol="ABT", quantity=140, entry_price=128.40, last_price=130.02,
                     stop_price=118.13, opened=days[-4]),
            Position(book_id="rsi2-paper", symbol="UNP", quantity=75, entry_price=238.55, last_price=241.10,
                     stop_price=219.47, opened=days[-1]),
            Position(book_id="ibs-paper", symbol="XLF", quantity=17, entry_price=51.20, last_price=51.62,
                     opened=days[-1], note="Exits on strength"),
        ]
        holdings = _holdings("roth", roth[-1]) + _holdings("brokerage", brokerage[-1]) + [
            # the trading account holds what the real book has open
            Holding(account_id="trading", symbol=p.symbol, name=NAMES[p.symbol], quantity=p.quantity,
                    price=p.last_price, value=round(p.quantity * p.last_price, 2),
                    cost_basis=round(p.quantity * p.entry_price, 2))
            for p in positions if p.book_id == "rsi2-real"
        ]
        as_of = datetime.combine(days[-1], time(16, 0), tzinfo=self.tz)
        accounts = [
            Account(id="roth", name="Roth IRA", institution="Brokerage A", account_type="Roth IRA",
                    category="long_term", value=roth[-1], cash=_cash(holdings, "roth", roth[-1]), as_of=as_of),
            Account(id="brokerage", name="Brokerage", institution="Brokerage A", account_type="Brokerage",
                    category="long_term", value=brokerage[-1], cash=_cash(holdings, "brokerage", brokerage[-1]),
                    as_of=as_of),
            Account(id="trading", name="Trading account", institution="Brokerage B", account_type="Individual",
                    category="trading", value=trading[-1], cash=_cash(holdings, "trading", trading[-1]), as_of=as_of),
            Account(id="savings", name="High-yield savings", institution="Bank C", account_type="Savings",
                    category="cash", value=savings[-1], cash=savings[-1], as_of=as_of, rate_pct=4.1),
            Account(id="checking", name="Checking", institution="Bank C", account_type="Checking", category="cash",
                    value=checking[-1], cash=checking[-1], as_of=as_of),
            Account(id="card", name="Credit card", institution="Bank D", account_type="Credit card", category="debt",
                    value=card[-1], as_of=as_of, rate_pct=24.9, limit=5000.0),
        ]
        account_history = [
            Series(id="roth", points=_points(days, roth, roth_flows)),
            Series(id="brokerage", points=_points(days, brokerage, brokerage_flows)),
            Series(id="trading", points=_points(days, trading, trading_flows)),
            Series(id="savings", points=_points(days, savings, savings_flows)),
            Series(id="checking", points=_points(days, checking, checking_flows)),
            Series(id="card", points=_points(days, card, card_flows)),
        ]
        transactions = _transactions(days, self.seed, card_flows=card_flows, card_payments=card_payments,
                                     savings_flows=savings_flows,
                                     deposits=[("Roth IRA", roth_flows), ("Brokerage", brokerage_flows),
                                               ("High-yield savings", savings_flows),
                                               ("Trading account", trading_flows)])
        cash_runway = Target(id="cash-runway", label="Cash runway", unit="x", target=6, low=4,
                             actual=round((savings[-1] + checking[-1]) / MONTHLY_SPEND, 1),
                             note="Months of spending the cash accounts cover")

        at = lambda hh, mm: _next_weekday_at(local, time(hh, mm))  # noqa: E731
        marked = days[-1]  # every book marks its positions at the last session's close
        books = [
            Book(id="rsi2-real", name="Mean reversion", money="real", strategy_id="rsi2", account_id="trading",
                 status="running", started=days[0] - timedelta(days=5), value=trading[-1], slots_total=5,
                 next_run=at(9, 31), capital=trading[-1], prices_as_of=marked,
                 capital_basis="The trading account's value; deposits are taken out of the return"),
            Book(id="rsi2-paper", name="Mean reversion", money="paper", strategy_id="rsi2", status="running",
                 started=days[0] - timedelta(days=60), value=paper[-1], slots_total=6, next_run=at(17, 30),
                 capital=100000.0, capital_basis="The simulator's $100,000 starting cash", prices_as_of=marked),
            Book(id="ibs-paper", name="ETF close strength", money="paper", strategy_id="ibs", status="running",
                 started=ibs_days[0], value=ibs[-1], slots_total=4, next_run=at(15, 56), capital=3200.0,
                 capital_basis="The $3,200 virtual book, at cost", prices_as_of=marked),
            Book(id="leader-paper", name="Opening leader", money="paper", strategy_id="leader", status="running",
                 started=leader_days[0], value=leader[-1], slots_total=1, next_run=at(9, 25)),
            Book(id="verticals-paper", name="Options verticals", money="paper", strategy_id="verticals",
                 status="paused", started=days[0] - timedelta(days=70), value=options[-1], slots_total=3),
        ]
        book_history = [
            Series(id="rsi2-real", points=_points(days, trading, trading_flows)),
            Series(id="rsi2-paper", points=_points(days, paper, zero)),
            Series(id="ibs-paper", points=_points(ibs_days, ibs, zero[:12])),
            Series(id="leader-paper", points=_points(leader_days, leader, zero[:10])),
            Series(id="verticals-paper", points=_points(days, options, zero)),
        ]
        rules, system_from = _rsi2_rules(days)
        paper_rules = [RuleVersion(version="paper", effective=days[0] - timedelta(days=60),
                                   summary="The same rules in the simulator, placed by the runner")]
        ibs_rules = [RuleVersion(version="paper v1", effective=ibs_days[0], summary="Run on paper in the sandbox")]
        trades = (
            _judged(_trades(rng, "rsi2-real", days, 34, win_p=0.72, win_mu=2.4, loss_mu=-1.4, stop_every=17,
                            stop_pct=8.0), rules, system_from, f"{self.seed}:judged:rsi2-real")
            + _judged(_trades(rng, "rsi2-paper", days, 71, win_p=0.72, win_mu=2.4, loss_mu=-1.4, stop_every=17,
                              stop_pct=8.0, lot=18000.0), paper_rules, paper_rules[0].effective,
                      f"{self.seed}:judged:rsi2-paper")
            + _judged(_trades(rng, "ibs-paper", ibs_days, 7, win_p=0.6, win_mu=1.2, loss_mu=-0.9, lot=800.0,
                              pool=FUNDS), ibs_rules, ibs_rules[0].effective, f"{self.seed}:judged:ibs-paper")
            + _trades(rng, "leader-paper", leader_days, 11, win_p=0.3, win_mu=1.0, loss_mu=-1.6, hold=(0, 0),
                      lot=24000.0)
            + _trades(rng, "verticals-paper", days[:paused_at], 13, win_p=0.35, win_mu=30.0, loss_mu=-35.0, lot=600.0)
        )
        sid = self.source_id
        sources = [
            Source(id=f"{sid}-portfolio", label="Portfolio", kind="data collector",
                   last_success=now - timedelta(minutes=2)),
            Source(id=f"{sid}-desk", label="Trading desk", kind="feed", last_success=now - timedelta(minutes=1)),
            Source(id=f"{sid}-paper", label="Paper broker", kind="rails", last_success=now - timedelta(minutes=6)),
            Source(id=f"{sid}-savings", label="Savings", kind="bank link", last_success=now - timedelta(hours=26),
                   status="stale"),
        ]
        return Snapshot(
            generated_at=now, sources=sources, accounts=accounts, holdings=holdings, account_history=account_history,
            transactions=transactions,
            books=books, book_history=book_history, positions=positions, trades=trades,
            trade_charts=[chart for book in books for chart in _charts(book, trades, days, self.seed)],
            strategies=_strategies(days, ibs_days), decisions=_decisions(days, self.tz, positions),
            runs=self._runs(local), benchmark=Benchmark(symbol="SPY", label="S&P 500", points=_points(days, spx, zero)),
            targets=[*TARGETS, cash_runway], theses=_theses(holdings, positions, local.date()),
            events=_events(local.date()), goals=_goals(local.date()), exposures=_exposures(holdings),
            backtests=_backtests(now, self.seed),
        )

    def _runs(self, local: datetime) -> list[Run]:
        """Today's runs (done up to now, due after) and the past week's, every weekday: all done but one failed run
        and one late one, so the Activity page's week grid has something to say. A weekend day has no runs."""
        plan = [
            (time(9, 25), "Opening leader · paper", "leader-paper", "Screens at 09:45", "Screened at 09:45 · no entry"),
            (time(9, 31), "Morning run", "rsi2-real", "Places queued entries and exits",
             "1 exit sold · MSFT entry filled"),
            (time(15, 56), "ETF close entries · paper", "ibs-paper", "Buys funds that close weak",
             "Bought XLF at the close"),
            (time(17, 30), "Nightly suite", None, "Signals, paper fills, the nightly note", "Nightly note written"),
            (time(17, 45), "Evening run", "rsi2-real", "Queues the next session's entries and exits",
             "Queued 1 entry"),
            (time(19, 0), "Watchdog", None, "Checks every run reported in", "All runs reported in"),
        ]
        today = local.date()
        weekdays_back = [d for d in (today - timedelta(days=n) for n in range(1, 8)) if d.weekday() < 5]
        failed_day = next((d for d in weekdays_back if (today - d).days >= 4), None)
        late_day = next((d for d in weekdays_back if (today - d).days >= 2 and d != failed_day), None)
        runs = []
        for day in [*reversed(weekdays_back), *([today] if today.weekday() < 5 else [])]:
            for at, label, book_id, due_detail, done_detail in plan:
                when = datetime.combine(day, at, tzinfo=local.tzinfo)
                if day == today:
                    done = when <= local
                    status, detail = ("done", done_detail) if done else ("due", due_detail)
                elif day == failed_day and label == "Evening run":
                    status, detail = "failed", "The broker timed out; the retry at 18:15 ran"
                elif day == late_day and label == "Watchdog":
                    status, detail = "late", "Reported in 40 minutes late"
                else:
                    status, detail = "done", done_detail
                runs.append(Run(time=when, label=label, book_id=book_id, status=status, detail=detail))
        return runs
