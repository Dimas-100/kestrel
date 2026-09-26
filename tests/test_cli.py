import json

import pytest

import kestrel.cli
from kestrel.cli import main

NOW = "2026-09-25T21:08:00+00:00"


def run(capsysbinary, *argv):
    code = main(list(argv))
    out, err = capsysbinary.readouterr()
    return code, out.decode("utf-8"), err.decode("utf-8")


def test_demo_prints_a_valid_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--now", NOW)
    data = json.loads(out)
    assert code == 0 and data["contract_version"] == "1" and len(data["accounts"]) == 4


def test_demo_home_is_reproducible(capsysbinary):
    first = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    second = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    assert first == second and json.loads(first)["summary"]["needs_you"] == 2


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
    profile.write_text('[[sources]]\nid = "desk"\nkind = "feed"\n', encoding="utf-8")
    code, out, _ = run(capsysbinary, "check", "--profile", str(profile))
    assert code == 1 and "error" in out
