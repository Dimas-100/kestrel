# Phase 4b — the `feed` connector — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** kestrel reads any system of your own through one generic connector, `feed`: one JSON document in the contract's own format (a Snapshot), from a URL or a file, checked and handed on, so a trading desk's books, strategies, trades and runs show without kestrel knowing anything else about it. A feed that is down, slow, huge or malformed becomes a red source row and the rest of kestrel keeps working. And when two sources use the same account, book or strategy id, the one earlier in the profile wins, with a note on the later source's line.

**Architecture:**
- **Profile:** `SourceCfg` checks a feed source's shape when the profile loads (exactly one of `url` and `path`, the scheme, no secret in the URL, `token_env` as a variable's name, `timeout` 1–60), in messages that never repeat a value back.
- **Connector:** `connectors/feed.py` reads the file, or sends one GET through an opener with no proxy, no redirect handler and no cookie jar; caps the body at 20 MB and the whole answer at the timeout; parses and validates the Snapshot; and replaces the payload's own sources with one row for the feed, whose last success is the payload's `generated_at`. The token is read from the environment each time and goes only in the request's `Authorization` header. The tests talk to a feed server on 127.0.0.1 in a thread: no network.
- **collect():** a pure pass over the connectors' parts, in profile order, drops a later part's duplicate accounts, books and strategies with everything that hangs off them, and notes the ids on that part's first source row.
- **Docs:** the `feed` section and the duplicate-id rule in `docs/connectors.md`, the commented block in `profile.example.toml`, a README line; the status lines move to Phase 4b.

**Tech Stack:** unchanged from Phase 4a: Python ≥ 3.11 (FastAPI 0.141, pydantic 2.13, the standard library's `urllib.request`, `http.client` and `json`; `http.server` in the tests), pytest, ruff. The web app, the contract and the generated files don't change. No new dependencies.

**Spec:** `docs/specs/2026-09-26-phase-4b-feed-design.md` (binding), with `docs/specs/2026-09-25-kestrel-design.md` (§7 contract, §8 connectors, §10 safety) and `AGENTS.md`.

**Provenance:** every code block below was run in a scratch clone of this repo, task by task, before this plan was written, and the plan itself was then replayed into a second fresh clone, task by task, taking every block out with the helper below; the counts in each task come from that replay.
- End state: `pytest` 265 passed, `ruff check .` clean; `tests/test_generated_files.py` current without regenerating anything (the demo and the contract don't move). No web command is needed in this phase.
- The HTTP tests (a hung feed, a trickle, 20 MB in one line, redirects, a proxy in the environment) were run six times in a row on Windows without a failure; `tests/test_feed_connector.py` takes about 3 s.

### How to use this plan (read before Task 1)

- **Copy file blocks with a script, never by hand.** Earlier plans lost typographic apostrophes, minus signs and non-breaking characters to retyping. Save this helper **outside the repo** (for example in your temp folder) and use it for every file block:

````python
"""Write a plan task's file blocks to disk, byte for byte.

Usage (from the repo root):
  python copy_blocks.py PLAN TASK              list the task's file blocks
  python copy_blocks.py PLAN TASK PATH [...]   write those blocks
  python copy_blocks.py PLAN TASK --all        write every block of the task
  python copy_blocks.py PLAN TASK --check      compare the task's blocks (and every earlier task's) with the tree
"""

import re
import sys
from pathlib import Path

BLOCK = re.compile(r"^`([^`\n]+)`:\n\n````[a-z]*\n(.*?)\n````\n", re.M | re.S)


def tasks(plan: str) -> dict[int, list[tuple[str, str]]]:
    parts = re.split(r"^### Task (\d+):", plan, flags=re.M)
    return {int(num): BLOCK.findall(body) for num, body in zip(parts[1::2], parts[2::2])}


def main(argv: list[str]) -> int:
    plan_path, task, *rest = argv
    by_task = tasks(Path(plan_path).read_text(encoding="utf-8"))
    n = int(task)
    blocks = dict(by_task.get(n, []))
    if not rest:
        for path in blocks:
            print(path)
        print(f"{len(blocks)} block(s) in task {n}")
        return 0
    if rest == ["--check"]:
        expected: dict[str, str] = {}
        for num in sorted(k for k in by_task if k <= n):
            expected.update(dict(by_task[num]))
        bad = 0
        for path, block in expected.items():
            p = Path(path)
            if not p.exists():
                print("MISSING", path)
                bad += 1
            elif p.read_text(encoding="utf-8").rstrip("\n") != block.rstrip("\n"):
                print("DRIFT", path)
                bad += 1
        print(len(expected), "blocks checked,", bad, "problem(s)")
        return 1 if bad else 0
    paths = list(blocks) if rest == ["--all"] else rest
    for path in paths:
        if path not in blocks:
            print(f"no block for {path} in task {n}", file=sys.stderr)
            return 2
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as f:
            f.write(blocks[path].rstrip("\n") + "\n")
        print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
````

  Run it from the repo root, for example `python <temp>/copy_blocks.py docs/plans/2026-09-26-phase-4b-feed.md 2 tests/feed_fixture.py tests/test_feed_connector.py`. Write the test files first (Step 1), run them, then write the code files (Step 3). After a task's Step 4, `python <temp>/copy_blocks.py docs/plans/2026-09-26-phase-4b-feed.md N --check` must end with `0 problem(s)`.
- **Every file block is the complete file.** "Replace the whole file" means overwrite it with the block. There are no partial edits except the documentation lines in Task 5, which are given as exact old and new text.
- **Non-ASCII characters are exact:** · (middle dot, in every source detail and the tests that pin it), — (em dash), … (ellipsis) and § in the docs, é, É and ★ (in the tests' fictional strings), and one you can't see: a byte-order mark (U+FEFF) inside a string in `tests/test_profile.py`'s byte-order-mark test. The tests pin every message; if one fails on a character, the copy drifted.
- **Paste raw output.** When you report a step, paste the tool's own summary lines (for example `265 passed in 9.9s`, `All checks passed!`), not a paraphrase.
- **Commands:** Python runs as `.venv/Scripts/python -m pytest` (on macOS and Linux, `.venv/bin/python`). `pyproject.toml` already adds `-q`; don't add another, or the summary line disappears. No web command is needed: the web app doesn't change in this phase.
- **The commit trailer:** save the session's trailer line (`Co-Authored-By: Claude Opus 5.5 (1M context) <…>`, with the address) to `<temp>/trailer.txt`, next to the helper. Each commit step passes it as the message's last paragraph: `git commit -m "subject" -m "$(cat <temp>/trailer.txt)"`.
- If anything doesn't match what a step says, stop and report it rather than improvising.

## Global Constraints

- **Read-only, always:** GET routes only; the server binds `127.0.0.1`; no broker or trading import and no call named `place`, `place_order`, `submit_order`, `cancel`, `cancel_order`, `replace_order`, `modify_order`, `post`, `put`, `patch`, `delete`, `api_route`, `add_api_route` or `websocket` anywhere in `src/kestrel` (`tests/test_read_only_guard.py`). The connector only reads: one GET or one file read per snapshot, nothing cached, nothing written.
- **The token (spec §2.1, §2.3):** "GET only; no cookies; the token (when used) only in the header; never logged, never in an error message." It comes only from the environment variable `token_env` names, never from the profile, and "is sent as `Authorization: Bearer …` to the configured URL only": no redirect is followed and no proxy is used.
- **Untrusted input (parent spec §10):** everything a feed sends is data rendered as text (the web app never injects HTML); a payload that fails validation is dropped and the source shows as `error`; the contract already limits alert links to pages inside kestrel.
- **A broken source never takes the page down:** "a feed that is down, slow, huge or malformed becomes a red source row; the rest of kestrel keeps working (`collect()` already isolates sources)."
- **The contract doesn't change:** `contract_version` stays `"1"`, and `docs/contract/snapshot.schema.json` and the web fixtures stay current without regenerating anything (`tests/test_generated_files.py`). If that test fails, something moved that shouldn't have: stop.
- **Nothing personal in git:** names, account numbers, balances, holdings and machine paths arrive only at runtime, through the gitignored `profile.toml` and the user's connectors. Demo data stays fictional ("Alex"). The test payloads are made up, example hosts are `example.com` and `127.0.0.1`, and `tests/test_hygiene.py` passes on every commit (an address-shaped string in a test, like Task 1's URL with a user name in it, ends in `@example.com`).
- **No network in tests:** every HTTP test talks to a `FeedServer` on 127.0.0.1 in a thread (`tests/feed_fixture.py`), and no test waits more than half a second for a timeout.
- **Messages are for a person:** plain English, in the spec's own words where it gives them ("the feed answered 503", "the feed sent more than 20 MB", "no feed file at <path>", "set KESTREL_DESK_TOKEN in the environment (token_env)"), and none repeats a secret back.
- **Commits:** `feat(scope): …` / `fix(scope): …` / `docs: …`, each ending with the trailer line `Co-Authored-By: Claude Opus 5.5 (1M context)` followed by the Anthropic noreply address in angle brackets, exactly as the session gives it. The address is left out of this file on purpose: `tests/test_hygiene.py` fails on any email address in a tracked file other than an example.com or GitHub noreply one, and this plan is tracked. Every commit step below reads the line from `<temp>/trailer.txt` (see How to use).

## Review Focus

These are the inputs most likely to bite a real person that the spec is silent on. Each has a test in the task named after it.

- **A feed that answers with a web page.** A desk behind a sign-in answers 200 with HTML, or redirects to its sign-in page. The page is named as one ("the feed sent something that isn't JSON: a web page (a sign-in page, or the wrong address?)"), not left as a JSON parser's position, and a redirect is refused with its target named. Tests: `test_a_web_page_such_as_a_sign_in_page_is_named` (Task 2), `test_a_sign_in_page_over_http_is_named` and `test_a_redirect_to_a_path_is_named_in_full` (Task 3).
- **A secret written in the wrong place.** A URL like `http://name:secret@host/…`, or the token itself pasted into `token_env`: both are profile errors whose message doesn't repeat the value (`token_env` must look like a variable's name in capitals, which a pasted token almost never does). A token with a line break inside is refused without showing it (`http.client` would have put it in its own error), and a redirect's target is shown without its user name or query. Tests: `test_a_feed_url_cant_carry_a_user_name_or_password` and `test_token_env_is_the_name_of_a_variable_never_the_token` (Task 1), `test_a_token_a_header_cant_carry_is_refused_without_showing_it` and `test_the_token_never_shows_in_an_error_or_a_log` (Task 3).
- **A huge single line.** 20 MB and one byte of JSON with no newline and no `Content-Length` is read in 64 KB chunks and stopped one byte past the cap, never read by line; a `Content-Length` over the cap is refused before reading; exactly 20 MB loads; `[` nested 100 000 deep is "nested too deeply to read", not a crash. Tests: `test_a_file_over_20_mb_is_refused_and_20_mb_exactly_is_read` and `test_something_that_isnt_json_is_refused[nested]` (Task 2), `test_more_than_20_mb_in_one_line_is_refused_whether_or_not_the_feed_says_so_up_front` (Task 3).
- **A payload from the future.** A `generated_at` ahead of this computer's clock would never go stale and would read "−5 minutes ago". Up to five minutes of drift reads as made now; further ahead is a red row that says how far ("4 hours", the usual sign of a local time given the wrong offset). Test: `test_a_payload_from_the_future_is_refused_beyond_five_minutes_of_clock_drift` (Task 2).
- **A slow trickle.** `urllib`'s timeout is per socket read, so a feed that sends a byte every 50 ms would never time out. The connector reads with `read1` against a deadline and stops at the timeout ("the feed was still sending after 5 s"). Tests: `test_a_slow_trickle_is_cut_off_at_the_timeout` and `test_a_feed_that_doesnt_answer_in_time_is_cut_off` (Task 3).

## File map

```
src/kestrel/profile.py                   SourceCfg._feed_shape                                          (Task 1)
src/kestrel/connectors/base.py           + DETAIL_LIMIT                                                 (Task 2)
src/kestrel/connectors/feed.py           new: read a file, parse, check, keep (Task 2); one GET, the token, the
                                         20 MB cap and the deadline (Task 3)
src/kestrel/connectors/__init__.py       build() knows kind "feed", DETAIL_LIMIT (Task 3); duplicate ids (Task 4)
tests/test_profile.py · tests/test_cli.py · tests/test_demo_connector.py (replaced)                     (Task 1)
tests/feed_fixture.py · tests/test_feed_connector.py (new)                                              (Tasks 2, 3)
tests/test_connectors.py (new)                                                                          (Task 4)
docs/connectors.md · profile.example.toml · README.md · AGENTS.md · docs/data-contract.md · docs/specs/*  (Task 5)
```

---

### Task 1: A feed source's shape is checked when the profile loads

**Files:**
- Modify (replace the whole file): `src/kestrel/profile.py`
- Test (replace the whole file): `tests/test_profile.py`, `tests/test_cli.py`, `tests/test_demo_connector.py`

**Interfaces:**
- Produces:
  - `profile.py` `SourceCfg._feed_shape`, a model validator that runs only for `kind = "feed"`: exactly one of `url` and `path`; a `url` is `http://` or `https://` with a host and no user name or password; a `path` is text (the existing `_resolve_paths` makes a relative one absolute against the profile's folder); `token_env`, when given, goes with a `url` and matches `^[A-Z_][A-Z0-9_]*$`; `timeout` (default 5) is a number from 1 to 60, not a boolean. Each failure is a `ValueError` whose message never repeats the value, so `load_profile` raises `ProfileError` with, for example, `sources.0: Value error, a feed url must start with http:// or https:// and name a host`.
  - `tests/test_cli.py` and `tests/test_demo_connector.py`: their examples of a source that can't be read used a bare `kind = "feed"`, which is now a profile error; they use `kind = "rails"` (still unavailable) instead. Nothing else in those files changes.

- [ ] **Step 1: Write the failing tests**

`tests/test_profile.py`:

````python
import os
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from kestrel.profile import DEMO_PROFILE, ProfileError, load_profile, parse_duration

ROOT = Path(__file__).resolve().parents[1]


def write(tmp_path, text):
    path = tmp_path / "profile.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_committed_example_profile_loads():
    profile, origin = load_profile(ROOT / "profile.example.toml")
    assert profile.you.name == "Alex"
    assert [s.kind for s in profile.sources] == ["demo"]
    assert origin.endswith("profile.example.toml")


def test_no_profile_file_means_the_demo_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profile, origin = load_profile()
    assert profile == DEMO_PROFILE and origin == "built-in demo profile"


def test_the_demo_profile_cannot_be_changed_by_a_caller():
    with pytest.raises(ValidationError):
        DEMO_PROFILE.you.name = "Mallory"
    with pytest.raises(ValidationError):
        DEMO_PROFILE.sources[0].kind = "feed"


def test_a_profile_in_the_working_directory_is_used(tmp_path, monkeypatch):
    write(tmp_path, '[you]\nname = "Sam"\n')
    monkeypatch.chdir(tmp_path)
    profile, _ = load_profile()
    assert profile.you.name == "Sam"
    assert profile.sources[0].kind == "demo"  # sources default to demo data


def test_a_bad_setting_names_the_field(tmp_path):
    with pytest.raises(ProfileError, match=r"app\.accent"):
        load_profile(write(tmp_path, '[app]\naccent = "purple"\n'))


def test_a_typo_in_a_section_is_refused(tmp_path):
    with pytest.raises(ProfileError, match="nmae"):
        load_profile(write(tmp_path, '[you]\nnmae = "Sam"\n'))


def test_broken_toml_is_reported_with_the_path(tmp_path):
    with pytest.raises(ProfileError, match="profile.toml"):
        load_profile(write(tmp_path, "[you\nname = 1\n"))


def test_a_missing_explicit_path_is_reported(tmp_path):
    with pytest.raises(ProfileError, match="file not found"):
        load_profile(tmp_path / "nope.toml")


def test_an_unknown_time_zone_is_refused(tmp_path):
    with pytest.raises(ProfileError, match="unknown time zone"):
        load_profile(write(tmp_path, '[app]\ntimezone = "Mars/Olympus"\n'))


def test_a_currency_must_be_a_three_letter_code(tmp_path):
    with pytest.raises(ProfileError, match=r"app\.currency"):
        load_profile(write(tmp_path, '[app]\ncurrency = "EURO"\n'))
    profile, _ = load_profile(write(tmp_path, '[app]\ncurrency = "EUR"\n'))
    assert profile.app.currency == "EUR"


def test_a_profile_saved_with_a_byte_order_mark_loads(tmp_path):
    path = tmp_path / "profile.toml"
    path.write_bytes('﻿[you]\nname = "Sam"\n'.encode("utf-8"))
    assert load_profile(path)[0].you.name == "Sam"


def test_a_profile_that_is_not_utf8_is_reported_plainly(tmp_path):
    path = tmp_path / "profile.toml"
    path.write_text('[you]\nname = "Sam"\n', encoding="utf-16")
    with pytest.raises(ProfileError, match="is not UTF-8 text"):
        load_profile(path)


def test_an_unreadable_profile_is_reported_plainly(tmp_path):
    folder = tmp_path / "profile.toml"
    folder.mkdir()  # reading a folder is an OSError on every platform
    with pytest.raises(ProfileError, match="could not read"):
        load_profile(folder)


def test_duplicate_source_ids_are_refused(tmp_path):
    text = '[[sources]]\nid = "a"\nkind = "demo"\n[[sources]]\nid = "a"\nkind = "demo"\n'
    with pytest.raises(ProfileError, match="duplicate source id"):
        load_profile(write(tmp_path, text))


def test_connector_specific_keys_are_kept_for_the_connector(tmp_path):
    profile, _ = load_profile(write(tmp_path, '[[sources]]\nid = "desk"\nkind = "feed"\nurl = "http://x"\n'))
    assert getattr(profile.sources[0], "url") == "http://x"


def test_durations():
    assert parse_duration("15m") == timedelta(minutes=15)
    assert parse_duration("36h") == timedelta(hours=36)
    assert parse_duration("2d") == timedelta(days=2)
    with pytest.raises(ValueError):
        parse_duration("soon")


def test_a_relative_source_path_is_relative_to_the_profile_not_the_working_directory(tmp_path, monkeypatch):
    home, elsewhere = tmp_path / "kestrel", tmp_path / "elsewhere"
    home.mkdir()
    elsewhere.mkdir()
    absolute = (tmp_path / "other" / "warehouse.db").as_posix()
    path = write(home, '[[sources]]\nid = "portfolio"\nkind = "fdc"\npath = "../collector/data/warehouse.db"\n'
                       f'[[sources]]\nid = "second"\nkind = "fdc"\npath = "{absolute}"\n')
    monkeypatch.chdir(elsewhere)
    profile, _ = load_profile(path)
    assert Path(getattr(profile.sources[0], "path")) == (tmp_path / "collector" / "data" / "warehouse.db").resolve()
    assert Path(getattr(profile.sources[1], "path")) == Path(absolute)
    assert not hasattr(DEMO_PROFILE.sources[0], "path")


def test_a_source_path_may_start_from_the_home_folder(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))  # where ~ points on macOS and Linux
    monkeypatch.setenv("USERPROFILE", str(home))  # and on Windows
    path = write(tmp_path, '[[sources]]\nid = "portfolio"\nkind = "fdc"\npath = "~/collector/warehouse.db"\n')
    profile, _ = load_profile(path)
    assert Path(getattr(profile.sources[0], "path")) == home / "collector" / "warehouse.db"


def test_an_unknown_category_is_a_profile_error(tmp_path):
    source = '[[sources]]\nid = "portfolio"\nkind = "fdc"\npath = "w.db"\n'
    with pytest.raises(ProfileError, match=r"unknown category 'trade' for 'Brokerage' \(use long_term, trading"):
        load_profile(write(tmp_path, source + '[sources.categories]\n"Brokerage" = "trade"\n'))
    with pytest.raises(ProfileError, match="categories must be a table"):
        load_profile(write(tmp_path, source + 'categories = "trading"\n'))
    profile, _ = load_profile(write(tmp_path, source + '[sources.categories]\n"brokerage-2" = "trading"\n'))
    assert getattr(profile.sources[0], "categories") == {"brokerage-2": "trading"}


def test_a_tilde_that_cant_be_expanded_is_a_profile_problem(tmp_path, monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda p: p)  # what an unknown ~user, or no home folder, looks like
    path = write(tmp_path, '[[sources]]\nid = "portfolio"\nkind = "fdc"\npath = "~nosuchuser/warehouse.db"\n')
    with pytest.raises(ProfileError, match=r"sources\.0: can't expand ~ in '~nosuchuser/warehouse\.db'"):
        load_profile(path)


FEED = '[[sources]]\nid = "desk"\nkind = "feed"\nlabel = "Trading desk"\n'


def test_a_feed_source_takes_a_url_or_a_path_and_its_options(tmp_path):
    profile, _ = load_profile(write(tmp_path, FEED + 'url = "https://desk.example.com/api/feed"\n'
                                                     'token_env = "KESTREL_DESK_TOKEN"\ntimeout = 30\n'))
    source = profile.sources[0]
    assert (getattr(source, "url"), getattr(source, "token_env"), getattr(source, "timeout")) == (
        "https://desk.example.com/api/feed", "KESTREL_DESK_TOKEN", 30)
    profile, _ = load_profile(write(tmp_path, FEED + 'path = "../desk/feed.json"\ntimeout = 2.5\n'))
    assert Path(getattr(profile.sources[0], "path")) == (tmp_path.parent / "desk" / "feed.json").resolve()
    with pytest.raises(ProfileError, match="a feed path is a file name in quotes"):
        load_profile(write(tmp_path, FEED + "path = 5\n"))


@pytest.mark.parametrize("lines", ["", 'url = "http://127.0.0.1:8000/api/feed"\npath = "feed.json"\n'],
                         ids=["neither", "both"])
def test_a_feed_source_needs_exactly_one_of_url_and_path(tmp_path, lines):
    with pytest.raises(ProfileError, match=r"sources\.0: Value error, a feed source needs exactly one of url and path"):
        load_profile(write(tmp_path, FEED + lines))


@pytest.mark.parametrize("url", ["ftp://desk.example.com/feed", "file:///srv/feed.json", "127.0.0.1:8000/api/feed",
                                 "http://", 8000])
def test_a_feed_url_must_be_http_or_https(tmp_path, url):
    value = f'"{url}"' if isinstance(url, str) else url
    with pytest.raises(ProfileError, match="a feed url must start with http:// or https:// and name a host"):
        load_profile(write(tmp_path, FEED + f"url = {value}\n"))


def test_a_feed_url_cant_carry_a_user_name_or_password(tmp_path):
    for url in ("http://alex:hunter2@127.0.0.1:8000/api/feed", "https://hunter2@example.com/feed"):
        with pytest.raises(ProfileError) as error:
            load_profile(write(tmp_path, FEED + f'url = "{url}"\n'))
        assert "a feed url can't carry a user name or password: put the token in an environment variable" in str(
            error.value)
        assert "hunter2" not in str(error.value)  # the secret is never repeated back


@pytest.mark.parametrize("name", ["sk_live_4f9a2b7c1d", "Bearer 4F9A2B7C", "", "1TOKEN", 42])
def test_token_env_is_the_name_of_a_variable_never_the_token(tmp_path, name):
    value = f'"{name}"' if isinstance(name, str) else name
    with pytest.raises(ProfileError) as error:
        load_profile(write(tmp_path, FEED + f'url = "http://127.0.0.1:8000/api/feed"\ntoken_env = {value}\n'))
    assert "token_env is the name of an environment variable in capitals, such as KESTREL_DESK_TOKEN" in str(
        error.value)
    assert not name or str(name) not in str(error.value)


def test_a_feed_file_takes_no_token(tmp_path):
    with pytest.raises(ProfileError, match="token_env goes with a url: a feed file is read without a token"):
        load_profile(write(tmp_path, FEED + 'path = "feed.json"\ntoken_env = "KESTREL_DESK_TOKEN"\n'))


@pytest.mark.parametrize("timeout", ["0", "0.5", "61", '"5"', "true"])
def test_a_feed_timeout_is_1_to_60_seconds(tmp_path, timeout):
    with pytest.raises(ProfileError, match="timeout is in seconds, from 1 to 60"):
        load_profile(write(tmp_path, FEED + f'url = "http://127.0.0.1:8000/api/feed"\ntimeout = {timeout}\n'))
    for fine in ("1", "60"):
        profile, _ = load_profile(write(tmp_path, FEED + f'url = "http://127.0.0.1:8000/api/feed"\ntimeout = {fine}\n'))
        assert getattr(profile.sources[0], "timeout") == int(fine)
````


`tests/test_cli.py`:

````python
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
    assert code == 0 and json.loads(out)["count"] == 4
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
````


`tests/test_demo_connector.py`:

````python
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
    assert len(snap.accounts) == 4  # the demo still arrived


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
        ("roth", "Roth IRA"), ("brokerage", "Brokerage"), ("trading", "Individual"), ("savings", "Savings")]
    for account in snap.accounts:
        held = sum(h.value for h in snap.holdings if h.account_id == account.id)
        assert round(held + account.cash, 2) == account.value
        assert 0 <= account.cash <= account.value
    assert {h.account_id for h in snap.holdings} == {"roth", "brokerage", "trading"}  # savings holds only cash


def test_holdings_are_priced_consistently_and_the_trading_account_holds_the_real_books_positions():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert all(h.value == round(h.quantity * h.price, 2) and h.name for h in snap.holdings)
    trading = {h.symbol: h.quantity for h in snap.holdings if h.account_id == "trading"}
    assert trading == {p.symbol: p.quantity for p in snap.positions if p.book_id == "rsi2-real"}
    assert [h.symbol for h in snap.holdings if h.cost_basis is None] == ["KO"]  # a cost the broker never reported
    assert len({h.symbol for h in snap.holdings}) == 13
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_profile.py tests/test_cli.py tests/test_demo_connector.py`
Expected: `20 failed, 47 passed`: every new feed-shape test (`Failed: DID NOT RAISE ProfileError`: the profile still takes any feed source); `test_a_feed_source_takes_a_url_or_a_path_and_its_options` loads its two good sources and fails only at its last check (`path = 5`). The moved `rails` examples in `test_cli.py` and `test_demo_connector.py` pass already: `rails` is still unavailable.

- [ ] **Step 3: Implement**

`src/kestrel/profile.py`:

````python
"""The personal profile: who you are, how kestrel looks, and where your data comes from.

profile.toml is gitignored. It never holds secrets: a source names the environment variable that holds its key.
"""

from __future__ import annotations

import re
import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Literal, get_args
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .contract import Category


class ProfileError(Exception):
    """A profile problem, worded so a person can fix it."""


_DURATION = re.compile(r"^\s*(\d+)\s*([mhd])\s*$")
# an environment variable's name in capitals: a token pasted in by mistake almost never looks like one
_ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")


def parse_duration(text: str) -> timedelta:
    match = _DURATION.match(text)
    if not match:
        raise ValueError(f"not a duration: {text!r} (use a number and m, h or d, e.g. 15m, 36h, 2d)")
    amount, unit = int(match.group(1)), match.group(2)
    return {"m": timedelta(minutes=amount), "h": timedelta(hours=amount), "d": timedelta(days=amount)}[unit]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class You(_Strict):
    name: str = "there"


class App(_Strict):
    name: str = "kestrel"
    accent: Literal["rufous", "slate", "mono"] = "rufous"
    theme: Literal["system", "dark", "light"] = "system"
    gain_loss: Literal["green-red", "blue-orange"] = "green-red"
    density: Literal["comfortable", "compact"] = "comfortable"
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")  # an ISO 4217 code, e.g. USD, EUR
    timezone: str = "America/New_York"

    @field_validator("timezone")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"unknown time zone {value!r} (use an IANA name such as America/New_York)") from None
        return value


class BenchmarkCfg(_Strict):
    symbol: str = "SPY"
    label: str = "S&P 500"


class SourceCfg(BaseModel):
    # connector-specific keys (path, url, token_env, seed) are allowed and read by the connector
    model_config = ConfigDict(extra="allow", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,31}$")
    kind: str
    label: str = ""
    stale_after: str = "36h"

    @field_validator("stale_after")
    @classmethod
    def _duration(cls, value: str) -> str:
        parse_duration(value)
        return value

    @model_validator(mode="after")
    def _known_categories(self) -> SourceCfg:
        # a typo in a category must stop the profile: silently falling back would file the money under another heading
        categories = getattr(self, "categories", None)
        if categories is None:
            return self
        if not isinstance(categories, dict):
            raise ValueError("categories must be a table: account id or label = category")
        known = get_args(Category)
        for key, value in categories.items():
            if value not in known:
                raise ValueError(f"unknown category {value!r} for {key!r} (use {', '.join(known[:-1])} or {known[-1]})")
        return self

    @model_validator(mode="after")
    def _feed_shape(self) -> SourceCfg:
        # a feed's shape is checked when the profile loads, and no message repeats a value back: a url or a
        # token_env can hold a secret written in the wrong place
        if self.kind != "feed":
            return self
        url, path = getattr(self, "url", None), getattr(self, "path", None)
        if (url is None) == (path is None):
            raise ValueError('a feed source needs exactly one of url and path, e.g. url = '
                             '"http://127.0.0.1:8000/api/feed" or path = "../desk/feed.json"')
        if url is not None:
            parts = urlsplit(url) if isinstance(url, str) else None
            if parts is None or parts.scheme not in ("http", "https") or not parts.hostname:
                raise ValueError("a feed url must start with http:// or https:// and name a host")
            if parts.username is not None or parts.password is not None:
                raise ValueError("a feed url can't carry a user name or password: put the token in an environment "
                                 "variable and name it in token_env")
        elif not isinstance(path, str) or not path:
            raise ValueError('a feed path is a file name in quotes, e.g. path = "../desk/feed.json"')
        token_env = getattr(self, "token_env", None)
        if token_env is not None:
            if path is not None:
                raise ValueError("token_env goes with a url: a feed file is read without a token")
            if not isinstance(token_env, str) or not _ENV_NAME.match(token_env):
                raise ValueError("token_env is the name of an environment variable in capitals, such as "
                                 "KESTREL_DESK_TOKEN, never the token itself")
        timeout = getattr(self, "timeout", 5)
        if isinstance(timeout, bool) or not isinstance(timeout, int | float) or not 1 <= timeout <= 60:
            raise ValueError("timeout is in seconds, from 1 to 60")
        return self

    @property
    def stale_delta(self) -> timedelta:
        return parse_duration(self.stale_after)


def _demo_sources() -> list[SourceCfg]:
    return [SourceCfg(id="demo", kind="demo", label="Demo data")]


class Profile(_Strict):
    you: You = You()
    app: App = App()
    benchmark: BenchmarkCfg = BenchmarkCfg()
    sources: list[SourceCfg] = Field(default_factory=_demo_sources)

    @model_validator(mode="after")
    def _unique_source_ids(self) -> Profile:
        ids = [s.id for s in self.sources]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate source id(s): {', '.join(dupes)}")
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.app.timezone)


DEMO_PROFILE = Profile(you=You(name="Alex"))


def _resolve_paths(raw: dict, folder: Path) -> None:
    """A `path` in a source may start with ~ (your home folder); a relative one is relative to the profile's own
    folder, not to wherever kestrel was started."""
    sources = raw.get("sources")
    for i, source in enumerate(sources if isinstance(sources, list) else []):
        if isinstance(source, dict) and isinstance(source.get("path"), str):
            try:
                path = Path(source["path"]).expanduser()
            except RuntimeError:  # an unknown ~user, or no home folder to put in place of ~
                raise ValueError(f"sources.{i}: can't expand ~ in {source['path']!r} (write the full path)") from None
            source["path"] = str(path if path.is_absolute() else (folder / path).resolve())


def load_profile(path: Path | None = None) -> tuple[Profile, str]:
    """Load a profile. With no path: ./profile.toml when it exists, else the built-in demo profile.

    Returns the profile and where it came from (for `kestrel check`). Relative and ~ source paths come back absolute.
    """
    if path is None:
        path = Path("profile.toml")
        if not path.exists():
            return DEMO_PROFILE, "built-in demo profile"
    try:
        text = path.read_text(encoding="utf-8-sig")  # -sig: Windows editors often save a byte-order mark
    except FileNotFoundError:
        raise ProfileError(f"{path}: file not found") from None
    except UnicodeDecodeError:
        raise ProfileError(f"{path}: is not UTF-8 text (save it as UTF-8 and try again)") from None
    except OSError as exc:
        raise ProfileError(f"{path}: could not read the file ({exc.strerror or exc})") from None
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"{path}: {exc}") from None
    try:
        _resolve_paths(raw, path.parent)
    except ValueError as exc:
        raise ProfileError(f"{path}: {exc}") from None
    try:
        return Profile.model_validate(raw), str(path)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors())
        raise ProfileError(f"{path}: {problems}") from None
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `219 passed` (`test_profile.py` 40, `test_cli.py` 12, `test_demo_connector.py` 15); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/profile.py tests/test_profile.py tests/test_cli.py tests/test_demo_connector.py
git commit -m "feat(profile): check a feed source's shape when the profile loads, without repeating a secret" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 2: The `feed` connector, part 1: read a file, check it, keep it

**Files:**
- Create: `src/kestrel/connectors/feed.py`, `tests/feed_fixture.py`, `tests/test_feed_connector.py`
- Modify (replace the whole file): `src/kestrel/connectors/base.py`

**Interfaces:**
- Consumes: `Snapshot`, `Source` (contract); `ConnectorError` (base); `kestrel.cli.main` (the test that feeds `kestrel demo`'s output back in).
- Produces:
  - `base.py` `DETAIL_LIMIT = 200`: how much of a source's error its row keeps (`collect()` switches from its literal `200` in Task 3).
  - `feed.py`: `MAX_BYTES` (20 × 1024 × 1024), `CLOCK_DRIFT` (five minutes), `SHOWN_PROBLEMS` (3), `NOT_JSON`;
    - `read_file(path) -> bytes`: `no feed file at <path>` (a folder too), `the feed file at <path> couldn't be read (…)`, `the feed file is more than 20 MB`;
    - `problems(ValidationError) -> str`: the first three problems as `field.path: message` joined by `; `, then `; and N more`, with fewer than three listed when three would pass `DETAIL_LIMIT`;
    - `parse(body) -> Snapshot`: UTF-8 with or without a byte-order mark; a body whose first non-space character is `<` is a web page; a JSON error with its line and column; nesting too deep to read; a missing `contract_version`; the contract's own message for another major version; otherwise `problems`;
    - `keep(snapshot, source_id, label, now) -> Snapshot`: a `generated_at` more than `CLOCK_DRIFT` ahead of `now` is refused; the payload's sources become one row (`kind = "feed"`, `last_success = min(generated_at, now)`, `status = "ok"`, detail `N books · N strategies · N trades`, with `N accounts · ` first when there are any);
    - `FeedConnector(source_id, label, *, path)`.
  - `tests/feed_fixture.py`: `MADE` (three minutes before the tests' `NOW`), `desk(**changes) -> dict` (a fictional desk: two books on one strategy, a day of history, a position, two trades, a run, an alert, a benchmark, and a source row of its own that kestrel replaces), `feed_file(folder, payload=None, name="feed.json") -> Path`.
  - Not registered yet: `build()` answers kind `feed` as unavailable until Task 3.

- [ ] **Step 1: Write the failing tests**

`tests/feed_fixture.py`:

````python
"""A small fictional feed payload for the feed connector's tests: a trading desk with two books on one strategy.

Every name and number here is made up.
"""

from __future__ import annotations

import json
from pathlib import Path

MADE = "2026-09-25T21:05:00+00:00"  # three minutes before the tests' NOW


def desk(**changes) -> dict:
    """The payload as JSON-ready data; keyword arguments replace its top-level fields."""
    payload = {
        "contract_version": "1",
        "generated_at": MADE,
        "sources": [{"id": "desk-broker", "label": "Broker link", "kind": "api", "status": "ok"}],
        "books": [
            {"id": "swing-real", "name": "Swing", "money": "real", "strategy_id": "swing", "status": "running",
             "started": "2026-03-02", "value": 2150.0, "slots_total": 4},
            {"id": "swing-paper", "name": "Swing (paper)", "money": "paper", "strategy_id": "swing",
             "status": "running", "started": "2026-01-05", "value": 10480.0, "slots_total": 6},
        ],
        "book_history": [
            {"id": "swing-real", "points": [{"date": "2026-09-24", "value": 2131.4},
                                            {"date": "2026-09-25", "value": 2150.0}]},
        ],
        "positions": [
            {"book_id": "swing-real", "symbol": "KO", "quantity": 5, "entry_price": 61.2, "last_price": 62.05,
             "stop_price": 56.3, "opened": "2026-09-22"},
        ],
        "trades": [
            {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "closed": "2026-09-11",
             "entry_price": 158.4, "exit_price": 162.1, "quantity": 3, "pnl": 11.1, "return_pct": 2.34,
             "exit_reason": "closed above its 5-day average"},
            {"book_id": "swing-paper", "symbol": "JNJ", "opened": "2026-09-14", "closed": "2026-09-18",
             "entry_price": 171.0, "exit_price": 168.2, "quantity": 10, "pnl": -28.0, "return_pct": -1.64,
             "exit_reason": "time stop"},
        ],
        "strategies": [{"id": "swing", "name": "Swing pullbacks",
                        "summary": "Buy a dip in an uptrend; sell the bounce."}],
        "runs": [{"time": "2026-09-25T19:56:00+00:00", "label": "Evening run", "book_id": "swing-real",
                  "status": "done"}],
        "alerts": [{"level": "warning", "title": "KO is near its stop", "detail": "8.2% of room left",
                    "link": "/strategies/swing"}],
        "benchmark": {"symbol": "SPY", "label": "S&P 500", "points": [{"date": "2026-09-24", "value": 655.1},
                                                                    {"date": "2026-09-25", "value": 657.3}]},
    }
    payload.update(changes)
    return payload


def feed_file(folder: Path, payload: dict | None = None, name: str = "feed.json") -> Path:
    """The payload saved as a feed file (the desk's payload when none is given)."""
    path = folder / name
    path.write_text(json.dumps(desk() if payload is None else payload), encoding="utf-8")
    return path
````


`tests/test_feed_connector.py`:

````python
import datetime as dt
import json
import os

import pytest
from feed_fixture import MADE, desk, feed_file

from kestrel.cli import main
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.feed import MAX_BYTES, FeedConnector
from kestrel.contract import Snapshot

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


def from_file(path):
    return FeedConnector("desk", "Trading desk", path=path).snapshot(NOW)


def refused(path) -> str:
    with pytest.raises(ConnectorError) as error:
        from_file(path)
    return str(error.value)


def test_a_valid_payload_from_a_file_keeps_every_list_and_the_benchmark_and_only_reads(tmp_path):
    path = feed_file(tmp_path)
    before = path.read_bytes()
    snap = from_file(path)
    expected = Snapshot.model_validate(desk())
    assert snap.model_dump(exclude={"sources"}) == expected.model_dump(exclude={"sources"})
    assert snap.benchmark is not None and snap.benchmark.symbol == "SPY"
    assert path.read_bytes() == before and os.listdir(tmp_path) == ["feed.json"]


def test_the_payloads_sources_are_replaced_by_one_row_for_the_feed(tmp_path):
    snap = from_file(feed_file(tmp_path))
    assert [s.model_dump() for s in snap.sources] == [{
        "id": "desk", "label": "Trading desk", "kind": "feed", "last_success": dt.datetime.fromisoformat(MADE),
        "status": "ok", "detail": "2 books · 1 strategy · 2 trades",
    }]


def test_alerts_pass_through_and_can_only_link_inside_kestrel(tmp_path):
    snap = from_file(feed_file(tmp_path))
    assert [(a.level, a.title, a.link) for a in snap.alerts] == [
        ("warning", "KO is near its stop", "/strategies/swing")]
    outside = desk(alerts=[{"level": "serious", "title": "Sign in again", "link": "https://desk.example.com/login"}])
    assert refused(feed_file(tmp_path, outside)).startswith("alerts.0.link: String should match pattern")


def test_kestrel_demo_prints_a_payload_a_feed_can_read(tmp_path, capsysbinary):
    main(["demo", "--now", NOW.isoformat()])
    path = tmp_path / "demo.json"
    path.write_bytes(capsysbinary.readouterr().out)
    snap = from_file(path)
    assert snap.sources[0].detail == "4 accounts · 5 books · 4 strategies · 136 trades"
    assert [a.id for a in snap.accounts] == ["roth", "brokerage", "trading", "savings"]


def test_a_byte_order_mark_is_fine(tmp_path):
    path = tmp_path / "feed.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(desk()).encode("utf-8"))
    assert len(from_file(path).books) == 2


def test_a_missing_file_is_named(tmp_path):
    assert refused(tmp_path / "nope.json") == f"no feed file at {tmp_path / 'nope.json'}"
    assert refused(tmp_path) == f"no feed file at {tmp_path}"  # a folder is not a feed file


def test_a_file_over_20_mb_is_refused_and_20_mb_exactly_is_read(tmp_path):
    body = json.dumps(desk()).encode("utf-8")
    path = tmp_path / "feed.json"
    path.write_bytes(body + b" " * (MAX_BYTES - len(body)))
    assert len(from_file(path).books) == 2
    path.write_bytes(body + b" " * (MAX_BYTES - len(body) + 1))
    assert refused(path) == "the feed file is more than 20 MB"


@pytest.mark.parametrize("body,why", [
    (b"", "(line 1, column 1: Expecting value)"),
    (b"{'books': []}", "(line 1, column 2: Expecting property name enclosed in double quotes)"),
    ('{"note": "café"}'.encode("latin-1"), "(it isn't UTF-8 text)"),
    (b"[" * 100_000, "(it is nested too deeply to read)"),
], ids=["empty", "single quotes", "latin-1", "nested"])
def test_something_that_isnt_json_is_refused(tmp_path, body, why):
    path = tmp_path / "feed.json"
    path.write_bytes(body)
    assert refused(path) == f"the feed sent something that isn't JSON {why}"


def test_a_web_page_such_as_a_sign_in_page_is_named(tmp_path):
    path = tmp_path / "feed.json"
    path.write_bytes(b"\n  <!DOCTYPE html>\n<html><head><title>Sign in</title></head><body><form></form></body></html>")
    assert refused(path) == ("the feed sent something that isn't JSON: "
                             "a web page (a sign-in page, or the wrong address?)")


@pytest.mark.parametrize("version", ["2", "2.0", "0"])
def test_another_major_version_is_refused_with_the_contracts_own_message(tmp_path, version):
    message = refused(feed_file(tmp_path, desk(contract_version=version, books="not even a list")))
    assert message == f"unsupported contract version {version!r}; this kestrel reads major version 1"


def test_a_newer_minor_version_loads_and_a_payload_must_say_its_version(tmp_path):
    assert len(from_file(feed_file(tmp_path, desk(contract_version="1.4", extra_field={"a": 1}))).books) == 2
    payload = desk()
    del payload["contract_version"]
    assert refused(feed_file(tmp_path, payload)) == (
        "the feed doesn't say which contract it speaks: add \"contract_version\": \"1\"")


def test_a_validation_error_lists_the_first_three_problems_then_how_many_more(tmp_path):
    payload = desk()
    payload["books"][0]["money"] = "cash"
    payload["books"][1]["value"] = "lots"
    del payload["trades"][0]["pnl"]
    payload["trades"][1]["closed"] = "soon"
    payload["runs"][0]["status"] = "maybe"
    assert refused(feed_file(tmp_path, payload)) == (
        "books.0.money: Input should be 'real' or 'paper'; "
        "books.1.value: Input should be a valid number, unable to parse string as a number; "
        "trades.0.pnl: Field required; and 2 more")


def test_problems_too_long_for_a_source_row_are_fewer_but_still_counted(tmp_path):
    chart = {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "stop": "x",
             "bars": [{"date": "2026-09-08", "open": "x", "high": 159.0, "low": 157.9, "close": 158.4}]}
    payload = desk(trade_charts=[chart])
    payload["runs"][0]["status"] = "maybe"
    message = refused(feed_file(tmp_path, payload))
    assert message == (
        "trade_charts.0.bars.0.open: Input should be a valid number, unable to parse string as a number; "
        "trade_charts.0.stop: Input should be a valid number, unable to parse string as a number; and 1 more")
    assert len(message) <= 200  # what a source row keeps of an error


def test_not_a_json_object_is_a_problem_of_the_whole_payload(tmp_path):
    assert refused(feed_file(tmp_path, [desk()])) == "Input should be a valid dictionary or instance of Snapshot"


def test_a_payload_from_the_future_is_refused_beyond_five_minutes_of_clock_drift(tmp_path):
    drift = from_file(feed_file(tmp_path, desk(generated_at="2026-09-25T21:12:00+00:00")))
    assert drift.sources[0].last_success == NOW  # four minutes ahead: this computer's clock is the one shown
    ahead = desk(generated_at="2026-09-25T21:08:00-04:00")  # a local time given the wrong offset: 4 hours ahead
    assert refused(feed_file(tmp_path, ahead)) == (
        "the feed's generated_at is 4 hours ahead of this computer's clock: "
        "check the clock and time zone where the feed is made")
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_feed_connector.py`
Expected: a collection error, `ModuleNotFoundError: No module named 'kestrel.connectors.feed'` (`1 error`).

- [ ] **Step 3: Implement**

`src/kestrel/connectors/base.py`:

````python
"""What every connector provides."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..contract import Snapshot

DETAIL_LIMIT = 200  # how much of a source's error its row keeps: a sidebar line, not a log


class Connector(Protocol):
    source_id: str

    def snapshot(self, now: datetime) -> Snapshot:
        """Everything this source knows, as of `now`. Read-only: a connector never writes to its source."""
        ...


class ConnectorUnavailable(Exception):
    """The profile names a connector kind this version of kestrel does not have."""


class ConnectorError(Exception):
    """A source that can't be read, worded so a person can fix it. It shows as that source's error."""
````


`src/kestrel/connectors/feed.py`:

````python
"""A feed: one JSON document in the contract's own format (a Snapshot), read from a file, checked, and handed on.
This is how a system of your own (a trading desk) shows its books, strategies, trades and runs; kestrel knows
nothing else about it.

The connector only reads, once per snapshot, and caches nothing: a feed is small and its system is local.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import ValidationError

from ..contract import Snapshot, Source
from .base import DETAIL_LIMIT, ConnectorError

MAX_BYTES = 20 * 1024 * 1024  # 20 MB: far more than any feed needs, and a stop for one that never ends
CLOCK_DRIFT = timedelta(minutes=5)  # how far a feed's clock may run ahead of this one before its time is refused
SHOWN_PROBLEMS = 3
NOT_JSON = "the feed sent something that isn't JSON"


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _span(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return _count(minutes, "minute", "minutes")
    hours = minutes // 60
    return _count(hours, "hour", "hours") if hours < 48 else _count(hours // 24, "day", "days")


def read_file(path: Path) -> bytes:
    if not path.is_file():
        raise ConnectorError(f"no feed file at {path}")
    try:
        with path.open("rb") as f:
            body = f.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ConnectorError(f"the feed file at {path} couldn't be read ({exc.strerror or exc})") from None
    if len(body) > MAX_BYTES:
        raise ConnectorError("the feed file is more than 20 MB")
    return body


def problems(exc: ValidationError) -> str:
    """The first three problems as `field.path: message`, then how many more; fewer than three when three wouldn't
    fit in a source row, so the count always shows."""
    found = [f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" if e["loc"] else e["msg"]
             for e in exc.errors()]
    shown = min(SHOWN_PROBLEMS, len(found))
    while True:
        more = len(found) - shown
        text = "; ".join(found[:shown]) + (f"; and {more} more" if more else "")
        if len(text) <= DETAIL_LIMIT or shown <= 1:
            return text
        shown -= 1


def parse(body: bytes) -> Snapshot:
    """The body as a Snapshot, or a ConnectorError that says what is wrong with it."""
    try:
        text = body.decode("utf-8-sig")  # -sig: a byte-order mark is fine
    except UnicodeDecodeError:
        raise ConnectorError(f"{NOT_JSON} (it isn't UTF-8 text)") from None
    if text.lstrip().startswith("<"):
        raise ConnectorError(f"{NOT_JSON}: a web page (a sign-in page, or the wrong address?)")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"{NOT_JSON} (line {exc.lineno}, column {exc.colno}: {exc.msg})") from None
    except RecursionError:
        raise ConnectorError(f"{NOT_JSON} (it is nested too deeply to read)") from None
    if isinstance(payload, dict) and "contract_version" not in payload:
        # the contract defaults a missing version to 1; a feed must say it, so a future one can't pass for this one
        raise ConnectorError('the feed doesn\'t say which contract it speaks: add "contract_version": "1"')
    try:
        return Snapshot.model_validate(payload)
    except ValidationError as exc:
        for e in exc.errors():
            if e["loc"] == ("contract_version",) and e["type"] == "value_error":
                raise ConnectorError(str(e["ctx"]["error"])) from None  # the contract's own words
        raise ConnectorError(problems(exc)) from None


def keep(snapshot: Snapshot, source_id: str, label: str, now: datetime) -> Snapshot:
    """What kestrel keeps of a payload: every list and the benchmark, with the payload's own sources replaced by one
    row for this feed, whose last success is when the payload was made."""
    made = snapshot.generated_at
    if made - now > CLOCK_DRIFT:
        raise ConnectorError(f"the feed's generated_at is {_span(made - now)} ahead of this computer's clock: "
                             "check the clock and time zone where the feed is made")
    counts = [_count(len(snapshot.books), "book", "books"), _count(len(snapshot.strategies), "strategy", "strategies"),
              _count(len(snapshot.trades), "trade", "trades")]
    if snapshot.accounts:
        counts.insert(0, _count(len(snapshot.accounts), "account", "accounts"))
    source = Source(id=source_id, label=label, kind="feed", last_success=min(made, now), status="ok",
                    detail=" · ".join(counts))
    return snapshot.model_copy(update={"sources": [source]})


class FeedConnector:
    """Reads one feed file."""

    def __init__(self, source_id: str, label: str, *, path: Path) -> None:
        self.source_id = source_id
        self.label = label
        self.path = path

    def snapshot(self, now: datetime) -> Snapshot:
        return keep(parse(read_file(self.path)), self.source_id, self.label, now)
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `239 passed` (`test_feed_connector.py` 20); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/connectors/base.py src/kestrel/connectors/feed.py tests/feed_fixture.py tests/test_feed_connector.py
git commit -m "feat(feed): read a feed file, check it against the contract, and keep it as one source" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 3: The `feed` connector, part 2: one GET, the token, the caps; registered

**Files:**
- Modify (replace the whole file): `src/kestrel/connectors/feed.py`, `src/kestrel/connectors/__init__.py`, `tests/feed_fixture.py`, `tests/test_feed_connector.py`

**Interfaces:**
- Consumes: Task 1's checked `SourceCfg`; Task 2's `read_file`, `parse`, `keep`, `problems` and fixture.
- Produces:
  - `feed.py` `TIMEOUT = 5.0`, `CHUNK` (64 KB); `FeedConnector(source_id, label, *, url=None, path=None, token_env=None, timeout=TIMEOUT)`, which reads the `url` when there is one, else the file;
    - `_opener()`: an `OpenerDirector` with only the HTTP, HTTPS, error and unknown-scheme handlers, so no proxy, no redirect handler and no cookie jar;
    - `_read(response, deadline, timeout)`: a `Content-Length` over the cap is refused before reading; otherwise `read1` in 64 KB chunks, stopped one byte past the cap or at the deadline;
    - `_shown(url)`: a URL without user info or query; `_why(reason)`: an `OSError`'s own words;
    - `FeedConnector._token()`: `set NAME in the environment (token_env)` for a missing or blank variable (trimmed first); a token with anything but visible ASCII is refused without being shown;
    - `FeedConnector._fetch(url)`: one GET with `Accept: application/json` and the token as an unredirected `Authorization: Bearer …` header; `the feed answered N` (anything but 200, 2xx included); `the feed redirected to <target>; kestrel doesn't follow redirects (set url to the feed's own address)`; `the feed didn't answer within N s`; `the feed was still sending after N s`; `the feed sent more than 20 MB`; `the feed couldn't be reached (…)`; `the feed couldn't be read (…)`.
  - `connectors.build`: kind `"feed"` builds a `FeedConnector` from the source's `url` or `path`, `token_env` and `timeout` (a float, default 5); `collect()` cuts an error at `DETAIL_LIMIT`.
  - `tests/feed_fixture.py` adds `FeedServer(reply)` (a server on 127.0.0.1 in a thread: `.url`, `.requests` with lower-case header names, `.close()`) and the replies `answer(body, status=200, headers=None, length=True)`, `hang`, `trickle` and `hang_up`.

- [ ] **Step 1: Write the failing tests (replace the whole files)**

`tests/feed_fixture.py`:

````python
"""A small fictional feed payload for the feed connector's tests (a trading desk with two books on one strategy),
and a feed server on 127.0.0.1 in a thread, so no test ever needs the network.

Every name and number here is made up.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

Reply = Callable[[BaseHTTPRequestHandler], None]

MADE = "2026-09-25T21:05:00+00:00"  # three minutes before the tests' NOW


def desk(**changes) -> dict:
    """The payload as JSON-ready data; keyword arguments replace its top-level fields."""
    payload = {
        "contract_version": "1",
        "generated_at": MADE,
        "sources": [{"id": "desk-broker", "label": "Broker link", "kind": "api", "status": "ok"}],
        "books": [
            {"id": "swing-real", "name": "Swing", "money": "real", "strategy_id": "swing", "status": "running",
             "started": "2026-03-02", "value": 2150.0, "slots_total": 4},
            {"id": "swing-paper", "name": "Swing (paper)", "money": "paper", "strategy_id": "swing",
             "status": "running", "started": "2026-01-05", "value": 10480.0, "slots_total": 6},
        ],
        "book_history": [
            {"id": "swing-real", "points": [{"date": "2026-09-24", "value": 2131.4},
                                            {"date": "2026-09-25", "value": 2150.0}]},
        ],
        "positions": [
            {"book_id": "swing-real", "symbol": "KO", "quantity": 5, "entry_price": 61.2, "last_price": 62.05,
             "stop_price": 56.3, "opened": "2026-09-22"},
        ],
        "trades": [
            {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "closed": "2026-09-11",
             "entry_price": 158.4, "exit_price": 162.1, "quantity": 3, "pnl": 11.1, "return_pct": 2.34,
             "exit_reason": "closed above its 5-day average"},
            {"book_id": "swing-paper", "symbol": "JNJ", "opened": "2026-09-14", "closed": "2026-09-18",
             "entry_price": 171.0, "exit_price": 168.2, "quantity": 10, "pnl": -28.0, "return_pct": -1.64,
             "exit_reason": "time stop"},
        ],
        "strategies": [{"id": "swing", "name": "Swing pullbacks",
                        "summary": "Buy a dip in an uptrend; sell the bounce."}],
        "runs": [{"time": "2026-09-25T19:56:00+00:00", "label": "Evening run", "book_id": "swing-real",
                  "status": "done"}],
        "alerts": [{"level": "warning", "title": "KO is near its stop", "detail": "8.2% of room left",
                    "link": "/strategies/swing"}],
        "benchmark": {"symbol": "SPY", "label": "S&P 500", "points": [{"date": "2026-09-24", "value": 655.1},
                                                                    {"date": "2026-09-25", "value": 657.3}]},
    }
    payload.update(changes)
    return payload


def feed_file(folder: Path, payload: dict | None = None, name: str = "feed.json") -> Path:
    """The payload saved as a feed file (the desk's payload when none is given)."""
    path = folder / name
    path.write_text(json.dumps(desk() if payload is None else payload), encoding="utf-8")
    return path


class FeedServer:
    """A feed answered from a thread: `reply(handler)` writes each answer; `requests` keeps each request's method,
    path and headers (names in lower case)."""

    def __init__(self, reply: Reply) -> None:
        self.requests: list[dict[str, str]] = []
        feed = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                feed.requests.append({"method": self.command, "path": self.path,
                                      **{name.lower(): value for name, value in self.headers.items()}})
                try:
                    reply(self)
                except ConnectionError:
                    pass  # kestrel hung up first, as it should on a slow or huge answer

            def log_message(self, *args) -> None:
                pass  # keep the test output quiet

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.stop = threading.Event()  # set when the test ends, so a reply that waits returns
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        # a short poll, so closing the server at the end of a test doesn't wait half a second
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.httpd.stop.set()
        self.httpd.shutdown()
        self.httpd.server_close()


def answer(body: bytes | dict | list, status: int = 200, headers: dict[str, str] | None = None,
           length: bool = True) -> Reply:
    """One answer: data goes as JSON; `length=False` leaves out Content-Length, so the body ends when the connection
    closes."""
    data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")

    def reply(handler: BaseHTTPRequestHandler) -> None:
        handler.send_response(status)
        for name, value in (headers or {"Content-Type": "application/json"}).items():
            handler.send_header(name, value)
        if length:
            handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    return reply


def hang(handler: BaseHTTPRequestHandler) -> None:
    """Never answer (until the test ends)."""
    handler.server.stop.wait(10)


def trickle(handler: BaseHTTPRequestHandler) -> None:
    """Answer at once, then send the body a byte every 50 ms, forever: each read on the socket gets something."""
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(f'{{"contract_version": "1", "generated_at": "{MADE}", "note": "'.encode("utf-8"))
    while not handler.server.stop.wait(0.05):
        handler.wfile.write(b"z")


def hang_up(handler: BaseHTTPRequestHandler) -> None:
    """Close the connection without a word."""
    handler.close_connection = True
````


`tests/test_feed_connector.py`:

````python
import datetime as dt
import json
import logging
import os
import time

import pytest
from feed_fixture import MADE, FeedServer, answer, desk, feed_file, hang, hang_up, trickle

from kestrel.cli import main
from kestrel.connectors import build, collect
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.feed import MAX_BYTES, FeedConnector
from kestrel.contract import Snapshot
from kestrel.profile import Profile, SourceCfg, load_profile

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
TOKEN = "kst_9f8e7d6c5b4a3210"  # a made-up token


@pytest.fixture
def serve():
    servers = []

    def start(reply):
        server = FeedServer(reply)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.close()


def from_file(path):
    return FeedConnector("desk", "Trading desk", path=path).snapshot(NOW)


def refused(path) -> str:
    with pytest.raises(ConnectorError) as error:
        from_file(path)
    return str(error.value)


def test_a_valid_payload_from_a_file_keeps_every_list_and_the_benchmark_and_only_reads(tmp_path):
    path = feed_file(tmp_path)
    before = path.read_bytes()
    snap = from_file(path)
    expected = Snapshot.model_validate(desk())
    assert snap.model_dump(exclude={"sources"}) == expected.model_dump(exclude={"sources"})
    assert snap.benchmark is not None and snap.benchmark.symbol == "SPY"
    assert path.read_bytes() == before and os.listdir(tmp_path) == ["feed.json"]


def test_the_payloads_sources_are_replaced_by_one_row_for_the_feed(tmp_path):
    snap = from_file(feed_file(tmp_path))
    assert [s.model_dump() for s in snap.sources] == [{
        "id": "desk", "label": "Trading desk", "kind": "feed", "last_success": dt.datetime.fromisoformat(MADE),
        "status": "ok", "detail": "2 books · 1 strategy · 2 trades",
    }]


def test_alerts_pass_through_and_can_only_link_inside_kestrel(tmp_path):
    snap = from_file(feed_file(tmp_path))
    assert [(a.level, a.title, a.link) for a in snap.alerts] == [
        ("warning", "KO is near its stop", "/strategies/swing")]
    outside = desk(alerts=[{"level": "serious", "title": "Sign in again", "link": "https://desk.example.com/login"}])
    assert refused(feed_file(tmp_path, outside)).startswith("alerts.0.link: String should match pattern")


def test_kestrel_demo_prints_a_payload_a_feed_can_read(tmp_path, capsysbinary):
    main(["demo", "--now", NOW.isoformat()])
    path = tmp_path / "demo.json"
    path.write_bytes(capsysbinary.readouterr().out)
    snap = from_file(path)
    assert snap.sources[0].detail == "4 accounts · 5 books · 4 strategies · 136 trades"
    assert [a.id for a in snap.accounts] == ["roth", "brokerage", "trading", "savings"]


def test_a_byte_order_mark_is_fine(tmp_path):
    path = tmp_path / "feed.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(desk()).encode("utf-8"))
    assert len(from_file(path).books) == 2


def test_a_missing_file_is_named(tmp_path):
    assert refused(tmp_path / "nope.json") == f"no feed file at {tmp_path / 'nope.json'}"
    assert refused(tmp_path) == f"no feed file at {tmp_path}"  # a folder is not a feed file


def test_a_file_over_20_mb_is_refused_and_20_mb_exactly_is_read(tmp_path):
    body = json.dumps(desk()).encode("utf-8")
    path = tmp_path / "feed.json"
    path.write_bytes(body + b" " * (MAX_BYTES - len(body)))
    assert len(from_file(path).books) == 2
    path.write_bytes(body + b" " * (MAX_BYTES - len(body) + 1))
    assert refused(path) == "the feed file is more than 20 MB"


@pytest.mark.parametrize("body,why", [
    (b"", "(line 1, column 1: Expecting value)"),
    (b"{'books': []}", "(line 1, column 2: Expecting property name enclosed in double quotes)"),
    ('{"note": "café"}'.encode("latin-1"), "(it isn't UTF-8 text)"),
    (b"[" * 100_000, "(it is nested too deeply to read)"),
], ids=["empty", "single quotes", "latin-1", "nested"])
def test_something_that_isnt_json_is_refused(tmp_path, body, why):
    path = tmp_path / "feed.json"
    path.write_bytes(body)
    assert refused(path) == f"the feed sent something that isn't JSON {why}"


def test_a_web_page_such_as_a_sign_in_page_is_named(tmp_path):
    path = tmp_path / "feed.json"
    path.write_bytes(b"\n  <!DOCTYPE html>\n<html><head><title>Sign in</title></head><body><form></form></body></html>")
    assert refused(path) == ("the feed sent something that isn't JSON: "
                             "a web page (a sign-in page, or the wrong address?)")


@pytest.mark.parametrize("version", ["2", "2.0", "0"])
def test_another_major_version_is_refused_with_the_contracts_own_message(tmp_path, version):
    message = refused(feed_file(tmp_path, desk(contract_version=version, books="not even a list")))
    assert message == f"unsupported contract version {version!r}; this kestrel reads major version 1"


def test_a_newer_minor_version_loads_and_a_payload_must_say_its_version(tmp_path):
    assert len(from_file(feed_file(tmp_path, desk(contract_version="1.4", extra_field={"a": 1}))).books) == 2
    payload = desk()
    del payload["contract_version"]
    assert refused(feed_file(tmp_path, payload)) == (
        "the feed doesn't say which contract it speaks: add \"contract_version\": \"1\"")


def test_a_validation_error_lists_the_first_three_problems_then_how_many_more(tmp_path):
    payload = desk()
    payload["books"][0]["money"] = "cash"
    payload["books"][1]["value"] = "lots"
    del payload["trades"][0]["pnl"]
    payload["trades"][1]["closed"] = "soon"
    payload["runs"][0]["status"] = "maybe"
    assert refused(feed_file(tmp_path, payload)) == (
        "books.0.money: Input should be 'real' or 'paper'; "
        "books.1.value: Input should be a valid number, unable to parse string as a number; "
        "trades.0.pnl: Field required; and 2 more")


def test_problems_too_long_for_a_source_row_are_fewer_but_still_counted(tmp_path):
    chart = {"book_id": "swing-real", "symbol": "PG", "opened": "2026-09-08", "stop": "x",
             "bars": [{"date": "2026-09-08", "open": "x", "high": 159.0, "low": 157.9, "close": 158.4}]}
    payload = desk(trade_charts=[chart])
    payload["runs"][0]["status"] = "maybe"
    message = refused(feed_file(tmp_path, payload))
    assert message == (
        "trade_charts.0.bars.0.open: Input should be a valid number, unable to parse string as a number; "
        "trade_charts.0.stop: Input should be a valid number, unable to parse string as a number; and 1 more")
    assert len(message) <= 200  # what a source row keeps of an error


def test_not_a_json_object_is_a_problem_of_the_whole_payload(tmp_path):
    assert refused(feed_file(tmp_path, [desk()])) == "Input should be a valid dictionary or instance of Snapshot"


def test_a_payload_from_the_future_is_refused_beyond_five_minutes_of_clock_drift(tmp_path):
    drift = from_file(feed_file(tmp_path, desk(generated_at="2026-09-25T21:12:00+00:00")))
    assert drift.sources[0].last_success == NOW  # four minutes ahead: this computer's clock is the one shown
    ahead = desk(generated_at="2026-09-25T21:08:00-04:00")  # a local time given the wrong offset: 4 hours ahead
    assert refused(feed_file(tmp_path, ahead)) == (
        "the feed's generated_at is 4 hours ahead of this computer's clock: "
        "check the clock and time zone where the feed is made")


def over_http(url, **options):
    return FeedConnector("desk", "Trading desk", url=url, **options).snapshot(NOW)


def refused_over_http(url, **options) -> str:
    with pytest.raises(ConnectorError) as error:
        over_http(url, **options)
    return str(error.value)


def test_a_valid_payload_over_http_is_one_plain_get_and_matches_the_file(tmp_path, serve):
    server = serve(answer(desk()))
    snap = over_http(server.url + "/api/feed")
    assert snap.model_dump() == from_file(feed_file(tmp_path)).model_dump()
    [request] = server.requests
    assert (request["method"], request["path"], request["accept"]) == ("GET", "/api/feed", "application/json")
    assert "authorization" not in request and "cookie" not in request


def test_the_token_goes_in_a_bearer_header_when_token_env_is_set(serve, monkeypatch):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", f"  {TOKEN}\n")  # the spaces and newline a .env line can leave
    server = serve(answer(desk()))
    over_http(server.url, token_env="KESTREL_TEST_TOKEN")
    assert server.requests[0]["authorization"] == f"Bearer {TOKEN}"


def test_a_missing_or_empty_token_variable_is_an_error_that_names_it(serve, monkeypatch):
    server = serve(answer(desk()))
    monkeypatch.delenv("KESTREL_TEST_TOKEN", raising=False)
    assert refused_over_http(server.url, token_env="KESTREL_TEST_TOKEN") == (
        "set KESTREL_TEST_TOKEN in the environment (token_env)")
    monkeypatch.setenv("KESTREL_TEST_TOKEN", "   ")
    assert refused_over_http(server.url, token_env="KESTREL_TEST_TOKEN") == (
        "set KESTREL_TEST_TOKEN in the environment (token_env)")
    assert server.requests == []  # nothing is sent without it


def test_a_token_a_header_cant_carry_is_refused_without_showing_it(serve, monkeypatch):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", f"{TOKEN}\r\nX-Extra: 1")
    server = serve(answer(desk()))
    message = refused_over_http(server.url, token_env="KESTREL_TEST_TOKEN")
    assert message == ("the token in KESTREL_TEST_TOKEN has a character a header can't carry "
                       "(a space or a line break?)")
    assert server.requests == []


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_a_redirect_is_refused_and_the_token_never_follows_it(serve, monkeypatch, code):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", TOKEN)
    elsewhere = serve(answer(desk()))
    server = serve(answer(b"", status=code, headers={"Location": f"{elsewhere.url}/login?session=a1b2c3"}))
    message = refused_over_http(server.url + "/api/feed", token_env="KESTREL_TEST_TOKEN")
    assert message == (f"the feed redirected to {elsewhere.url}/login; "
                       "kestrel doesn't follow redirects (set url to the feed's own address)")
    assert elsewhere.requests == []


def test_a_redirect_to_a_path_is_named_in_full(serve):
    server = serve(answer(b"", status=302, headers={"Location": "/sign-in"}))
    assert refused_over_http(server.url + "/api/feed").startswith(f"the feed redirected to {server.url}/sign-in; ")


@pytest.mark.parametrize("code", [503, 404, 401, 204])
def test_a_status_other_than_200_is_an_error(serve, code):
    server = serve(answer(b"" if code == 204 else b'{"error": "no"}', status=code))
    assert refused_over_http(server.url) == f"the feed answered {code}"


def test_a_feed_that_doesnt_answer_in_time_is_cut_off(serve):
    server = serve(hang)
    started = time.monotonic()
    assert refused_over_http(server.url, timeout=0.3) == "the feed didn't answer within 0.3 s"
    assert time.monotonic() - started < 2


def test_a_slow_trickle_is_cut_off_at_the_timeout(serve):
    server = serve(trickle)
    started = time.monotonic()
    assert refused_over_http(server.url, timeout=0.5) == "the feed was still sending after 0.5 s"
    assert time.monotonic() - started < 2  # a byte every 50 ms never trips a per-read timeout


def test_more_than_20_mb_in_one_line_is_refused_whether_or_not_the_feed_says_so_up_front(serve):
    head = f'{{"contract_version": "1", "generated_at": "{MADE}", "note": "'.encode("utf-8")
    exactly = head + b"z" * (MAX_BYTES - len(head) - 2) + b'"}'
    assert len(over_http(serve(answer(exactly, length=False)).url).books) == 0
    one_line = exactly[:-2] + b'z"}'  # one byte over, no newline anywhere, no Content-Length
    assert refused_over_http(serve(answer(one_line, length=False)).url) == "the feed sent more than 20 MB"
    declared = serve(answer(b"{}", headers={"Content-Length": str(MAX_BYTES + 1)}, length=False))
    assert refused_over_http(declared.url) == "the feed sent more than 20 MB"


def test_a_sign_in_page_over_http_is_named(serve):
    page = b"<!doctype html><html><body><h1>Sign in</h1></body></html>"
    server = serve(answer(page, headers={"Content-Type": "text/html"}))
    assert refused_over_http(server.url) == ("the feed sent something that isn't JSON: "
                                             "a web page (a sign-in page, or the wrong address?)")


def test_a_feed_that_hangs_up_without_answering_is_an_error(serve):
    server = serve(hang_up)
    assert refused_over_http(server.url) == (
        "the feed couldn't be read (Remote end closed connection without response)")


def test_no_proxy_is_used_so_the_token_goes_only_to_the_feed(serve, monkeypatch):
    proxy = serve(answer(desk(books=[])))
    for name in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.setenv(name, proxy.url)
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("KESTREL_TEST_TOKEN", TOKEN)
    server = serve(answer(desk()))
    assert len(over_http(server.url, token_env="KESTREL_TEST_TOKEN").books) == 2
    assert proxy.requests == [] and len(server.requests) == 1


def test_the_token_never_shows_in_an_error_or_a_log(serve, monkeypatch, caplog, capsys):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", TOKEN)
    caplog.set_level(logging.DEBUG)
    replies = [answer(b"", status=503), answer(b"", status=302, headers={"Location": "/login"}),
               answer(b"<html></html>"), hang_up, answer(desk(contract_version="2")), answer(desk(books=[{}]))]
    messages = [refused_over_http(serve(reply).url, token_env="KESTREL_TEST_TOKEN") for reply in replies]
    out, err = capsys.readouterr()
    assert len(messages) == 6 and not [m for m in messages if TOKEN in m]
    assert TOKEN not in caplog.text and TOKEN not in out + err


def test_a_feed_url_in_a_profile_is_read_through_collect_with_its_options(serve, monkeypatch):
    monkeypatch.setenv("KESTREL_TEST_TOKEN", TOKEN)
    server = serve(answer(desk()))
    profile = Profile(sources=[SourceCfg(id="desk", kind="feed", label="Trading desk", url=server.url,
                                         token_env="KESTREL_TEST_TOKEN", timeout=30, stale_after="15m")])
    assert build(profile.sources[0], profile).timeout == 30.0
    assert build(SourceCfg(id="desk", kind="feed", url=server.url), profile).timeout == 5.0
    snap = collect(profile, NOW)
    assert [(s.id, s.label, s.kind, s.status, s.detail) for s in snap.sources] == [
        ("desk", "Trading desk", "feed", "ok", "2 books · 1 strategy · 2 trades")]
    later = collect(profile, NOW + dt.timedelta(minutes=20))  # the payload is 23 minutes old by then
    assert later.sources[0].status == "stale"
    assert server.requests[0]["authorization"] == f"Bearer {TOKEN}"


def test_a_feed_file_is_found_from_the_profiles_folder_and_a_broken_feed_is_a_red_row(tmp_path, monkeypatch):
    (tmp_path / "desk").mkdir()
    feed_file(tmp_path / "desk")
    (tmp_path / "kestrel").mkdir()
    (tmp_path / "kestrel" / "profile.toml").write_text(
        '[[sources]]\nid = "demo"\nkind = "demo"\n'
        '[[sources]]\nid = "desk"\nkind = "feed"\nlabel = "Trading desk"\npath = "../desk/feed.json"\n'
        '[[sources]]\nid = "night"\nkind = "feed"\nlabel = "Night desk"\nurl = "http://127.0.0.1:9/feed"\n'
        'token_env = "KESTREL_NIGHT_TOKEN"\n', encoding="utf-8")
    monkeypatch.delenv("KESTREL_NIGHT_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path / "desk")  # anywhere but the profile's folder
    profile, _ = load_profile(tmp_path / "kestrel" / "profile.toml")
    snap = collect(profile, NOW)
    rows = {s.id: (s.status, s.detail) for s in snap.sources}
    assert rows["desk"] == ("ok", "2 books · 1 strategy · 2 trades")
    assert rows["night"] == ("error", "set KESTREL_NIGHT_TOKEN in the environment (token_env)")
    assert len(snap.accounts) == 4 and len(snap.books) == 7  # the demo's and the desk's
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_feed_connector.py`
Expected: `23 failed, 20 passed`: the 21 tests that give the connector a `url` (`TypeError: FeedConnector.__init__() got an unexpected keyword argument 'url'`), and the two profile tests, where kind `feed` isn't registered yet: `build` raises `ConnectorUnavailable: connector kind 'feed' is not available in this version of kestrel`, and in `collect()` the desk is an error row that says so (`AssertionError: assert ('error', 'co...n of kestrel') == ('ok', '2 boo...y · 2 trades')`). Task 2's 20 tests still pass.

- [ ] **Step 3: Implement (replace the whole files)**

`src/kestrel/connectors/feed.py`:

````python
"""A feed: one JSON document in the contract's own format (a Snapshot), read from a URL or a file, checked, and
handed on. This is how a system of your own (a trading desk) shows its books, strategies, trades and runs; kestrel
knows nothing else about it.

The connector only reads: one GET, or one file read, per snapshot, and nothing is cached (a feed is small and its
system is local). The token, when there is one, goes in that GET's Authorization header and nowhere else: never in a
message, never in a log, never to a redirect or a proxy.
"""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from pydantic import ValidationError

from ..contract import Snapshot, Source
from .base import DETAIL_LIMIT, ConnectorError

TIMEOUT = 5.0  # seconds, unless the profile says otherwise (1 to 60)
MAX_BYTES = 20 * 1024 * 1024  # 20 MB: far more than any feed needs, and a stop for one that never ends
CHUNK = 64 * 1024
CLOCK_DRIFT = timedelta(minutes=5)  # how far a feed's clock may run ahead of this one before its time is refused
SHOWN_PROBLEMS = 3
NOT_JSON = "the feed sent something that isn't JSON"


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _span(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return _count(minutes, "minute", "minutes")
    hours = minutes // 60
    return _count(hours, "hour", "hours") if hours < 48 else _count(hours // 24, "day", "days")


def read_file(path: Path) -> bytes:
    if not path.is_file():
        raise ConnectorError(f"no feed file at {path}")
    try:
        with path.open("rb") as f:
            body = f.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ConnectorError(f"the feed file at {path} couldn't be read ({exc.strerror or exc})") from None
    if len(body) > MAX_BYTES:
        raise ConnectorError("the feed file is more than 20 MB")
    return body


def _opener() -> urllib.request.OpenerDirector:
    """HTTP and HTTPS and nothing more: no proxy (the token goes to the configured host only), no redirect handler
    (a redirect comes back as an error), no cookie jar."""
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(),
                    urllib.request.HTTPDefaultErrorHandler(), urllib.request.HTTPErrorProcessor(),
                    urllib.request.UnknownHandler()):
        opener.add_handler(handler)
    return opener


def _shown(url: str) -> str:
    """A URL fit to show a person: no user name or password and no query, either of which could carry a secret."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.rpartition("@")[2], parts.path, "", ""))


def _read(response: http.client.HTTPResponse, deadline: float, timeout: float) -> bytes:
    """The body, up to MAX_BYTES and within the deadline. `read1` makes at most one read on the socket, so a feed
    that sends a byte at a time can't outlast the timeout (the socket's own timeout is per read)."""
    length = response.headers.get("Content-Length", "")
    if length.isdigit() and int(length) > MAX_BYTES:
        raise ConnectorError("the feed sent more than 20 MB")
    chunks: list[bytes] = []
    size = 0
    try:
        while chunk := response.read1(CHUNK):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ConnectorError("the feed sent more than 20 MB")
            if time.monotonic() > deadline:
                raise ConnectorError(f"the feed was still sending after {timeout:g} s")
            chunks.append(chunk)
    except TimeoutError:
        raise ConnectorError(f"the feed was still sending after {timeout:g} s") from None
    return b"".join(chunks)


def _why(reason: object) -> str:
    return reason.strerror if isinstance(reason, OSError) and reason.strerror else str(reason)


def problems(exc: ValidationError) -> str:
    """The first three problems as `field.path: message`, then how many more; fewer than three when three wouldn't
    fit in a source row, so the count always shows."""
    found = [f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" if e["loc"] else e["msg"]
             for e in exc.errors()]
    shown = min(SHOWN_PROBLEMS, len(found))
    while True:
        more = len(found) - shown
        text = "; ".join(found[:shown]) + (f"; and {more} more" if more else "")
        if len(text) <= DETAIL_LIMIT or shown <= 1:
            return text
        shown -= 1


def parse(body: bytes) -> Snapshot:
    """The body as a Snapshot, or a ConnectorError that says what is wrong with it."""
    try:
        text = body.decode("utf-8-sig")  # -sig: a byte-order mark is fine
    except UnicodeDecodeError:
        raise ConnectorError(f"{NOT_JSON} (it isn't UTF-8 text)") from None
    if text.lstrip().startswith("<"):
        raise ConnectorError(f"{NOT_JSON}: a web page (a sign-in page, or the wrong address?)")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConnectorError(f"{NOT_JSON} (line {exc.lineno}, column {exc.colno}: {exc.msg})") from None
    except RecursionError:
        raise ConnectorError(f"{NOT_JSON} (it is nested too deeply to read)") from None
    if isinstance(payload, dict) and "contract_version" not in payload:
        # the contract defaults a missing version to 1; a feed must say it, so a future one can't pass for this one
        raise ConnectorError('the feed doesn\'t say which contract it speaks: add "contract_version": "1"')
    try:
        return Snapshot.model_validate(payload)
    except ValidationError as exc:
        for e in exc.errors():
            if e["loc"] == ("contract_version",) and e["type"] == "value_error":
                raise ConnectorError(str(e["ctx"]["error"])) from None  # the contract's own words
        raise ConnectorError(problems(exc)) from None


def keep(snapshot: Snapshot, source_id: str, label: str, now: datetime) -> Snapshot:
    """What kestrel keeps of a payload: every list and the benchmark, with the payload's own sources replaced by one
    row for this feed, whose last success is when the payload was made."""
    made = snapshot.generated_at
    if made - now > CLOCK_DRIFT:
        raise ConnectorError(f"the feed's generated_at is {_span(made - now)} ahead of this computer's clock: "
                             "check the clock and time zone where the feed is made")
    counts = [_count(len(snapshot.books), "book", "books"), _count(len(snapshot.strategies), "strategy", "strategies"),
              _count(len(snapshot.trades), "trade", "trades")]
    if snapshot.accounts:
        counts.insert(0, _count(len(snapshot.accounts), "account", "accounts"))
    source = Source(id=source_id, label=label, kind="feed", last_success=min(made, now), status="ok",
                    detail=" · ".join(counts))
    return snapshot.model_copy(update={"sources": [source]})


class FeedConnector:
    """Reads one feed: `url` (one GET) or `path` (one file). `token_env` names the environment variable that holds a
    bearer token for the url; it is read each time, so the token lives in no object."""

    def __init__(self, source_id: str, label: str, *, url: str | None = None, path: Path | None = None,
                 token_env: str | None = None, timeout: float = TIMEOUT) -> None:
        self.source_id = source_id
        self.label = label
        self.url = url
        self.path = path
        self.token_env = token_env
        self.timeout = timeout

    def snapshot(self, now: datetime) -> Snapshot:
        body = self._fetch(self.url) if self.url is not None else read_file(self.path)
        return keep(parse(body), self.source_id, self.label, now)

    def _token(self) -> str | None:
        if self.token_env is None:
            return None
        token = os.environ.get(self.token_env, "").strip()
        if not token:
            raise ConnectorError(f"set {self.token_env} in the environment (token_env)")
        if not all("!" <= c <= "~" for c in token):
            # http.client would refuse it with the token in its message; visible ASCII is what a bearer token is
            raise ConnectorError(f"the token in {self.token_env} has a character a header can't carry "
                                 "(a space or a line break?)")
        return token

    def _fetch(self, url: str) -> bytes:
        token = self._token()
        request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        if token:
            # unredirected: were a redirect ever followed, the token would stay behind
            request.add_unredirected_header("Authorization", f"Bearer {token}")
        deadline = time.monotonic() + self.timeout
        no_answer = f"the feed didn't answer within {self.timeout:g} s"
        try:
            with _opener().open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ConnectorError(f"the feed answered {response.status}")
                return _read(response, deadline, self.timeout)
        except urllib.error.HTTPError as exc:  # any answer outside 2xx, a redirect included
            location = exc.headers.get("Location")
            exc.close()
            if 300 <= exc.code < 400 and location:
                raise ConnectorError(f"the feed redirected to {_shown(urljoin(url, location))}; kestrel doesn't "
                                     "follow redirects (set url to the feed's own address)") from None
            raise ConnectorError(f"the feed answered {exc.code}") from None
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise ConnectorError(no_answer) from None
            raise ConnectorError(f"the feed couldn't be reached ({_why(exc.reason)})") from None
        except TimeoutError:
            raise ConnectorError(no_answer) from None
        except (http.client.HTTPException, OSError) as exc:
            raise ConnectorError(f"the feed couldn't be read ({exc})") from None
````


`src/kestrel/connectors/__init__.py`:

````python
"""Connectors turn a profile's sources into one Snapshot."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..contract import Snapshot, Source, merge
from ..profile import Profile, SourceCfg
from .base import DETAIL_LIMIT, Connector, ConnectorError, ConnectorUnavailable
from .demo import DemoConnector
from .fdc import FdcConnector
from .feed import TIMEOUT as FEED_TIMEOUT
from .feed import FeedConnector

__all__ = ["Connector", "ConnectorError", "ConnectorUnavailable", "build", "collect"]


def build(cfg: SourceCfg, profile: Profile) -> Connector:
    if cfg.kind == "demo":
        return DemoConnector(cfg.id, tz=profile.tz, seed=int(getattr(cfg, "seed", 340)))
    if cfg.kind == "fdc":
        path = getattr(cfg, "path", None)
        if not isinstance(path, str) or not path:
            raise ConnectorError("an fdc source needs a path to the warehouse, "
                                 'e.g. path = "../financial-data-collector/data/warehouse.db"')
        return FdcConnector(cfg.id, cfg.label or cfg.id, Path(path), categories=getattr(cfg, "categories", None),
                            benchmark=profile.benchmark)
    if cfg.kind == "feed":
        # the profile has already checked the shape: exactly one of url and path, the scheme, token_env, timeout
        path = getattr(cfg, "path", None)
        return FeedConnector(cfg.id, cfg.label or cfg.id, url=getattr(cfg, "url", None),
                             path=Path(path) if path is not None else None, token_env=getattr(cfg, "token_env", None),
                             timeout=float(getattr(cfg, "timeout", FEED_TIMEOUT)))
    raise ConnectorUnavailable(f"connector kind {cfg.kind!r} is not available in this version of kestrel")


def _with_staleness(sources: list[Source], cfg: SourceCfg, now: datetime) -> list[Source]:
    out = []
    for s in sources:
        old = s.last_success is not None and now - s.last_success > cfg.stale_delta
        out.append(s.model_copy(update={"status": "stale"}) if s.status == "ok" and old else s)
    return out


def collect(profile: Profile, now: datetime) -> Snapshot:
    """Ask every source for its snapshot. One broken source shows as an error; it never takes the page down."""
    parts: list[Snapshot] = []
    failed: list[Source] = []
    for cfg in profile.sources:
        try:
            part = build(cfg, profile).snapshot(now)
        except Exception as exc:  # noqa: BLE001 - any connector failure becomes a visible source error
            failed.append(Source(id=cfg.id, label=cfg.label or cfg.id, kind=cfg.kind, status="error",
                                 detail=str(exc)[:DETAIL_LIMIT]))
            continue
        parts.append(part.model_copy(update={"sources": _with_staleness(list(part.sources), cfg, now)}))
    snapshot = merge(parts, generated_at=now)
    return snapshot.model_copy(update={"sources": [*snapshot.sources, *failed]})
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `262 passed` (`test_feed_connector.py` 43); `All checks passed!`. The file takes about 3 s: its longest waits are the 0.3 s and 0.5 s timeouts.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/connectors/feed.py src/kestrel/connectors/__init__.py tests/feed_fixture.py tests/test_feed_connector.py
git commit -m "feat(feed): one GET with the token, no redirects or proxy, 20 MB and the timeout; registered" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 4: When two sources use the same id, the first one wins

**Files:**
- Modify (replace the whole file): `src/kestrel/connectors/__init__.py`
- Create: `tests/test_connectors.py`

**Interfaces:**
- Consumes: Tasks 2–3's connector and fixture (two feed files make two sources; `kestrel demo`'s output makes a copy of the demo).
- Produces:
  - `connectors._without_duplicates(parts) -> list[Snapshot]`: in profile order, a later part's account, book or strategy whose id an earlier part already has is dropped, with the account's holdings and account history; the book's book history, positions, trades, trade charts and runs; nothing more for a strategy (books keep pointing at the first one). A run with no book and every alert stay.
  - `connectors._noted(sources, ignored)`: the later part's first source row gains ` · ignored duplicate ids: a, b` (each id once, in order: accounts, books, strategies; at most five, then `, and N more`).
  - `collect()` merges the parts through `_without_duplicates`.

- [ ] **Step 1: Write the failing tests**

`tests/test_connectors.py`:

````python
"""collect() and ids that two sources share: the first source in the profile keeps its item."""

import datetime as dt

from feed_fixture import desk, feed_file

from kestrel.cli import main
from kestrel.connectors import collect
from kestrel.profile import DEMO_PROFILE, Profile, SourceCfg

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
DAY = {"date": "2026-09-25", "value": 100.0}


def with_account(payload: dict) -> dict:
    """The desk's payload plus a brokerage account with one holding and a day of history."""
    return {**payload,
            "accounts": [{"id": "brokerage", "name": "Brokerage", "category": "long_term", "value": 5000.0,
                          "as_of": "2026-09-25T20:00:00+00:00"}],
            "holdings": [{"account_id": "brokerage", "symbol": "VTI", "quantity": 10, "price": 300.0,
                          "value": 3000.0}],
            "account_history": [{"id": "brokerage", "points": [{"date": "2026-09-25", "value": 5000.0}]}]}


def household() -> dict:
    """A second fictional source that reuses the desk's account, book and strategy ids, and has its own too."""
    return desk(
        accounts=[{"id": "brokerage", "name": "Joint brokerage", "category": "long_term", "value": 9999.0,
                   "as_of": "2026-09-25T20:00:00+00:00"},
                  {"id": "hsa", "name": "HSA", "category": "long_term", "value": 1200.0,
                   "as_of": "2026-09-25T20:00:00+00:00"}],
        holdings=[{"account_id": "brokerage", "symbol": "BND", "quantity": 1, "price": 72.0, "value": 72.0},
                  {"account_id": "hsa", "symbol": "VXUS", "quantity": 2, "price": 70.0, "value": 140.0}],
        account_history=[{"id": "brokerage", "points": [DAY]}, {"id": "hsa", "points": [DAY]}],
        books=[{"id": "swing-real", "name": "Other swing", "money": "real", "strategy_id": "swing",
                "status": "paused", "started": "2025-01-02", "value": 1.0},
               {"id": "ibs-paper", "name": "IBS (paper)", "money": "paper", "strategy_id": "ibs",
                "status": "running", "started": "2026-02-02", "value": 3200.0}],
        book_history=[{"id": "swing-real", "points": [DAY]}, {"id": "ibs-paper", "points": [DAY]}],
        positions=[{"book_id": "swing-real", "symbol": "XOM", "quantity": 1, "entry_price": 110.0,
                    "last_price": 111.0, "opened": "2026-09-23"}],
        trades=[{"book_id": "swing-real", "symbol": "CVX", "opened": "2026-09-01", "closed": "2026-09-02",
                 "entry_price": 150.0, "exit_price": 151.0, "quantity": 1, "pnl": 1.0, "return_pct": 0.67},
                {"book_id": "ibs-paper", "symbol": "SPY", "opened": "2026-09-21", "closed": "2026-09-22",
                 "entry_price": 650.0, "exit_price": 653.0, "quantity": 2, "pnl": 6.0, "return_pct": 0.46}],
        trade_charts=[{"book_id": "swing-real", "symbol": "CVX", "opened": "2026-09-01",
                       "bars": [{"date": "2026-09-01", "open": 150.0, "high": 151.5, "low": 149.2, "close": 150.4}]}],
        strategies=[{"id": "swing", "name": "Someone else's swing"}, {"id": "ibs", "name": "Weak close"}],
        runs=[{"time": "2026-09-25T13:31:00+00:00", "label": "Other morning", "book_id": "swing-real",
               "status": "done"},
              {"time": "2026-09-25T19:56:00+00:00", "label": "Close entries", "book_id": "ibs-paper",
               "status": "done"},
              {"time": "2026-09-25T23:00:00+00:00", "label": "Backup", "status": "due"}],
        alerts=[{"level": "note", "title": "IBS book opened a trade"}],
    )


def profile_of(*paths) -> Profile:
    return Profile(sources=[SourceCfg(id=path.stem, kind="feed", label=path.stem.title(), path=str(path))
                            for path in paths])


def test_a_later_sources_duplicate_ids_are_dropped_with_everything_that_hangs_off_them(tmp_path):
    first = feed_file(tmp_path, with_account(desk()), "desk.json")
    later = feed_file(tmp_path, household(), "household.json")
    snap = collect(profile_of(first, later), NOW)
    assert [(a.id, a.name) for a in snap.accounts] == [("brokerage", "Brokerage"), ("hsa", "HSA")]
    assert [h.symbol for h in snap.holdings] == ["VTI", "VXUS"]
    assert [(s.id, s.points[0].value) for s in snap.account_history] == [("brokerage", 5000.0), ("hsa", 100.0)]
    assert [(b.id, b.name) for b in snap.books] == [("swing-real", "Swing"), ("swing-paper", "Swing (paper)"),
                                                   ("ibs-paper", "IBS (paper)")]
    assert [(s.id, s.points[-1].value) for s in snap.book_history] == [("swing-real", 2150.0), ("ibs-paper", 100.0)]
    assert [p.symbol for p in snap.positions] == ["KO"]
    assert [t.symbol for t in snap.trades] == ["PG", "JNJ", "SPY"]
    assert snap.trade_charts == []
    assert [(s.id, s.name) for s in snap.strategies] == [("swing", "Swing pullbacks"), ("ibs", "Weak close")]
    assert [r.label for r in snap.runs] == ["Evening run", "Close entries", "Backup"]  # a run with no book stays
    assert [a.title for a in snap.alerts] == ["KO is near its stop", "IBS book opened a trade"]
    assert {s.id: s.detail for s in snap.sources} == {
        "desk": "1 account · 2 books · 1 strategy · 2 trades",
        "household": "2 accounts · 2 books · 2 strategies · 2 trades · ignored duplicate ids: brokerage, swing-real, "
                     "swing",
    }


def test_profile_order_decides_which_source_is_first(tmp_path):
    desk_path = feed_file(tmp_path, with_account(desk()), "desk.json")
    household_path = feed_file(tmp_path, household(), "household.json")
    snap = collect(profile_of(household_path, desk_path), NOW)
    assert [(a.id, a.name) for a in snap.accounts] == [("brokerage", "Joint brokerage"), ("hsa", "HSA")]
    assert [h.symbol for h in snap.holdings] == ["BND", "VXUS"]
    assert [(b.id, b.name) for b in snap.books] == [("swing-real", "Other swing"), ("ibs-paper", "IBS (paper)"),
                                                   ("swing-paper", "Swing (paper)")]
    assert [p.symbol for p in snap.positions] == ["XOM"]
    assert [t.symbol for t in snap.trades] == ["CVX", "SPY", "JNJ"]
    assert [c.symbol for c in snap.trade_charts] == ["CVX"]
    assert [r.label for r in snap.runs] == ["Other morning", "Close entries", "Backup"]
    assert [s.name for s in snap.strategies] == ["Someone else's swing", "Weak close"]
    assert {s.id: s.detail for s in snap.sources}["desk"] == (
        "1 account · 2 books · 1 strategy · 2 trades · ignored duplicate ids: brokerage, swing-real, swing")


def test_the_demo_left_in_next_to_a_feed_of_the_same_data_counts_once(tmp_path, capsysbinary):
    main(["demo", "--now", NOW.isoformat()])
    path = tmp_path / "copy.json"
    path.write_bytes(capsysbinary.readouterr().out)
    demo = collect(DEMO_PROFILE, NOW)
    feed = SourceCfg(id="copy", kind="feed", label="Copy", path=str(path))
    snap = collect(Profile(sources=[*DEMO_PROFILE.sources, feed]), NOW)
    for field in ("accounts", "holdings", "account_history", "books", "book_history", "positions", "trades",
                  "trade_charts", "strategies"):
        assert getattr(snap, field) == getattr(demo, field), field
    assert len(snap.runs) == len(demo.runs) + 2  # the two runs that belong to no book
    assert snap.sources[-1].detail == ("4 accounts · 5 books · 4 strategies · 136 trades · ignored duplicate ids: "
                                       "roth, brokerage, trading, savings, rsi2-real, and 8 more")
    reversed_order = collect(Profile(sources=[feed, *DEMO_PROFILE.sources]), NOW)
    assert [(s.id, s.detail) for s in reversed_order.sources][:2] == [
        ("copy", "4 accounts · 5 books · 4 strategies · 136 trades"),
        ("demo-portfolio", "ignored duplicate ids: roth, brokerage, trading, savings, rsi2-real, and 8 more"),
    ]  # the note goes on the later source's first row
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_connectors.py`
Expected: `3 failed`: nothing is dropped yet, so the later source's duplicates arrive too (`AssertionError: assert [('brokerage'...` in the first two tests, and `AssertionError: accounts` in the demo test, where every list arrives twice).

- [ ] **Step 3: Implement (replace the whole file)**

`src/kestrel/connectors/__init__.py`:

````python
"""Connectors turn a profile's sources into one Snapshot."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..contract import Snapshot, Source, merge
from ..profile import Profile, SourceCfg
from .base import DETAIL_LIMIT, Connector, ConnectorError, ConnectorUnavailable
from .demo import DemoConnector
from .fdc import FdcConnector
from .feed import TIMEOUT as FEED_TIMEOUT
from .feed import FeedConnector

__all__ = ["Connector", "ConnectorError", "ConnectorUnavailable", "build", "collect"]


def build(cfg: SourceCfg, profile: Profile) -> Connector:
    if cfg.kind == "demo":
        return DemoConnector(cfg.id, tz=profile.tz, seed=int(getattr(cfg, "seed", 340)))
    if cfg.kind == "fdc":
        path = getattr(cfg, "path", None)
        if not isinstance(path, str) or not path:
            raise ConnectorError("an fdc source needs a path to the warehouse, "
                                 'e.g. path = "../financial-data-collector/data/warehouse.db"')
        return FdcConnector(cfg.id, cfg.label or cfg.id, Path(path), categories=getattr(cfg, "categories", None),
                            benchmark=profile.benchmark)
    if cfg.kind == "feed":
        # the profile has already checked the shape: exactly one of url and path, the scheme, token_env, timeout
        path = getattr(cfg, "path", None)
        return FeedConnector(cfg.id, cfg.label or cfg.id, url=getattr(cfg, "url", None),
                             path=Path(path) if path is not None else None, token_env=getattr(cfg, "token_env", None),
                             timeout=float(getattr(cfg, "timeout", FEED_TIMEOUT)))
    raise ConnectorUnavailable(f"connector kind {cfg.kind!r} is not available in this version of kestrel")


def _with_staleness(sources: list[Source], cfg: SourceCfg, now: datetime) -> list[Source]:
    out = []
    for s in sources:
        old = s.last_success is not None and now - s.last_success > cfg.stale_delta
        out.append(s.model_copy(update={"status": "stale"}) if s.status == "ok" and old else s)
    return out


def _noted(sources: list[Source], ignored: list[str]) -> list[Source]:
    """The part's first source row, its detail naming the ids it lost (at most five), then the rest unchanged."""
    if not sources:
        return sources
    names = ", ".join(ignored[:5]) + (f", and {len(ignored) - 5} more" if len(ignored) > 5 else "")
    first = sources[0]
    detail = " · ".join(text for text in (first.detail, f"ignored duplicate ids: {names}") if text)
    return [first.model_copy(update={"detail": detail}), *sources[1:]]


def _without_duplicates(parts: list[Snapshot]) -> list[Snapshot]:
    """When a later source uses an account, book or strategy id an earlier one already has, the earlier one's item
    stays and the later one's goes, with everything that hangs off it: an account's holdings and history; a book's
    history, positions, trades, trade charts and runs. Books keep pointing at the first strategy of their id."""
    seen_accounts: set[str] = set()
    seen_books: set[str] = set()
    seen_strategies: set[str] = set()
    out = []
    for part in parts:
        accounts = {a.id for a in part.accounts} & seen_accounts
        books = {b.id for b in part.books} & seen_books
        strategies = {s.id for s in part.strategies} & seen_strategies
        seen_accounts |= {a.id for a in part.accounts}
        seen_books |= {b.id for b in part.books}
        seen_strategies |= {s.id for s in part.strategies}
        if not (accounts or books or strategies):
            out.append(part)
            continue
        ignored = [*(a.id for a in part.accounts if a.id in accounts), *(b.id for b in part.books if b.id in books),
                   *(s.id for s in part.strategies if s.id in strategies)]
        out.append(part.model_copy(update={
            "accounts": [a for a in part.accounts if a.id not in accounts],
            "holdings": [h for h in part.holdings if h.account_id not in accounts],
            "account_history": [s for s in part.account_history if s.id not in accounts],
            "books": [b for b in part.books if b.id not in books],
            "book_history": [s for s in part.book_history if s.id not in books],
            "positions": [p for p in part.positions if p.book_id not in books],
            "trades": [t for t in part.trades if t.book_id not in books],
            "trade_charts": [c for c in part.trade_charts if c.book_id not in books],
            "runs": [r for r in part.runs if r.book_id not in books],
            "strategies": [s for s in part.strategies if s.id not in strategies],
            "sources": _noted(list(part.sources), list(dict.fromkeys(ignored))),  # an id named once, in order
        }))
    return out


def collect(profile: Profile, now: datetime) -> Snapshot:
    """Ask every source for its snapshot. One broken source shows as an error; it never takes the page down. When
    two sources use the same id, the one earlier in the profile wins (`_without_duplicates`)."""
    parts: list[Snapshot] = []
    failed: list[Source] = []
    for cfg in profile.sources:
        try:
            part = build(cfg, profile).snapshot(now)
        except Exception as exc:  # noqa: BLE001 - any connector failure becomes a visible source error
            failed.append(Source(id=cfg.id, label=cfg.label or cfg.id, kind=cfg.kind, status="error",
                                 detail=str(exc)[:DETAIL_LIMIT]))
            continue
        parts.append(part.model_copy(update={"sources": _with_staleness(list(part.sources), cfg, now)}))
    snapshot = merge(_without_duplicates(parts), generated_at=now)
    return snapshot.model_copy(update={"sources": [*snapshot.sources, *failed]})
````


- [ ] **Step 4: Run everything and watch it pass**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `265 passed` (`test_connectors.py` 3); `All checks passed!`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/connectors/__init__.py tests/test_connectors.py
git commit -m "feat(connectors): the first source wins an id two sources share; the later one says what it dropped" -m "$(cat <temp>/trailer.txt)"
```

---

### Task 5: The docs, and a run through the CLI

**Files:**
- Modify (replace the whole file): `docs/connectors.md`, `profile.example.toml`
- Modify (exact lines below): `README.md`, `AGENTS.md`, `docs/data-contract.md`, `docs/specs/2026-09-25-kestrel-design.md`, `docs/specs/2026-09-26-phase-4b-feed-design.md`

**Interfaces:** none (documentation). `tests/test_profile.py::test_the_committed_example_profile_loads` keeps passing: the `feed` block is commented out.

- [ ] **Step 1: Write the connector guide and the example profile**

`docs/connectors.md`:

````markdown
# Connectors

A connector reads one source and returns a Snapshot, the format in [`data-contract.md`](data-contract.md). kestrel
asks every source in your `profile.toml` each time a page loads. A source that can't be read shows as an error in the
sidebar's Sources block, and the rest of the page still works. Every connector only reads: none of them changes its
source's data.

| `kind` | Reads | Since |
|---|---|---|
| `demo` | nothing: a fictional year for "Alex" | Phase 2; the default when there is no `profile.toml` |
| `fdc` | [financial-data-collector](https://github.com/Dimas-100/financial-data-collector)'s SQLite warehouse | Phase 4a |
| `feed` | any system that serves the contract as JSON, at a URL or in a file (your trading desk) | Phase 4b |
| `rails` | a trading-rails install: paper books, the run log, backtests | later |

`kestrel check` tries every source and prints what it found; `kestrel serve --demo` and `kestrel check --demo` show
the demo whatever `profile.toml` says. When two sources use the same id, the one earlier in the profile wins (see
[the last section](#when-two-sources-use-the-same-id)).

## `demo`

```toml
[[sources]]
id = "demo"
kind = "demo"
label = "Demo data"
```

Accounts, holdings, books, trades and runs for a believable year, with the dates moving so the last day is today.

## `fdc`: financial-data-collector

```toml
[[sources]]
id = "portfolio"
kind = "fdc"
label = "Portfolio"
path = "../financial-data-collector/data/warehouse.db"   # relative to this profile's folder
stale_after = "36h"

[sources.categories]          # optional: account id or exact label = long_term | trading | cash | other
"brokerage-2" = "trading"
```

- **`path`** is the warehouse file. A relative path is relative to the folder `profile.toml` is in, not to wherever
  you start kestrel.
- **Read-only.** The file is opened with `mode=ro` and `query_only` on top, and closed straight after each read. A
  sync running at the same time is fine: kestrel reads what the collector last committed. Reading a warehouse in WAL
  mode (the collector's mode) lets SQLite create its standard `-wal` and `-shm` coordination files beside it when
  they are missing; kestrel never changes the warehouse's data.
- **Cached.** kestrel keeps what it read, keyed to the warehouse's and its `-wal` file's size and modification time,
  so a sync shows up at once (and within a minute at most, for a same-size write that leaves both looking unchanged).
- **Needs** schema version 3 or later: the tables `accounts`, `transactions`, `prices`, `sync_runs`, `holdings_daily`
  and `cash_daily`, and the views `positions_latest` and `account_values_daily`.

### Accounts

| kestrel shows | from the warehouse |
|---|---|
| id | the account's label as a slug: `Alex Roth IRA` is `alex-roth-ira`, `Épargne` is `epargne`; a label with no letters or digits is `account`. Two labels that make the same slug get `-2`, `-3` in the order the collector first saw them. The id is the account's address: `/accounts/alex-roth-ira`. |
| name | the label |
| institution | `fidelity` is Fidelity, `webull` Webull, anything else title-cased; `unknown` is left out |
| type | `roth_ira` is Roth IRA, `traditional_ira` Traditional IRA, `401k` 401(k), `brokerage` Brokerage, `crypto` Crypto (and the other retirement types the same way); anything else title-cased |
| category | set in `[sources.categories]` by id or label (an id wins over a label), else from the type: retirement accounts, an HSA, a pension and `brokerage` are long-term; `checking`, `savings`, `cash` and `money_market` are cash; anything else, crypto included, is other |

Trading money is whatever you file under `trading`. Until a real trading book has a history of its own, Home's
"Trading vs your index money" draws the trading accounts.

A category that isn't one of the four is a profile error: `kestrel check` stops before reading any source (see
Troubleshooting). A `categories` entry that matches no account is noted on the source's line.

### Values, history and money moved

- **Value and cash:** the newer of the broker's last snapshot (`account_values_daily`) and the last replayed day
  (`holdings_daily` plus `cash_daily`). When both are from the same day, the snapshot wins. A value is as of that
  day's US close.
- **History:** each account's holdings plus its cash, per day, ending on the account's value: the snapshot's total
  replaces the replayed day it shares, a newer snapshot adds its day, and an account with only a snapshot has a
  one-day history. So the Accounts total, the growth's "Now" and each account's chart agree.
- **History before the first snapshot** is reconstructed by the collector from the account's transactions. If those
  don't reach back to when the account was opened, the jump at the first snapshot shows up as market growth in "All".
- **Money moved in and out,** from `transactions`, so deposits never count as growth:
  - a `contribution` counts as its signed amount (a negative one is a reversal),
  - a `withdrawal` is always money out,
  - a `transfer` keeps its sign; a transfer of shares with no cash amount moves no money,
  - money moved on a day without history (a Saturday deposit) counts on the next day that has one, a newer
    snapshot's day included; money moved after the last day is left for the next sync.
- **Holdings:** the broker's latest snapshot of each account (`positions_latest`), each with the day it was
  reported. A position with no market value is left out and counted in the source's detail; one with no price is
  priced at its value over its quantity. When the replayed history is newer than that snapshot, the holdings are
  older than the value, and the account page says so under its holdings table.

### Benchmark

When the warehouse has prices for your profile's `[benchmark]` symbol, kestrel draws it from their adjusted closes
(dividends included, as they are in the accounts), starting at the last close on or before the first day of your
accounts' history. Pick a symbol the collector already prices, such as an index fund you hold. Otherwise there is no
benchmark line, and the source's detail says `no SPY prices in the warehouse`.

### Freshness

The source's last success is when the collector last finished its `derive` step without an error (the step that
rebuilds the daily history), else any step that finished without one. After `stale_after` it turns amber. A
warehouse that has never finished a step shows as stale.

### Troubleshooting

Run `kestrel check`. Under the source's line it lists each account as `id  category  name`, never a balance.

| The source's line says | What to do |
|---|---|
| `no warehouse at …` | Check `path`: it is relative to the folder `profile.toml` is in. |
| `… is not a financial-data-collector warehouse` | The file isn't a collector warehouse (or is empty): check `path`. |
| `this warehouse is at schema version 2 …` or `this warehouse is missing holdings_daily …` | Update financial-data-collector and run `fdc sync`. |
| `the warehouse couldn't be read: database is locked` | Another program held the file for more than five seconds. Refresh once it is done. |
| `no account matches categories 'brokerage-9'` | Use an id from the account lines, or the exact label. |
| `no SPY prices in the warehouse` | Set `[benchmark] symbol` to something the collector prices, or add it to the collector. |

An unknown category is a profile error, not a line under the source: `kestrel check` stops before reading any source
with `profile problem: <path>: sources.0: Value error, unknown category 'trade' for 'Brokerage' (use long_term,
trading, cash or other)` and exits with status 2. Use one of those four in `[sources.categories]`.

## `feed`: any system that serves the contract

```toml
[[sources]]
id = "desk"
kind = "feed"
label = "Trading desk"
url = "http://127.0.0.1:8000/api/feed"   # or: path = "../desk/feed.json" (relative to this profile's folder)
token_env = "KESTREL_DESK_TOKEN"          # optional, with a url: the NAME of the variable that holds a bearer token
timeout = 5                               # optional: seconds, 1 to 60 (default 5)
stale_after = "15m"
```

A feed is one JSON document in the contract's own format, a Snapshot ([`data-contract.md`](data-contract.md)), served
at a URL or saved in a file. It is how a system of your own, such as a trading desk, shows its books, strategies,
trades, runs and alerts (and its accounts, if it has any) without kestrel knowing anything else about it.

- **Exactly one of `url` and `path`.** A `url` starts with `http://` or `https://`. A relative `path` is relative to
  the folder `profile.toml` is in.
- **`token_env`** names an environment variable, in capitals; the token itself never goes in the profile. kestrel
  reads it each time it asks the feed and sends it as `Authorization: Bearer …` to the configured URL and nowhere
  else: it doesn't follow redirects and doesn't use a proxy, and it never prints or logs the token. A URL can't carry
  a user name or password (`http://name:secret@…`); use `token_env`.
- **Read-only, and asked each time a page loads.** One GET, with `Accept: application/json` and no cookies, or one
  file read. Nothing is cached.

A feed's shape is checked when the profile loads: a source with both `url` and `path` (or neither), another scheme,
a user name in the URL, a `token_env` that isn't a variable's name (or that goes with a `path`), or a `timeout`
outside 1 to 60 stops `kestrel check` with `profile problem: …` and exit status 2, before any source is read.

### What is checked

In this order; the first check that fails is the source's error, and the rest of kestrel keeps working.

1. **The token**, when `token_env` is set: the variable must be set and not empty, and hold only visible characters.
2. **The answer:** status 200 only; the whole answer inside `timeout`, not just its first byte; at most 20 MB. A
   file must exist and be at most 20 MB.
3. **JSON:** UTF-8 text (a byte-order mark is fine), and not a web page.
4. **The contract version:** the payload must say `"contract_version"`, and its major version must be 1. A newer
   minor version (`"1.4"`) loads; fields this kestrel doesn't know are ignored.
5. **The Snapshot:** every field the contract names. The first three problems are listed as `field.path: message`,
   then how many more (fewer than three when three wouldn't fit on the source's line).
6. **The time:** `generated_at` no more than five minutes ahead of this computer's clock. A payload up to five
   minutes ahead reads as made now.

### What kestrel keeps

Every list the payload carries, and its benchmark. The payload's own `sources` are replaced by one row for the feed:
its label, `kind = "feed"`, a last success of the payload's `generated_at`, and a detail like
`2 books · 1 strategy · 61 trades` (the accounts first, when there are any). So a system that keeps serving an old
payload turns amber after `stale_after`. The payload's alerts pass through; the contract already limits their links
to pages inside kestrel.

### Build a payload

`kestrel demo` prints a complete, valid payload (the demo's fictional year), and `kestrel schema` prints the contract
as JSON Schema. The smallest payload kestrel accepts is:

```json
{"contract_version": "1", "generated_at": "2026-09-25T21:05:00+00:00"}
```

Serve it at any address on this computer, or save it to a file, and point a `feed` source at it. Set
`generated_at` each time the payload is rebuilt: it is how kestrel knows the feed is fresh.

### Troubleshooting

| The source's line says | What to do |
|---|---|
| `set KESTREL_DESK_TOKEN in the environment (token_env)` | Set the variable where kestrel runs, then restart `kestrel serve`. |
| `the token in KESTREL_DESK_TOKEN has a character a header can't carry …` | The variable holds more than the token: a space or a line break inside it. |
| `the feed couldn't be reached (…)` or `the feed couldn't be read (…)` | Is the system that serves the feed running? Check `url`. |
| `the feed answered 401` (or `403`, `404`, `503`, …) | The feed's own answer: check the token, the address, or the system itself. |
| `the feed redirected to …; kestrel doesn't follow redirects` | Set `url` to the feed's own address; a redirect to a sign-in page usually means the feed wants a token (`token_env`). |
| `the feed didn't answer within 5 s` or `the feed was still sending after 5 s` | Make the feed faster, or raise `timeout` (up to 60). |
| `the feed sent more than 20 MB` or `the feed file is more than 20 MB` | Send less: a feed carries what the pages show, not raw history. |
| `no feed file at …` | Check `path`: it is relative to the folder `profile.toml` is in. |
| `the feed sent something that isn't JSON: a web page …` | The address answers with a page, often a sign-in page: point `url` at the feed itself. |
| `the feed sent something that isn't JSON (…)` | Compare the feed with `kestrel demo`'s output. |
| `the feed doesn't say which contract it speaks …` | Add `"contract_version": "1"` to the payload. |
| `unsupported contract version '2'; this kestrel reads major version 1` | The feed speaks a newer contract: update kestrel. |
| `books.0.money: Input should be 'real' or 'paper'; …; and 2 more` | The payload doesn't match the contract: fix those fields in the feed. |
| `the feed's generated_at is 4 hours ahead of this computer's clock …` | Check the clock, and the time zone offset, where the payload is made. |

## When two sources use the same id

Two sources can name the same thing: two warehouses that each have an account called "Brokerage", or the demo left in
next to a real feed. The source earlier in `profile.toml` keeps its item, and the later source's goes, with
everything that hangs off it:

| A later source's duplicate | Goes with it |
|---|---|
| account id | its holdings and its account history |
| book id | its book history, positions, trades, trade charts and runs |
| strategy id | nothing else: books keep pointing at the first source's strategy |

The later source's line in the sidebar then ends with `ignored duplicate ids: brokerage, rsi2` (the ids only, at
most five, then `and N more`), on its first row when it has several. To show the later source's item instead, move
that source up in the profile. `kestrel check` reads each source on its own, so it lists every source's accounts and
never shows this note.

## `rails`

Later: a trading-rails install's paper books, run log and backtests. Until then a source of this kind shows as an
error that says it isn't available in this version.
````


`profile.example.toml`:

````toml
# kestrel profile. Copy this file to profile.toml (gitignored) and make it yours.
# Never put a key or password in here: a source names the environment variable that holds it.

[you]
name = "Alex"

[app]
name = "kestrel"
accent = "rufous"          # rufous | slate | mono
theme = "system"           # system | dark | light
gain_loss = "green-red"    # green-red | blue-orange
density = "comfortable"    # comfortable | compact
currency = "USD"
timezone = "America/New_York"

[benchmark]                # the index your money is compared with; an fdc source draws it from its own prices
symbol = "SPY"
label = "S&P 500"

# Where your data comes from. The demo source works out of the box; see docs/connectors.md for every kind.
[[sources]]
id = "demo"
kind = "demo"
label = "Demo data"

# Your accounts, from financial-data-collector's warehouse (read-only). Replace the demo source above with this one:
#
# [[sources]]
# id = "portfolio"
# kind = "fdc"
# label = "Portfolio"
# path = "../financial-data-collector/data/warehouse.db"   # relative to this file's folder
# stale_after = "36h"
#
# [sources.categories]               # optional: account id or exact label = long_term | trading | cash | other
# "brokerage-2" = "trading"
#
# A system of your own (a trading desk) that serves the kestrel contract as JSON: its books, strategies, trades and
# runs. Add it next to your other sources; `kestrel demo` prints an example payload:
#
# [[sources]]
# id = "desk"
# kind = "feed"
# label = "Trading desk"
# url = "http://127.0.0.1:8000/api/feed"   # or: path = "../desk/feed.json" (relative to this file's folder)
# token_env = "KESTREL_DESK_TOKEN"          # optional: the NAME of the environment variable holding a bearer token
# timeout = 5                               # optional: seconds, 1 to 60
# stale_after = "15m"
#
# When two sources use the same id, the one higher up in this file wins. A trading-rails source comes later.
````


- [ ] **Step 2: Update the docs**

In `README.md`, replace:

````text
> **Status: Phase 4a of 5 — Home, Accounts and the Strategies pages run.** Accounts read your own data from
> financial-data-collector, or the demo; Books, Backtests, Activity and Settings arrive in later phases. See the [design spec](docs/specs/2026-09-25-kestrel-design.md).
````

with:

````text
> **Status: Phase 4b of 5 — Home, Accounts and the Strategies pages run.** Accounts read your own data from
> financial-data-collector, books and strategies from any system that serves the data contract (a `feed`), or the
> demo; Books, Backtests, Activity and Settings arrive in later phases. See the [design spec](docs/specs/2026-09-25-kestrel-design.md).
````

In `README.md`, replace:

````text
3. Run `kestrel check`: the source should read `ok`, with every account and its category listed under it (never a
   balance). Then `kestrel serve`; `kestrel serve --demo` still shows the demo.
````

with:

````text
3. Run `kestrel check`: the source should read `ok`, with every account and its category listed under it (never a
   balance). Then `kestrel serve`; `kestrel serve --demo` still shows the demo.
4. A system of your own, such as a trading desk, plugs in through a `feed` source: serve the
   [data contract](docs/data-contract.md) as JSON at a local address (`kestrel demo` prints an example) and add the
   commented `feed` block.
````

In `AGENTS.md`, replace:

````text
**Status:** Phase 4a of 5 — the skeleton, the Strategies pages and the Accounts pages, with the `fdc` connector reading
financial-data-collector's warehouse. The trading desk's `feed` and `rails` are Phase 4b; Books is Phase 3b.
````

with:

````text
**Status:** Phase 4b of 5 — the skeleton, the Strategies pages and the Accounts pages, with the `fdc` connector reading
financial-data-collector's warehouse and the `feed` connector reading any system that serves the contract (a trading
desk). Books is Phase 3b; `rails` comes later.
````

In `docs/data-contract.md`, replace:

````text
Every source kestrel reads speaks one format: a **Snapshot**. The built-in connectors produce one, and so can any
system of your own — serve a Snapshot as JSON and the `feed` connector (Phase 4) plugs it in without a line of your
system's code entering this repo.
````

with:

````text
Every source kestrel reads speaks one format: a **Snapshot**. The built-in connectors produce one, and so can any
system of your own — serve a Snapshot as JSON and the `feed` connector plugs it in without a line of your system's
code entering this repo ([how](connectors.md#feed-any-system-that-serves-the-contract)).
````

In `docs/data-contract.md`, replace:

````text
- `contract_version` is `"1"`. Within a major version changes are **additive only**; kestrel ignores fields it does
  not know, and refuses an unknown major version (the source shows as `error` with the reason).
````

with:

````text
- `contract_version` is `"1"`, and a feed must say so. Within a major version changes are **additive only**; kestrel
  ignores fields it does not know, and refuses an unknown major version (the source shows as `error` with the reason).
````

In `docs/data-contract.md`, replace:

````text
- A strategy, book or account `id` appears directly in a URL path (`/strategies/{id}`); an id must not contain `/`.
````

with:

````text
- A strategy, book or account `id` appears directly in a URL path (`/strategies/{id}`); an id must not contain `/`.
  When two sources use the same id, the one earlier in the profile keeps it and the later one's item is dropped
  ([connectors.md](connectors.md#when-two-sources-use-the-same-id)).
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
- **Status:** design approved. Phases 0 (mockups), 1 (this repo, spec, design system, hygiene test), 2 (the skeleton), 3a (the Strategies pages) and 4a (Accounts and the `fdc` connector) are done; Phase 4b (the trading desk's `feed` and `rails`) is next, then 3b (Books).
````

with:

````text
- **Status:** design approved. Phases 0 (mockups), 1 (this repo, spec, design system, hygiene test), 2 (the skeleton), 3a (the Strategies pages), 4a (Accounts and the `fdc` connector) and 4b (the `feed` connector) are done; Phase 3b (Books) is next, and `rails` later.
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
    connectors/             base protocol · demo (Phase 2) · fdc (Phase 4a) · rails · feed (Phase 4b)   (§8)
````

with:

````text
    connectors/             base protocol · demo (Phase 2) · fdc (Phase 4a) · feed (Phase 4b) · rails (later)   (§8)
````

In `docs/specs/2026-09-25-kestrel-design.md`, replace:

````text
| 4 | Accounts; `fdc`, `rails`, `feed` connectors | 4a done (Accounts, `fdc`); 4b (`feed`, `rails`) next |
````

with:

````text
| 4 | Accounts; `fdc`, `rails`, `feed` connectors | 4a done (Accounts, `fdc`); 4b done (`feed`); `rails` later |
````

In `docs/specs/2026-09-26-phase-4b-feed-design.md`, replace:

````text
- **Status:** design decided autonomously (owner: "proceed with the next phase"); plan next.
````

with:

````text
- **Status:** built (plan: [`../plans/2026-09-26-phase-4b-feed.md`](../plans/2026-09-26-phase-4b-feed.md)).
````


- [ ] **Step 3: Run everything from a clean start**

Run: `.venv/Scripts/python -m pytest && .venv/Scripts/python -m ruff check .`
Expected: `265 passed`; `All checks passed!`.

- [ ] **Step 4: A run through the CLI (the check the tests don't make from the outside)**

With `KESTREL_DESK_TOKEN` not set in the shell (`unset KESTREL_DESK_TOKEN`):

```bash
.venv/Scripts/kestrel demo > <temp>/desk.json
printf '[[sources]]\nid = "desk"\nkind = "feed"\nlabel = "Trading desk"\npath = "desk.json"\nstale_after = "15m"\n' > <temp>/feed-profile.toml
.venv/Scripts/kestrel check --profile <temp>/feed-profile.toml; echo "exit $?"
printf '[[sources]]\nid = "desk"\nkind = "feed"\nlabel = "Trading desk"\nurl = "http://127.0.0.1:9/api/feed"\ntoken_env = "KESTREL_DESK_TOKEN"\n' > <temp>/url-profile.toml
.venv/Scripts/kestrel check --profile <temp>/url-profile.toml; echo "exit $?"
printf '[[sources]]\nid = "desk"\nkind = "feed"\nurl = "http://alex:hunter2@127.0.0.1:8000/api/feed"\n' > <temp>/bad-profile.toml
.venv/Scripts/kestrel check --profile <temp>/bad-profile.toml; echo "exit $?"
```
Expected (each path prints as you typed it, and `0 minutes ago` reads `1 minute ago` if a minute has passed):

```text
profile: <temp>/feed-profile.toml - hello, there
  ok     Trading desk     feed             0 minutes ago  4 accounts · 5 books · 4 strategies · 136 trades
         roth             long_term        Roth IRA
         brokerage        long_term        Brokerage
         trading          trading          Trading account
         savings          cash             High-yield savings
exit 0
profile: <temp>/url-profile.toml - hello, there
  error  Trading desk     feed             never  set KESTREL_DESK_TOKEN in the environment (token_env)
exit 1
profile problem: <temp>/bad-profile.toml: sources.0: Value error, a feed url can't carry a user name or password: put the token in an environment variable and name it in token_env
exit 2
```

The password in the third profile appears nowhere in the output.

- [ ] **Step 5: Commit, push, and watch CI**

```bash
git add docs/connectors.md profile.example.toml README.md AGENTS.md docs/data-contract.md docs/specs/2026-09-25-kestrel-design.md docs/specs/2026-09-26-phase-4b-feed-design.md
git commit -m "docs: the feed connector and the duplicate-id rule; Phase 4b is done" -m "$(cat <temp>/trailer.txt)"
git push
gh run watch --exit-status
```
Expected: all three CI jobs green (`python` 3.11 and 3.12, `python-windows`, `web`).

---

## Done when

- A `profile.toml` with a `feed` source reads a URL or a file; `kestrel check` shows its row, `ok` with its book, strategy and trade counts, or `error` with a message a person can act on, and never the token.
- A redirect is refused and the token never follows it; no proxy is used; a feed that is slow, trickling, huge, a web page or malformed is a red row, and the rest still arrives.
- Two sources with the same id show the first source's item, and the later source's line in the sidebar names what it dropped.
- 265 Python tests pass locally and in CI (including Windows); ruff is clean; the generated files are current.
- The parent spec's Phase 4 row reads "4b done (`feed`)"; `rails` comes later.

## After the build: the owner's setup (local only, never committed)

The private system's own feed is specified and built in its own repo (spec §6: out of scope here). Once it serves, add its `feed` block to `kestrel/profile.toml` (gitignored) after the `fdc` source: `url` at its local address, `token_env` naming the variable if it asks for a token, and `stale_after` a little longer than it takes to rebuild its payload. Set that variable where kestrel starts, run `kestrel check`, and confirm the row reads `ok` with the expected counts. If the demo source is still in the profile, remove it: wherever its ids clash with the desk's, the demo's would win.

## Self-review

- **Spec coverage:** §2.1 profile → Task 1 (exactly one of `url` and `path`, the scheme, `timeout` 1–60, a relative `path` from the profile's folder, `token_env` as a name) and Task 3 (the missing-variable error, the header, the configured URL only); §2.2 HTTP → Task 3 (one GET with the timeout and `Accept: application/json`, redirects refused naming the target, "the feed answered 503", 20 MB); file → Task 2 (20 MB, UTF-8 with a BOM, "no feed file at <path>"); parse and validate → Task 2 (JSON first, another major version with the contract's message, the first three problems and "and N more"); what kestrel keeps → Task 2 (every list and the benchmark, one source row with `kind`, `last_success` and the detail, alerts passed through) and Task 3 (through `collect()`, where the row goes stale after `stale_after`); nothing cached → every snapshot reads again (Tasks 2–3); §2.3 safety → Task 3 (GET only, no cookies, the token only in the header and never in a message or a log, a red row for a broken feed while the demo still arrives), Task 2 (alert links limited by the contract); §3 duplicates → Task 4 (accounts, books and strategies with their dependents, the note with at most five ids, profile order); §4 docs → Task 5; §5 testing → every listed case, in Tasks 1–4, and the hygiene and read-only guards pass unchanged (`urllib` is the standard library); §6 out of scope → nothing here pushes, streams, edits or places, and the private system's side is not in this repo.
- **Interpretations** (decided in the prototype, listed for the reviewer):
  - **20 MB** is 20 × 1024 × 1024 bytes. A `Content-Length` over it is refused before reading; a body without one is read in 64 KB chunks and stopped one byte past it; a file is read to one byte past it.
  - **The timeout covers the whole answer.** `urllib`'s timeout is per socket read, so the connector also keeps a deadline, checked after each chunk: a trickle ends at the timeout (at worst one blocked read later, so under twice the timeout). Two messages tell the cases apart: "didn't answer within" (nothing came back) and "was still sending after".
  - **No proxy.** "To the configured URL only" rules out a proxy from the environment or the system's settings, which `urllib` would otherwise use (even for 127.0.0.1 when `NO_PROXY` is unset): the opener has no proxy handler, so a feed on another host must be reachable directly.
  - **A feed must declare `contract_version`.** The contract defaults a missing version to `"1"`; the parent spec (§7) says every feed declares it, so a payload without one is refused (`the feed doesn't say which contract it speaks: add "contract_version": "1"`). A newer minor (`"1.4"`) loads.
  - **Fewer than three problems when three don't fit.** `collect()` keeps 200 characters of an error (now `DETAIL_LIMIT` in `base.py`), so the list drops to two, or one, problems and "and N more" always shows. Pydantic's messages are shown as they are; a problem of the whole payload (a JSON list, say) has no field path.
  - **"The feed sent something that isn't JSON" says why:** where the parser stopped (`(line 1, column 2: Expecting property name enclosed in double quotes)`), or that the body isn't UTF-8 text or is nested too deeply to read; and a body whose first non-space character is `<` is named as a web page instead.
  - **A payload from the future.** The spec says `last_success` is the payload's `generated_at`; up to five minutes ahead it is this computer's time instead (so the row never reads a negative age), and further ahead the feed is a red row naming how far ahead.
  - **Secrets in the wrong place are profile errors that don't repeat the value:** a user name or password in the `url`; a `token_env` that isn't a variable's name in capitals (lower-case names, legal on macOS and Linux, are refused too, because a pasted token is almost never all capitals); a `token_env` with a `path` (a file is read without a token). At read time, a token with a space or line break inside is refused without being shown, and a redirect's target is shown without user info or query.
  - **The detail** always counts books, strategies and trades, and puts the accounts first when there are any: `kestrel demo`'s payload reads `4 accounts · 5 books · 4 strategies · 136 trades`.
  - **Every status but 200 is an error,** a 204 included; a 3xx with a `Location` is the redirect message, one without is `the feed answered 302`.
  - **Duplicates:** a run that names a dropped book goes with it (the spec's table lists history, positions, trades and trade charts; otherwise the run would show under the first source's book of that id); a run with no book and every alert stay. The note goes on the later source's first row (the demo has four). An id that is both a book and a strategy is named once. Duplicates inside one source aren't touched: the spec is about sources, and `fdc` already makes unique ids.
  - **`kestrel check` reads one source at a time** (Phase 4a), so it neither drops a duplicate nor shows the note; the sidebar does, and `docs/connectors.md` says so.
  - **The unavailable-kind examples** in `tests/test_cli.py` and `tests/test_demo_connector.py` move from a bare `feed` to `rails`, which is still unavailable.
- **Placeholders:** none; every step has its file blocks or its exact command and output.
- **Names and types:** `FeedConnector`'s keyword arguments (`url`, `path`, `token_env`, `timeout`) are the profile's keys, read by `build()` (Task 3); the fixture's `desk()`, `feed_file()`, `FeedServer` and replies keep their names through Tasks 2–4; `DETAIL_LIMIT` (Task 2) is what `problems()` fits under and what `collect()` cuts at (Task 3).

## After the task reviews

The file blocks above show the code as first built, in the Task 1–4 reviews; a later hardening round (brief:
`.superpowers/sdd/2026-09-26-phase-4b-feed/hardening-brief.md`) found five things worth fixing before this is truly
done, each test-first:

- **H1:** the `timeout` bounded only the body (`_read`'s own deadline); a peer that trickled bytes without ever
  finishing its headers could defeat it and block for far longer. `_fetch` now fetches with `http.client` directly
  (never a redirect, never a proxy — the same guarantees as before, stronger) plus a watchdog thread that shuts the
  socket down if the headers aren't in within `timeout`; the body keeps its original, unchanged deadline.
- **H2:** `json.loads` accepts `NaN`, `Infinity` and `-Infinity` (not valid JSON), and so did pydantic's floats;
  `parse()` now passes `parse_constant` to refuse them by name.
- **H3:** `_noted`'s duplicate-ids note always named five ids without checking the row's length; `_fit_note` now
  shrinks the name count (five, then fewer, then none) and, only as a last resort, the source's own detail, the
  same shrink-until-it-fits idea as `feed.problems()`.
- **H4:** two items of the same id within one source (not just across sources) passed through untouched;
  `_dedupe_within` now keeps the first and drops the later item itself, before the cross-source check runs.
- **H5:** a malformed bracketed URL (`http://[::1/feed`) made `urlsplit` raise its own "Invalid IPv6 URL" past the
  feed shape check instead of the profile's friendly message; that check now catches it.
