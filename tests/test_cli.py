import json
import re

import pytest
from fdc_fixture import Warehouse

import kestrel.cli
import kestrel.server
from kestrel.cli import main
from kestrel.profile import DEMO_PROFILE

NOW = "2026-09-25T21:08:00+00:00"


def run(capsysbinary, *argv):
    code = main(list(argv))
    out, err = capsysbinary.readouterr()
    return code, out.decode("utf-8"), err.decode("utf-8")


def test_demo_prints_a_valid_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--now", NOW)
    data = json.loads(out)
    assert code == 0 and data["contract_version"] == "1" and len(data["accounts"]) == 6


def test_demo_home_is_reproducible(capsysbinary):
    first = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    second = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    assert first == second and json.loads(first)["summary"]["needs_you"] == 4


def test_schema_describes_the_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "schema")
    schema = json.loads(out)
    assert code == 0 and schema["title"] == "Snapshot" and "accounts" in schema["properties"]


def test_check_passes_on_the_demo_and_fails_on_a_bad_profile(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsysbinary, "check")
    assert code == 0 and "hello, Alex" in out and "stale" in out
    bad = tmp_path / "bad.toml"
    bad.write_text('[app]\ntheme = "neon"\n', encoding="utf-8")
    code, _, err = run(capsysbinary, "check", "--profile", str(bad))
    assert code == 2 and "app.theme" in err


def test_serve_only_ever_listens_on_this_computer(capsys):
    assert kestrel.cli.HOST == "127.0.0.1"
    with pytest.raises(SystemExit) as done:
        main(["serve", "--help"])
    out = capsys.readouterr().out
    assert done.value.code == 0 and "--port" in out and "--host" not in out


def test_check_fails_when_a_source_cannot_be_read(capsysbinary, tmp_path):
    profile = tmp_path / "p.toml"
    profile.write_text('[[sources]]\nid = "paper"\nkind = "rails"\n', encoding="utf-8")
    code, out, _ = run(capsysbinary, "check", "--profile", str(profile))
    assert code == 1 and "error" in out


def test_demo_prints_the_strategy_views(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--view", "strategies", "--now", NOW)
    assert code == 0 and [c["id"] for c in json.loads(out)["strategies"]] == ["rsi2", "ibs", "leader", "verticals"]
    code, out, _ = run(capsysbinary, "demo", "--view", "strategy", "--id", "rsi2", "--now", NOW)
    assert code == 0 and json.loads(out)["book"] == "real"
    code, out, _ = run(capsysbinary, "demo", "--view", "strategy", "--id", "rsi2", "--book", "paper", "--now", NOW)
    assert code == 0 and json.loads(out)["primary"] == "rsi2-paper"


def test_demo_strategy_needs_a_known_id(capsysbinary):
    code, _, err = run(capsysbinary, "demo", "--view", "strategy", "--now", NOW)
    assert code == 2 and "--view strategy needs --id" in err
    code, _, err = run(capsysbinary, "demo", "--view", "strategy", "--id", "nope", "--now", NOW)
    assert code == 2 and "no strategy 'nope' in the demo data" in err


def test_check_lists_each_sources_accounts_but_never_a_balance(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsysbinary, "check")
    assert code == 0
    assert [line for line in out.splitlines() if line.startswith(" " * 9)] == [
        "         roth             long_term        Roth IRA",
        "         brokerage        long_term        Brokerage",
        "         trading          trading          Trading account",
        "         savings          cash             High-yield savings",
        "         checking         cash             Checking",
        "         card             debt             Credit card",
    ]
    assert "$" not in out and not re.search(r"\d{4}", out)  # no balances, no amounts


def test_the_demo_flag_shows_the_demo_whatever_profile_toml_says(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profile.toml").write_text('[you]\nname = "Sam"\n[[sources]]\nid = "paper"\nkind = "rails"\n',
                                           encoding="utf-8")
    code, out, _ = run(capsysbinary, "check")
    assert code == 1 and "hello, Sam" in out
    code, out, _ = run(capsysbinary, "check", "--demo")
    assert code == 0 and out.startswith("profile: built-in demo profile - hello, Alex")
    served = []
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: None)
    monkeypatch.setattr(kestrel.server, "create_app", lambda profile, **kwargs: served.append(profile))
    code, out, _ = run(capsysbinary, "serve", "--demo", "--no-open")
    assert code == 0 and served == [DEMO_PROFILE] and "profile: built-in demo profile" in out
    with pytest.raises(SystemExit) as refused:
        main(["check", "--demo", "--profile", "profile.toml"])
    assert refused.value.code == 2


def test_demo_prints_the_account_views(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--view", "accounts", "--now", NOW)
    assert code == 0 and json.loads(out)["count"] == 6
    code, out, _ = run(capsysbinary, "demo", "--view", "account", "--id", "savings", "--now", NOW)
    savings = json.loads(out)
    assert code == 0 and savings["holdings"] == [] and savings["cash"] == savings["value"]
    code, _, err = run(capsysbinary, "demo", "--view", "account", "--now", NOW)
    assert code == 2 and "--view account needs --id, e.g. --id roth" in err
    code, _, err = run(capsysbinary, "demo", "--view", "account", "--id", "nope", "--now", NOW)
    assert code == 2 and "no account 'nope' in the demo data" in err


def test_check_prints_a_warehouses_accounts_whatever_their_labels(capsysbinary, tmp_path):
    w = Warehouse(tmp_path / "warehouse.db")
    w.account("Épargne · Alex", "unknown", "savings")
    w.account("★ ★ ★", "webull", "brokerage")
    w.close()
    profile = tmp_path / "profile.toml"
    profile.write_text('[[sources]]\nid = "portfolio"\nkind = "fdc"\nlabel = "Portfolio"\npath = "warehouse.db"\n'
                       '[sources.categories]\n"account" = "trading"\n', encoding="utf-8")
    code, out, _ = run(capsysbinary, "check", "--profile", str(profile))
    assert code == 0 and "Portfolio        fdc              never  2 accounts · 0 holdings · no prices yet" in out
    assert [line for line in out.splitlines() if line.startswith(" " * 9)] == [
        "         epargne-alex     cash             Épargne · Alex",
        "         account          trading          ★ ★ ★",
    ]
