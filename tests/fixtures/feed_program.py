"""A stand-in for a desk's feed program, for tests/test_command_feed.py. The tests run it with their own interpreter
(`sys.executable`), never through a shell:

    feed_program.py MODE [ARGUMENTS]

    ok                      print the desk's payload (feed_fixture.desk()) as JSON
    fail                    write "boom" and "last line" to standard error, then exit 2
    fail-long               write a 500-character line to standard error, then exit 3
    fail-quiet              exit 4 without a word
    sleep                   sleep 10 s, then print the payload
    linger                  print the payload and close standard output, then sleep 10 s
    flood                   print 21 MB
    bytes N                 print exactly N bytes
    noisy                   write 5 MB to standard error, then print the payload
    count FILE [SECONDS]    append a line to FILE, wait SECONDS (default 0), then print the payload
    cwd                     print the folder it runs in

Every name and number in the payload is made up.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

MB = 1024 * 1024


def payload() -> bytes:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/, for feed_fixture
    from feed_fixture import desk

    return json.dumps(desk()).encode("utf-8")


def main(mode: str, *args: str) -> int:
    out, err = sys.stdout.buffer, sys.stderr.buffer
    if mode == "ok":
        out.write(payload())
    elif mode == "fail":
        err.write(b"boom\nlast line\n")
        return 2
    elif mode == "fail-long":
        err.write(b"starting\n" + b"x" * 500 + b"\n\n")
        return 3
    elif mode == "fail-quiet":
        return 4
    elif mode == "sleep":
        time.sleep(10)
        out.write(payload())
    elif mode == "linger":
        out.write(payload())
        out.flush()
        os.close(1)  # standard output ends here; the program goes on
        time.sleep(10)
    elif mode == "flood":
        block = b"x" * MB
        for _ in range(21):
            out.write(block)
    elif mode == "bytes":
        out.write(b"x" * int(args[0]))
    elif mode == "noisy":
        block = b"e" * MB
        for _ in range(5):
            err.write(block)
        err.flush()
        out.write(payload())
    elif mode == "count":
        with open(args[0], "a", encoding="utf-8") as f:
            f.write("ran\n")
        time.sleep(float(args[1]) if len(args) > 1 else 0)
        out.write(payload())
    elif mode == "cwd":
        out.write(os.getcwd().encode("utf-8"))
    else:
        err.write(f"unknown mode {mode}\n".encode())
        return 64
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
