"""A feed that is a command kestrel runs itself: the runner's errors, its limits, and the cache that lets one run
serve every request for `refresh`."""

import datetime as dt
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from feed_fixture import MADE

from kestrel.connectors import build, collect
from kestrel.connectors import command as command_module
from kestrel.connectors.base import ConnectorError
from kestrel.connectors.command import DEFAULT_REFRESH, DEFAULT_TIMEOUT, MAX_OUTPUT, cached_run, run
from kestrel.connectors.feed import FeedConnector
from kestrel.profile import Profile, SourceCfg, load_profile

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)
PROGRAM = str(Path(__file__).resolve().parent / "fixtures" / "feed_program.py")


def argv(*args: str) -> list[str]:
    return [sys.executable, PROGRAM, *args]


@pytest.fixture(autouse=True)
def fresh_cache():
    command_module._results.clear()
    yield
    command_module._results.clear()


@pytest.fixture
def started(monkeypatch):
    """Every process the runner starts, with the options it was started with."""
    seen: list[tuple[subprocess.Popen, dict]] = []

    class Spy(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            seen.append((self, kwargs))

    monkeypatch.setattr(command_module.subprocess, "Popen", Spy)
    return seen


def failure(args: list[str], **options) -> str:
    options.setdefault("cwd", Path.cwd())
    options.setdefault("timeout", 20)
    with pytest.raises(ConnectorError) as error:
        run(args, **options)
    return str(error.value)


def desk_feed(tmp_path: Path, *args: str, refresh: dt.timedelta = DEFAULT_REFRESH) -> FeedConnector:
    return FeedConnector("desk", "Trading desk", command=argv(*args), cwd=tmp_path, refresh=refresh)


def runs(count_file: Path) -> int:
    return len(count_file.read_text(encoding="utf-8").splitlines()) if count_file.exists() else 0


# --- the runner -------------------------------------------------------------------------------------------------


def test_the_defaults():
    assert MAX_OUTPUT == 20 * 1024 * 1024
    assert DEFAULT_TIMEOUT == 30.0
    assert DEFAULT_REFRESH == dt.timedelta(minutes=1)


def test_a_command_that_prints_the_payload_is_a_feed(tmp_path):
    snap = desk_feed(tmp_path, "ok").snapshot(NOW)
    assert [s.model_dump() for s in snap.sources] == [{
        "id": "desk", "label": "Trading desk", "kind": "feed", "last_success": dt.datetime.fromisoformat(MADE),
        "status": "ok", "detail": "2 books · 1 strategy · 2 trades",
    }]
    assert [b.id for b in snap.books] == ["swing-real", "swing-paper"]


def test_the_program_runs_directly_with_no_input_and_no_window(tmp_path, started):
    run(argv("ok"), cwd=tmp_path, timeout=20)
    (process, options), = started
    assert process.args == argv("ok")  # the list itself: never one string for a shell to read
    assert options.get("shell", False) is False
    assert options["stdin"] == subprocess.DEVNULL
    assert options["cwd"] == tmp_path
    if sys.platform == "win32":
        assert options["creationflags"] & subprocess.CREATE_NO_WINDOW
    assert process.returncode == 0


def test_the_program_runs_in_its_folder(tmp_path):
    assert Path(run(argv("cwd"), cwd=tmp_path, timeout=20).decode("utf-8")) == tmp_path


def test_a_failing_command_shows_its_exit_code_and_the_last_line_it_wrote_to_standard_error():
    assert failure(argv("fail")) == "the command failed (exit 2): last line"


def test_the_last_line_of_standard_error_is_cut_to_160_characters():
    message = failure(argv("fail-long"))
    assert message.startswith("the command failed (exit 3): xxx")
    assert len(message.split(": ", 1)[1]) == 160


def test_a_failing_command_that_says_nothing_shows_its_exit_code():
    assert failure(argv("fail-quiet")) == "the command failed (exit 4)"


def test_no_message_repeats_the_arguments_or_the_programs_folder(tmp_path):
    secret = "--token=s3cret-4f9a"
    for message in (failure(argv("fail", secret)), failure([str(tmp_path / "desk" / "export.exe"), secret])):
        assert "s3cret" not in message and str(tmp_path) not in message and PROGRAM not in message


def test_a_command_that_runs_too_long_is_killed_and_named(started):
    began = time.monotonic()
    assert failure(argv("sleep"), timeout=1) == "the command took longer than 1 s"
    assert time.monotonic() - began < 3
    (process, _), = started
    assert process.returncode is not None and process.returncode != 0  # killed, and reaped


def test_a_command_that_closes_its_output_but_keeps_running_is_killed_too(started):
    began = time.monotonic()
    assert failure(argv("linger"), timeout=1.5) == "the command took longer than 1.5 s"
    assert time.monotonic() - began < 3.5
    (process, _), = started
    assert process.returncode is not None


def test_a_missing_program_is_named():
    assert failure(["kestrel-no-such-program-4f2a"]) == "no such program: kestrel-no-such-program-4f2a"


def test_a_missing_program_path_is_named_by_its_file_name_only(tmp_path):
    assert failure([str(tmp_path / "desk" / "export.exe"), "--now"]) == "no such program: export.exe"


def test_a_bare_program_name_is_looked_up_on_path(tmp_path, monkeypatch, started):
    monkeypatch.setenv("PATH", str(Path(sys.executable).parent))
    assert run([Path(sys.executable).name, PROGRAM, "ok"], cwd=tmp_path, timeout=20).startswith(b"{")
    (process, _), = started
    assert os.path.normcase(process.args[0]) == os.path.normcase(sys.executable)  # the file PATH led to, in full


@pytest.mark.skipif(sys.platform != "win32", reason="PATHEXT lookup only applies on Windows")
def test_an_empty_pathext_still_finds_a_program_by_the_default_extensions(monkeypatch, started, tmp_path):
    # PATHEXT="" is a set-but-empty value (some stripped-down shells and CI images): .get("PATHEXT", default) would
    # return "" as-is, leaving no extension to try and so no bare name ever found — a regression this guards
    monkeypatch.setenv("PATH", str(Path(sys.executable).parent))
    monkeypatch.setenv("PATHEXT", "")
    bare = Path(sys.executable).stem  # "python", with no .exe of its own
    assert command_module._on_path(bare) is not None
    assert run([bare, PROGRAM, "ok"], cwd=tmp_path, timeout=20).startswith(b"{")
    (process, _), = started
    assert os.path.normcase(process.args[0]) == os.path.normcase(sys.executable)


def test_a_bare_name_is_never_taken_from_the_folder_kestrel_started_in(tmp_path, monkeypatch, started):
    # Windows' own lookup (and Python's shutil.which there) tries the current folder before PATH, and an empty or
    # relative PATH entry means the current folder anywhere: a program planted where kestrel was started would run
    name = Path(sys.executable).name
    planted = tmp_path / "planted"
    planted.mkdir()
    for file in (name, "kestrel-planted-4f2a", "kestrel-planted-4f2a.exe"):
        (planted / file).write_bytes(b"not a program")
        (planted / file).chmod(0o755)
    monkeypatch.chdir(planted)
    monkeypatch.setenv("PATH", os.pathsep.join(["", ".", "planted", str(Path(sys.executable).parent)]))
    assert run([name, PROGRAM, "ok"], cwd=tmp_path, timeout=20).startswith(b"{")
    (process, _), = started
    assert os.path.normcase(process.args[0]) == os.path.normcase(sys.executable)  # PATH's, not the planted one
    assert failure(["kestrel-planted-4f2a"]) == "no such program: kestrel-planted-4f2a"
    assert len(started) == 1


def test_a_folder_that_cant_be_read_is_named_and_that_is_reused_too(tmp_path):
    looked: list[bool] = []

    class Locked(type(tmp_path)):
        def is_dir(self) -> bool:
            looked.append(True)
            raise PermissionError(13, "Permission denied")

    message = failure(argv("ok"), cwd=Locked(tmp_path))
    assert message == f"the command's folder can't be read: {tmp_path} (Permission denied)"
    feed = FeedConnector("desk", "Trading desk", command=argv("ok"), cwd=Locked(tmp_path))
    for _ in range(2):
        with pytest.raises(ConnectorError, match="the command's folder can't be read"):
            feed.snapshot(NOW)
    assert len(looked) == 2  # once for run() above, once for both snapshots


def test_a_program_the_system_cant_run_is_named_without_windows_placeholder(tmp_path):
    program = tmp_path / "desk.exe"
    program.write_bytes(b"not a program")
    program.chmod(0o755)
    message = failure([str(program)])
    assert message.startswith("the command couldn't start desk.exe (") and "%1" not in message
    if sys.platform == "win32":  # Windows' own words carry a %1 where the program's name goes
        assert message.startswith("the command couldn't start desk.exe (This version of desk.exe is not compatible")


def test_the_program_is_stopped_even_when_its_output_cant_be_read(tmp_path, monkeypatch, started):
    def broken(self) -> None:
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(command_module._Reader, "start", broken)
    with pytest.raises(RuntimeError, match="can't start new thread"):
        run(argv("sleep"), cwd=tmp_path, timeout=20)
    (process, _), = started
    assert process.returncode is not None  # killed and reaped, not left sleeping


@pytest.mark.skipif(sys.platform != "win32", reason="only Windows runs a batch file through cmd.exe")
def test_a_batch_file_is_refused_since_windows_runs_it_through_a_shell(tmp_path, monkeypatch, started):
    (tmp_path / "deskfeed.cmd").write_text("@echo {}\n", encoding="utf-8")
    message = "deskfeed.cmd is a batch file, which Windows runs through cmd.exe: name the program it runs instead"
    assert failure([str(tmp_path / "deskfeed.cmd")]) == message
    monkeypatch.setenv("PATH", str(tmp_path))
    assert failure(["deskfeed"]).lower() == message.lower()  # found on PATH by its extension (PATHEXT's .CMD)
    assert "is a batch file" in failure([str(tmp_path / "deskfeed.cmd. ")])  # Windows drops the trailing dot and space
    assert not started


def test_a_missing_folder_is_named(tmp_path):
    assert failure(argv("ok"), cwd=tmp_path / "gone").startswith("the command's folder doesn't exist")


def test_a_command_that_floods_its_output_is_killed_at_20_mb(started):
    began = time.monotonic()
    assert failure(argv("flood")) == "the command printed more than 20 MB"
    assert time.monotonic() - began < 10
    (process, _), = started
    assert process.returncode is not None


def test_exactly_the_limit_is_read_and_one_byte_more_is_refused(tmp_path):
    assert run(argv("bytes", "5000"), cwd=tmp_path, timeout=20, limit=5000) == b"x" * 5000
    assert failure(argv("bytes", "5001"), limit=5000) == "the command printed more than 5,000 bytes"


def test_a_lot_of_standard_error_never_blocks_the_program(tmp_path):
    began = time.monotonic()
    assert run(argv("noisy"), cwd=tmp_path, timeout=20).startswith(b'{"contract_version"')
    assert time.monotonic() - began < 10


def test_what_the_command_prints_goes_through_the_feeds_checks(tmp_path):
    with pytest.raises(ConnectorError, match="the feed sent something that isn't JSON"):
        desk_feed(tmp_path, "bytes", "10").snapshot(NOW)


# --- reuse --------------------------------------------------------------------------------------------------------


def test_two_snapshots_within_refresh_run_the_program_once(tmp_path):
    counted = tmp_path / "count.txt"
    feed = desk_feed(tmp_path, "count", str(counted))
    first, second = feed.snapshot(NOW), feed.snapshot(NOW)
    assert runs(counted) == 1 and first == second


def test_after_refresh_the_program_runs_again(tmp_path):
    counted = tmp_path / "count.txt"
    clock = [1000.0]
    options = {"cwd": tmp_path, "timeout": 20, "refresh": dt.timedelta(seconds=60), "now": lambda: clock[0]}
    key = ("desk", tuple(argv("count", str(counted))))
    cached_run(key, argv("count", str(counted)), **options)
    clock[0] += 59.9
    cached_run(key, argv("count", str(counted)), **options)
    assert runs(counted) == 1
    clock[0] += 0.1
    cached_run(key, argv("count", str(counted)), **options)
    assert runs(counted) == 2


def test_five_requests_at_once_share_one_run(tmp_path):
    counted = tmp_path / "count.txt"
    feed = desk_feed(tmp_path, "count", str(counted), "0.5")  # still running when the others arrive
    start = threading.Barrier(5)
    results: list = []

    def request() -> None:
        start.wait()
        results.append(feed.snapshot(NOW))

    threads = [threading.Thread(target=request) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert runs(counted) == 1
    assert len(results) == 5 and all(r == results[0] for r in results)


def test_an_error_is_reused_within_refresh_too(tmp_path, started):
    feed = desk_feed(tmp_path, "fail")
    for _ in range(3):
        with pytest.raises(ConnectorError, match=r"the command failed \(exit 2\): last line"):
            feed.snapshot(NOW)
    assert len(started) == 1


def test_an_unexpected_failure_isnt_kept_and_frees_the_source_for_the_next_request(tmp_path, monkeypatch):
    calls: list[int] = []
    real = command_module.run

    def hiccup(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("the machine hiccupped")
        return real(*args, **kwargs)

    monkeypatch.setattr(command_module, "run", hiccup)
    feed = desk_feed(tmp_path, "ok")
    with pytest.raises(RuntimeError, match="hiccupped"):
        feed.snapshot(NOW)
    assert not any(result.lock.locked() for result in command_module._results.values())  # never a stuck source
    assert feed.snapshot(NOW).sources[0].status == "ok"
    assert len(calls) == 2  # the second request ran it again: only a ConnectorError is kept


def test_a_changed_command_never_reuses_the_old_result(tmp_path):
    counted = tmp_path / "count.txt"
    desk_feed(tmp_path, "count", str(counted)).snapshot(NOW)
    desk_feed(tmp_path, "count", str(counted), "0").snapshot(NOW)  # the same source id, other arguments
    assert runs(counted) == 2


def test_the_same_command_in_another_folder_is_another_run(tmp_path):
    counted = tmp_path / "count.txt"
    for folder in ("a", "b"):
        (tmp_path / folder).mkdir()
        FeedConnector("desk", "Trading desk", command=argv("count", str(counted)), cwd=tmp_path / folder).snapshot(NOW)
    assert runs(counted) == 2


def test_two_sources_running_the_same_command_each_run_it(tmp_path):
    counted = tmp_path / "count.txt"
    command = argv("count", str(counted))
    for source_id in ("desk", "night"):
        FeedConnector(source_id, source_id, command=command, cwd=tmp_path).snapshot(NOW)
    assert runs(counted) == 2


# --- through the profile ------------------------------------------------------------------------------------------


def test_a_command_source_is_built_with_its_options_and_defaults(tmp_path):
    profile = Profile(sources=[
        SourceCfg(id="desk", kind="feed", command=argv("ok"), cwd=str(tmp_path), timeout=90, refresh="30s"),
        SourceCfg(id="night", kind="feed", command=argv("ok")),
    ])
    desk, night = (build(cfg, profile) for cfg in profile.sources)
    assert (desk.command, desk.cwd, desk.timeout, desk.refresh) == (
        argv("ok"), tmp_path, 90.0, dt.timedelta(seconds=30))
    assert (night.timeout, night.refresh) == (DEFAULT_TIMEOUT, DEFAULT_REFRESH)


def test_a_command_in_a_profile_runs_in_the_profiles_folder_through_collect(tmp_path, monkeypatch):
    home = tmp_path / "kestrel"
    home.mkdir()
    counted = tmp_path / "count.txt"
    program = Path(PROGRAM).as_posix()
    python = Path(sys.executable).as_posix()
    (home / "profile.toml").write_text(
        '[[sources]]\nid = "desk"\nkind = "feed"\nlabel = "Trading desk"\nstale_after = "15m"\n'
        f'command = ["{python}", "{program}", "count", "{counted.as_posix()}"]\n'
        '[[sources]]\nid = "broken"\nkind = "feed"\nlabel = "Broken desk"\n'
        f'command = ["{python}", "{program}", "fail"]\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)  # anywhere but the profile's folder
    profile, _ = load_profile(home / "profile.toml")
    assert build(profile.sources[0], profile).cwd == home.resolve()
    snap = collect(profile, NOW)
    rows = {s.id: (s.kind, s.status, s.detail) for s in snap.sources}
    assert rows == {"desk": ("feed", "ok", "2 books · 1 strategy · 2 trades"),
                    "broken": ("feed", "error", "the command failed (exit 2): last line")}
    later = collect(profile, NOW + dt.timedelta(minutes=20))  # the payload is 23 minutes old by then
    assert {s.id: s.status for s in later.sources}["desk"] == "stale"
    assert runs(counted) == 1  # both collects inside one refresh
