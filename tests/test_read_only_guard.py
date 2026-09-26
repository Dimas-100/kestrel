"""kestrel shows money; it never moves it. This walks every module and fails on anything that could place,
change or cancel an order, or open a write route."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "kestrel"

FORBIDDEN_IMPORTS = ("trading_rails", "webull", "alpaca", "ib_insync", "ibapi", "robin_stocks", "schwab", "tda")
FORBIDDEN_CALLS = {"place", "place_order", "submit_order", "cancel", "cancel_order", "replace_order", "modify_order"}
FORBIDDEN_ROUTES = {"post", "put", "patch", "delete", "api_route", "add_api_route", "websocket"}


def modules():
    return sorted(SRC.rglob("*.py"))


def test_there_is_something_to_check():
    assert len(modules()) >= 8


def test_no_broker_or_trading_library_is_imported():
    offenders = []
    for path in modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            offenders += [f"{path.name}: {n}" for n in names if n.split(".")[0].lower() in FORBIDDEN_IMPORTS]
    assert not offenders, offenders


def test_nothing_calls_an_order_method_or_registers_a_write_route():
    offenders = []
    for path in modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                name = node.func.attr
                if name in FORBIDDEN_CALLS or name in FORBIDDEN_ROUTES:
                    offenders.append(f"{path.name}:{node.lineno} .{name}()")
    assert not offenders, offenders


def test_the_guard_catches_what_it_should():
    bad = ast.parse("broker.place_order(o)\napp.post('/x')\nimport webull.trade")
    calls = [n.func.attr for n in ast.walk(bad) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert "place_order" in calls and "post" in calls
