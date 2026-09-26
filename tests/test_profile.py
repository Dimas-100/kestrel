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
