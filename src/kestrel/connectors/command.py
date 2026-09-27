"""A feed's command: a program kestrel runs itself, whose standard output is the feed's JSON. This is the one place
kestrel starts a program (tests/test_read_only_guard.py holds it to that), and it only ever starts the one the
profile names, with the owner's own permissions, like a shell alias would.

The program runs straight from its argv list, never through a shell: with no standard input, a copy of kestrel's
environment, and on Windows no console window. Its standard output is read up to a limit, and its standard error is
kept only for the last line of an error message. A program that runs too long, or prints too much, is killed and
reaped before the error is raised.

Known limit: only the program itself is killed. A program that starts programs of its own (a shell script that runs
python, say) can leave them running after a timeout, and if they hold its output open, kestrel stops waiting for
them after a short grace period and leaves them be.

One run serves every request for `refresh` (`cached_run`): a page asks several routes at once, and a desk's export
can take seconds.
"""

from __future__ import annotations

import ntpath
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import IO

from .base import ConnectorError

MAX_OUTPUT = 20 * 1024 * 1024  # 20 MB, as for any feed
DEFAULT_TIMEOUT = 30.0  # seconds, unless the profile says otherwise (1 to 120)
DEFAULT_REFRESH = timedelta(minutes=1)
CHUNK = 64 * 1024
ERROR_TAIL = 64 * 1024  # how much of the end of standard error is kept: only its last line is ever shown
LAST_LINE = 160  # characters of that line in a message
GRACE = 1.0  # seconds to wait for a killed program to be reaped and its pipes to close
# no console window flashing up on Windows each time a page loads
_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
_PATHEXT = ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC"  # Windows' own list, when PATHEXT isn't set


def _name(program: str) -> str:
    """The program's file name alone, whichever slash its path uses: its folder can be a machine path."""
    return ntpath.basename(program) or "the program"


def _on_path(name: str) -> str | None:
    """The program `name` in the first PATH folder that holds it (on Windows, the name as it is when it already ends
    in one of PATHEXT's extensions, else with each of them in turn), or None. Only absolute PATH folders are searched,
    never the current one: Windows' own lookup, and shutil.which there, try the folder kestrel was started from
    first, and an empty or relative PATH entry means that folder anywhere, so a program planted there would run in
    place of the one PATH names."""
    windows = sys.platform == "win32"
    names = [name]
    if windows:
        extensions = [ext for ext in os.environ.get("PATHEXT", _PATHEXT).split(os.pathsep) if ext]
        if not name.lower().endswith(tuple(ext.lower() for ext in extensions)):
            names = [name + ext for ext in extensions]
    for folder in os.environ.get("PATH", os.defpath).split(os.pathsep):
        if windows:
            folder = folder.strip().strip('"')
        # on Windows an absolute folder has a drive or a share: \desk alone hangs off whichever drive is current
        if not os.path.isabs(folder) or (windows and not ntpath.splitdrive(folder)[0]):
            continue
        for candidate in names:
            path = os.path.join(folder, candidate)
            if os.path.isfile(path) and (windows or os.access(path, os.X_OK)):
                return path
    return None


def _size(limit: int) -> str:
    mb = 1024 * 1024
    return f"{limit // mb} MB" if limit % mb == 0 else f"{limit:,} bytes"


def _last_line(err: bytes) -> str:
    """The last non-empty line of standard error, printable characters only, at most LAST_LINE characters."""
    for line in reversed(err.decode("utf-8", errors="replace").splitlines()):
        line = "".join(c for c in line if c.isprintable()).strip()
        if line:
            return line if len(line) <= LAST_LINE else line[:LAST_LINE - 1] + "…"
    return ""


class _Reader(threading.Thread):
    """Reads one pipe to its end on its own thread, so neither pipe can fill up and stall the program: standard
    output up to `limit` + 1 bytes (and then stops: `over` is set), standard error to the end, keeping only its last
    `limit` bytes. The pipe is closed here, by the one thread that reads it."""

    def __init__(self, pipe: IO[bytes], limit: int, *, keep_tail: bool = False) -> None:
        super().__init__(daemon=True)
        self.pipe = pipe
        self.limit = limit
        self.keep_tail = keep_tail
        self.data = bytearray()
        self.over = False

    def run(self) -> None:
        try:
            while True:
                want = CHUNK if self.keep_tail else min(CHUNK, self.limit + 1 - len(self.data))
                chunk = self.pipe.read(want)
                if not chunk:
                    return
                self.data += chunk
                if self.keep_tail:
                    del self.data[:-self.limit]
                elif len(self.data) > self.limit:
                    self.over = True
                    return
        except (OSError, ValueError):
            return  # the pipe broke or was closed: what came is what there is
        finally:
            try:
                self.pipe.close()
            except OSError:
                pass


def _stop(process: subprocess.Popen) -> None:
    """Kill the program and reap it (never waiting more than GRACE)."""
    try:
        process.kill()
    except OSError:
        pass  # it has just ended on its own
    try:
        process.wait(GRACE)
    except subprocess.TimeoutExpired:
        pass  # a program the system can't end at once is left to it; Popen reaps it later


def run(argv: list[str], *, cwd: Path | None, timeout: float, limit: int = MAX_OUTPUT) -> bytes:
    """Run argv (never through a shell), stdin closed, no console window on Windows. Returns stdout.

    A bare program name (no slash) is looked up on PATH only (`_on_path`), never in the current folder.

    Raises ConnectorError worded for a person: 'no such program: <name>', 'the command took longer than <t> s',
    'the command failed (exit <n>): <last stderr line, <=160 chars>', 'the command printed more than 20 MB'.
    On timeout or overflow the child is killed before returning. kestrel's own words never hold the arguments or the
    environment (either can carry a secret); the stderr line is the program's own, and may.
    """
    deadline = time.monotonic() + timeout
    too_long = f"the command took longer than {timeout:g} s"
    program = argv[0]
    if cwd is not None:
        try:
            exists = cwd.is_dir()
        except OSError as exc:  # a folder kestrel may not look into, say
            why = exc.strerror or type(exc).__name__
            raise ConnectorError(f"the command's folder can't be read: {cwd} ({why})") from None
        if not exists:
            raise ConnectorError(f"the command's folder doesn't exist: {cwd}")
    if ntpath.basename(program) == program:  # a bare name, such as python: looked up on PATH
        found = _on_path(program)
        if found is None:
            raise ConnectorError(f"no such program: {program}")
        program = found
    if sys.platform == "win32" and program.lower().rstrip(". ").endswith((".bat", ".cmd")):
        # Windows runs a batch file through cmd.exe, which reads the arguments again, its own way: a shell (and
        # drops a name's trailing dots and spaces, so "desk.cmd." is one too)
        raise ConnectorError(f"{_name(program)} is a batch file, which Windows runs through cmd.exe: "
                             "name the program it runs instead")
    try:
        process = subprocess.Popen([program, *argv[1:]], cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0, creationflags=_FLAGS)
    except FileNotFoundError:
        raise ConnectorError(f"no such program: {_name(program)}") from None
    except (OSError, ValueError) as exc:  # not a program (a folder, a script Windows can't run), or no permission
        why = exc.strerror if isinstance(exc, OSError) and exc.strerror else type(exc).__name__
        # Windows' words for some of these hold a %1 where the program's name goes
        why = why.replace("%1", _name(program))
        raise ConnectorError(f"the command couldn't start {_name(program)} ({why})") from None
    out = _Reader(process.stdout, limit)
    err = _Reader(process.stderr, ERROR_TAIL, keep_tail=True)
    try:
        out.start()  # in here, so a thread that can't start still stops the program
        err.start()
        out.join(max(0.0, deadline - time.monotonic()))  # ends at the end of the output, or just past the limit
        if out.over or out.is_alive():
            raise ConnectorError(f"the command printed more than {_size(limit)}" if out.over else too_long)
        try:
            code = process.wait(max(0.0, deadline - time.monotonic()))  # its output has ended; has the program?
        except subprocess.TimeoutExpired:
            raise ConnectorError(too_long) from None
    except BaseException:
        _stop(process)  # too long, too much, or anything else (even Ctrl+C): the program doesn't outlive the request
        raise
    finally:
        until = time.monotonic() + GRACE  # one grace period for both pipes, so a request never waits long here
        for reader in (out, err):
            if reader.ident is None:  # never started: nothing else will close its pipe
                reader.pipe.close()
            else:
                reader.join(max(0.0, until - time.monotonic()))
    if code != 0:
        line = _last_line(bytes(err.data))
        raise ConnectorError(f"the command failed (exit {code})" + (f": {line}" if line else ""))
    return bytes(out.data)


@dataclass
class _Result:
    lock: threading.Lock = field(default_factory=threading.Lock)  # held while the command runs
    made: float | None = None  # when the last run ended, on the `now` clock
    output: bytes | None = None
    error: str | None = None


_results: dict[tuple, _Result] = {}
_results_lock = threading.Lock()


def cached_run(key: tuple, argv: list[str], *, cwd: Path | None, timeout: float, refresh: timedelta,
               now: Callable[[], float] = time.monotonic) -> bytes:
    """One run per key at a time; a result (bytes or the ConnectorError) is reused for `refresh`; callers arriving
    while a run is in flight wait for it. Module-level cache guarded by a lock per key.

    The key is the source's id, its argv and its folder: the same program run elsewhere is another run."""
    with _results_lock:
        result = _results.setdefault(key, _Result())
    with result.lock:
        if result.made is None or now() - result.made >= refresh.total_seconds():
            try:
                result.output, result.error = run(argv, cwd=cwd, timeout=timeout), None
            except ConnectorError as exc:
                result.output, result.error = None, str(exc)
            result.made = now()
        output, error = result.output, result.error
    if error is not None:
        raise ConnectorError(error)  # a new one each time: one exception raised in many threads would share a traceback
    return output
