"""Files generated from the code must match the code. Regenerate with the command in each failure message."""

import json
from pathlib import Path

import pytest

from kestrel.cli import main

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-09-25T21:08:00+00:00"

GENERATED = [
    (ROOT / "docs" / "contract" / "snapshot.schema.json", ["schema"]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "home.json", ["demo", "--view", "home", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "shell.json", ["demo", "--view", "shell", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "strategies.json", ["demo", "--view", "strategies", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "strategy-rsi2.json",
     ["demo", "--view", "strategy", "--id", "rsi2", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "accounts.json", ["demo", "--view", "accounts", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "account-roth.json",
     ["demo", "--view", "account", "--id", "roth", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "books.json", ["demo", "--view", "books", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "book-rsi2-real.json",
     ["demo", "--view", "book", "--id", "rsi2-real", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "activity.json", ["demo", "--view", "activity", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "calendar.json", ["demo", "--view", "calendar", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "backtests.json", ["demo", "--view", "backtests", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "settings.json", ["demo", "--view", "settings", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "plan.json", ["demo", "--view", "plan", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "reserves.json", ["demo", "--view", "reserves", "--now", NOW]),
]


@pytest.mark.parametrize("path,argv", GENERATED, ids=[p.name for p, _ in GENERATED])
def test_generated_file_is_current(path, argv, capsysbinary):
    main(argv)
    emitted = capsysbinary.readouterr().out.decode("utf-8")
    command = "kestrel " + " ".join(argv) + f" > {path.relative_to(ROOT).as_posix()}"
    assert path.is_file(), f"missing: run `{command}`"
    written = path.read_text(encoding="utf-8")  # newlines read as "\n" whatever the checkout wrote
    assert json.loads(written) == json.loads(emitted), f"out of date: run `{command}`"
    # the text too: JSON equality can't see formatting, and it reads -0.0 as 0.0
    assert written == emitted, f"not the text the CLI writes: run `{command}`"
