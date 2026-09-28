import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from kestrel.profile import DEMO_PROFILE, Profile, ProfileError, SourceCfg, load_profile, parse_duration, source_config

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


@pytest.mark.parametrize("lines", ["", 'url = "http://127.0.0.1:8000/api/feed"\npath = "feed.json"\n',
                                   'url = "http://127.0.0.1:8000/api/feed"\ncommand = ["python", "-m", "desk.feed"]\n',
                                   'path = "feed.json"\ncommand = ["python", "-m", "desk.feed"]\n'],
                         ids=["neither", "url and path", "url and command", "path and command"])
def test_a_feed_source_needs_exactly_one_of_url_path_and_command(tmp_path, lines):
    with pytest.raises(ProfileError, match=r"sources\.0: Value error, a feed source needs exactly one of url, path "
                                           "and command"):
        load_profile(write(tmp_path, FEED + lines))


@pytest.mark.parametrize("url", ["ftp://desk.example.com/feed", "file:///srv/feed.json", "127.0.0.1:8000/api/feed",
                                 "http://", 8000])
def test_a_feed_url_must_be_http_or_https(tmp_path, url):
    value = f'"{url}"' if isinstance(url, str) else url
    with pytest.raises(ProfileError, match="a feed url must start with http:// or https:// and name a host"):
        load_profile(write(tmp_path, FEED + f"url = {value}\n"))


def test_a_malformed_bracketed_url_gets_the_friendly_message(tmp_path):
    with pytest.raises(ProfileError) as error:
        load_profile(write(tmp_path, FEED + 'url = "http://[::1/feed"\n'))
    assert "a feed url must start with http:// or https:// and name a host" in str(error.value)
    assert "[::1" not in str(error.value)  # the malformed url text is never echoed back


@pytest.mark.parametrize("url", ["http://127.0.0.1:99999/api/feed", "http://127.0.0.1:k3y/api/feed",
                                 "http://127.0.0.1:0/api/feed"], ids=["out of range", "not a number", "zero"])
def test_a_feed_urls_port_is_a_number_from_1_to_65535(tmp_path, url):
    with pytest.raises(ProfileError) as error:
        load_profile(write(tmp_path, FEED + f'url = "{url}"\n'))
    assert "a feed url must start with http:// or https:// and name a host" in str(error.value)
    shown = str(error.value).replace(str(tmp_path), "")  # the message, less the profile's own path
    assert "k3y" not in shown and "99999" not in shown  # the url is never echoed back


# written as TOML escapes (\t, \n, \u0007), they reach the profile as a tab, a line break and a control character
@pytest.mark.parametrize("url", [r"http://127.0.0.1:8000/api feed?key=s3cret", r"http://127.0.0.1:8000/api\tfeed?key=s3cret",
                                 r"http://127.0.0.1:8000/api/feed?key=s3cret\n",
                                 r"http://127.0.0.1:8000/api\u0007feed?key=s3cret"],
                         ids=["space", "tab", "line break", "control character"])
def test_a_feed_url_cant_hold_spaces_or_control_characters(tmp_path, url):
    # http.client would refuse a space later, quoting the path and query (where a secret can hide) in the row
    with pytest.raises(ProfileError) as error:
        load_profile(write(tmp_path, FEED + f'url = "{url}"\n'))
    assert "a feed url can't contain spaces or control characters" in str(error.value)
    shown = str(error.value).replace(str(tmp_path), "")  # the message, less the profile's own path
    assert "s3cret" not in shown and "api" not in shown


@pytest.mark.parametrize("url", ["http://desk.example.com/api/feed", "http://192.168.1.20:8000/api/feed"])
def test_a_token_goes_only_over_https_or_to_this_computer(tmp_path, url):
    token = 'token_env = "KESTREL_DESK_TOKEN"\n'
    with pytest.raises(ProfileError, match="a token goes only over https, or to this computer"):
        load_profile(write(tmp_path, FEED + f'url = "{url}"\n' + token))
    for fine in ("http://127.0.0.1:8000/api/feed", "http://localhost:8000/api/feed", "http://[::1]:8000/api/feed",
                 "https://desk.example.com/api/feed"):
        profile, _ = load_profile(write(tmp_path, FEED + f'url = "{fine}"\n' + token))
        assert getattr(profile.sources[0], "token_env") == "KESTREL_DESK_TOKEN"
    load_profile(write(tmp_path, FEED + f'url = "{url}"\n'))  # without a token nothing secret goes: fine


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
    # the profile's own path is left out of the search: pytest's temp folder (pytest-3842) can hold the "42"
    assert not name or str(name) not in str(error.value).replace(str(tmp_path), "")


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


def test_durations_can_be_seconds_too():
    assert parse_duration("30s") == timedelta(seconds=30)
    with pytest.raises(ValueError, match=r"use a number and s, m, h or d"):
        parse_duration("30 sec")


COMMAND = 'command = ["python", "-m", "desk.feed"]\n'


def test_a_feed_source_can_be_a_command_with_its_options(tmp_path):
    profile, _ = load_profile(write(tmp_path, FEED + COMMAND + 'cwd = "../desk"\ntimeout = 120\nrefresh = "30s"\n'))
    source = profile.sources[0]
    assert getattr(source, "command") == ["python", "-m", "desk.feed"]  # a bare name is looked up on PATH
    assert Path(getattr(source, "cwd")) == (tmp_path.parent / "desk").resolve()
    assert (getattr(source, "timeout"), getattr(source, "refresh")) == (120, "30s")


def test_a_commands_program_path_and_folder_are_relative_to_the_profile(tmp_path, monkeypatch):
    home, elsewhere = tmp_path / "kestrel", tmp_path / "elsewhere"
    home.mkdir()
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    profile, _ = load_profile(write(home, FEED + 'command = ["./tools/x.py", "--out", "./feed.json"]\n'
                                                 'cwd = "../desk"\n'))
    source = profile.sources[0]
    # the program's own path, not where a link points: a virtual environment's python is often a link
    assert getattr(source, "command") == [os.path.abspath(home / "tools" / "x.py"), "--out", "./feed.json"]
    assert Path(getattr(source, "cwd")) == (tmp_path / "desk").resolve()
    profile, _ = load_profile(write(home, FEED + r'command = ["..\\desk\\export.exe"]' + "\n"))  # Windows style
    assert getattr(profile.sources[0], "command") == [os.path.abspath(home / r"..\desk\export.exe")]


def test_a_command_runs_in_the_profiles_folder_unless_it_says_otherwise(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path.parent)
    profile, _ = load_profile(write(tmp_path, FEED + COMMAND))
    assert Path(getattr(profile.sources[0], "cwd")) == tmp_path.resolve()


@pytest.mark.skipif(os.name == "nt", reason="a link needs extra rights on Windows")
def test_a_program_that_is_a_link_is_run_by_its_own_path(tmp_path):
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "python").symlink_to(Path(sys.executable))
    profile, _ = load_profile(write(tmp_path, FEED + 'command = ["./venv/python", "-m", "desk.feed"]\n'))
    assert getattr(profile.sources[0], "command")[0] == str(tmp_path / "venv" / "python")


@pytest.mark.parametrize("value", ['"python -m desk.feed"', "[]", '[""]', '["python", ""]', '["python", 5]', "5"],
                         ids=["a string", "empty", "an empty program", "an empty argument", "a number argument",
                              "a number"])
def test_a_command_is_a_list_of_strings(tmp_path, value):
    with pytest.raises(ProfileError) as error:
        load_profile(write(tmp_path, FEED + f"command = {value}\n"))
    assert 'a command is a list: the program, then its arguments, e.g. command = ["python", "-m", "desk.feed"]' in str(
        error.value)


def test_a_command_cant_hold_a_nul_character(tmp_path):
    with pytest.raises(ProfileError, match="a command can't hold a NUL character"):
        load_profile(write(tmp_path, FEED + r'command = ["python", "desk\u0000feed"]' + "\n"))  # a TOML escape


def test_a_command_takes_no_token(tmp_path):
    with pytest.raises(ProfileError, match="token_env goes with a url: a command gets kestrel's environment"):
        load_profile(write(tmp_path, FEED + COMMAND + 'token_env = "KESTREL_DESK_TOKEN"\n'))


@pytest.mark.parametrize("value", ['""', "5", '["../desk"]'])
def test_a_commands_folder_is_a_name_in_quotes(tmp_path, value):
    with pytest.raises(ProfileError, match='cwd is a folder name in quotes, e.g. cwd = "../desk"'):
        load_profile(write(tmp_path, FEED + COMMAND + f"cwd = {value}\n"))


@pytest.mark.parametrize("refresh", ['"1s"', '"4s"', '"61m"', '"2h"', '"soon"', "60", '"0m"'])
def test_a_commands_refresh_is_5_seconds_to_an_hour(tmp_path, refresh):
    with pytest.raises(ProfileError, match="refresh is how long one run's output is reused, from 5s to 1h"):
        load_profile(write(tmp_path, FEED + COMMAND + f"refresh = {refresh}\n"))
    for fine in ("5s", "90s", "1h", "60m"):
        profile, _ = load_profile(write(tmp_path, FEED + COMMAND + f'refresh = "{fine}"\n'))
        assert getattr(profile.sources[0], "refresh") == fine


@pytest.mark.parametrize("timeout", ["0", "0.5", "121", '"30"', "true"])
def test_a_commands_timeout_is_1_to_120_seconds(tmp_path, timeout):
    with pytest.raises(ProfileError, match="timeout is in seconds, from 1 to 120"):
        load_profile(write(tmp_path, FEED + COMMAND + f"timeout = {timeout}\n"))
    for fine in ("1", "61", "120"):
        profile, _ = load_profile(write(tmp_path, FEED + COMMAND + f"timeout = {fine}\n"))
        assert getattr(profile.sources[0], "timeout") == int(fine)


@pytest.mark.parametrize("line,message", [('refresh = "1m"\n', "refresh goes with a command"),
                                          ('cwd = "../desk"\n', "cwd goes with a command")])
def test_refresh_and_cwd_go_only_with_a_command(tmp_path, line, message):
    for where in ('url = "http://127.0.0.1:8000/api/feed"\n', 'path = "feed.json"\n'):
        with pytest.raises(ProfileError, match=message):
            load_profile(write(tmp_path, FEED + where + line))


def test_source_config_matches_exact_id_first_then_the_longest_prefix():
    desk = SourceCfg(id="desk", kind="feed", url="http://127.0.0.1:9000/feed")
    desk2 = SourceCfg(id="desk-2", kind="feed", url="http://127.0.0.1:9001/feed")
    for sources in ([desk, desk2], [desk2, desk]):
        profile = Profile(sources=sources)
        assert source_config(profile, "desk").id == "desk"
        assert source_config(profile, "desk-2").id == "desk-2"
        # "desk-extra" has no exact entry: it falls back to the one cfg it's a sub-source of ("desk-2-" isn't a
        # prefix of it), whichever order the profile lists the sources in
        assert source_config(profile, "desk-extra").id == "desk"
    assert source_config(Profile(sources=[desk]), "nope") is None
