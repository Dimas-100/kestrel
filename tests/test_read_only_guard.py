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


# kestrel starts one kind of program: a feed's command, which the owner names in the profile. Only the runner may
# start it, and never through a shell (where a stray character in the profile could become a second command).
RUNNER = SRC / "connectors" / "command.py"
PROGRAM_MODULES = {"subprocess", "pty"}
# os.system, os.popen, os.spawn*, os.exec*, os.posix_spawn*, os.startfile, os.fork* and asyncio's
# create_subprocess_*, by exact name (a prefix would catch sqlite's cursor.execute)
PROGRAM_CALLS = {"system", "popen", "startfile", "fork", "forkpty", "posix_spawn", "posix_spawnp",
                 "create_subprocess_exec", "create_subprocess_shell",
                 *(verb + tail for verb in ("exec", "spawn")
                   for tail in ("l", "le", "lp", "lpe", "v", "ve", "vp", "vpe"))}


def program_starts(tree: ast.AST) -> list[str]:
    """Every place in `tree` that could start a program, by line: `subprocess` or `pty` imported or named, or one
    of PROGRAM_CALLS, called on anything or imported by name."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, f"import {a.name}") for a in node.names if a.name.split(".")[0] in PROGRAM_MODULES]
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in PROGRAM_MODULES:
                found.append((node.lineno, f"from {node.module} import"))
            found += [(node.lineno, f"import {a.name}") for a in node.names if a.name in PROGRAM_CALLS]
        elif isinstance(node, ast.Attribute) and node.attr in PROGRAM_CALLS:
            found.append((node.lineno, f".{node.attr}"))
        elif isinstance(node, ast.Name) and node.id in PROGRAM_MODULES:
            found.append((node.lineno, node.id))
    return [f"{line}: {what}" for line, what in sorted(found)]


def shell_calls(tree: ast.AST) -> list[str]:
    """Every call in `tree` that passes `shell=` anything but a plain False."""
    return [f"{node.lineno}: shell=" for node in ast.walk(tree) if isinstance(node, ast.Call)
            for kw in node.keywords
            if kw.arg == "shell" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False)]


def test_only_the_command_runner_starts_programs():
    assert RUNNER.exists()
    offenders = []
    for path in modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        where = path.relative_to(SRC).as_posix()
        if path != RUNNER:
            offenders += [f"{where}:{found}" for found in program_starts(tree)]
        offenders += [f"{where}:{found}" for found in shell_calls(tree)]  # the runner included
    assert not offenders, offenders


def test_the_program_guard_catches_what_it_should():
    planted = ast.parse("\n".join([
        "import subprocess",                      # 1
        "from os import execv",                   # 2
        "from subprocess import run",             # 3
        "subprocess.run(['x'], shell=True)",      # 4
        "os.system('x')",                         # 5
        "os.popen('x')",                          # 6
        "os.spawnl(0, 'x')",                      # 7
        "os.execvp('x', [])",                     # 8
        "os.posix_spawn('x', [], {})",            # 9
        "os.startfile('x')",                      # 10
        "asyncio.create_subprocess_shell('x')",   # 11
        "run(['x'], shell=flag)",                 # 12
        "cursor.execute('select 1')",             # 13: not a program
    ]))
    assert program_starts(planted) == [
        "1: import subprocess", "2: import execv", "3: from subprocess import", "4: subprocess", "5: .system",
        "6: .popen", "7: .spawnl", "8: .execvp", "9: .posix_spawn", "10: .startfile", "11: .create_subprocess_shell"]
    assert shell_calls(planted) == ["4: shell=", "12: shell="]
    assert not shell_calls(ast.parse("subprocess.run(['x'], shell=False)"))
