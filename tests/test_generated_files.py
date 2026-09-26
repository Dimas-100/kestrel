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
]


@pytest.mark.parametrize("path,argv", GENERATED, ids=[p.name for p, _ in GENERATED])
def test_generated_file_is_current(path, argv, capsysbinary):
    main(argv)
    current = json.loads(capsysbinary.readouterr().out.decode("utf-8"))
    command = "kestrel " + " ".join(argv) + f" > {path.relative_to(ROOT).as_posix()}"
    assert path.is_file(), f"missing: run `{command}`"
    assert json.loads(path.read_text(encoding="utf-8")) == current, f"out of date: run `{command}`"
