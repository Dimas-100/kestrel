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
