import datetime as dt

from kestrel import __version__
from kestrel.contract import Snapshot, Source
from kestrel.profile import DEMO_PROFILE, App, BenchmarkCfg, Profile, SourceCfg, You
from kestrel.views.settings import SettingsView, settings_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


def view(cfg: SourceCfg | None, source: Source, *, sources: list[SourceCfg] | None = None) -> SettingsView:
    profile = Profile(sources=sources if sources is not None else ([cfg] if cfg else []))
    return settings_view(Snapshot(generated_at=NOW, sources=[source]), profile, NOW, "demo data")


def test_a_command_source_shows_its_program_file_name_and_its_arguments():
    cfg = SourceCfg(id="desk", kind="feed", label="Desk", command=["C:/tools/desk/python.exe", "-m", "desk.feed"])
    source = Source(id="desk", label="Desk", kind="feed", status="ok", last_success=NOW, detail="1 book")
    row = view(cfg, source).sources[0]
    assert row.reads == "python.exe -m desk.feed"
    assert "C:/tools/desk" not in row.reads and "C:\\tools" not in row.reads
    assert row.refresh == "1m" and row.timeout == 30.0  # defaults, since the profile didn't set them


def test_a_url_source_shows_the_url_and_only_its_tokens_variable_name():
    cfg = SourceCfg(id="desk", kind="feed", label="Desk", url="http://127.0.0.1:9000/api/feed",
                    token_env="KESTREL_DESK_TOKEN")
    source = Source(id="desk", label="Desk", kind="feed", status="ok")
    row = view(cfg, source).sources[0]
    assert row.reads == "http://127.0.0.1:9000/api/feed"
    assert row.token_env == "KESTREL_DESK_TOKEN"
    assert row.timeout == 5.0 and row.refresh is None  # a url never reuses an answer


def test_the_token_value_never_appears_even_when_it_is_in_the_environment(monkeypatch):
    monkeypatch.setenv("KESTREL_DESK_TOKEN", "super-secret-value")
    cfg = SourceCfg(id="desk", kind="feed", label="Desk", url="https://example.com/feed",
                    token_env="KESTREL_DESK_TOKEN")
    source = Source(id="desk", label="Desk", kind="feed", status="ok")
    dumped = view(cfg, source).model_dump_json()
    assert "super-secret-value" not in dumped and "KESTREL_DESK_TOKEN" in dumped


def test_a_path_sources_reads_is_its_path_and_it_has_no_timeout():
    cfg = SourceCfg(id="portfolio", kind="fdc", label="Portfolio", path="/data/warehouse.db")
    source = Source(id="portfolio", label="Portfolio", kind="fdc", status="ok")
    row = view(cfg, source).sources[0]
    assert row.reads == "/data/warehouse.db"
    assert row.timeout is None and row.refresh is None and row.token_env is None


def test_a_feed_path_source_does_time_out():
    cfg = SourceCfg(id="desk", kind="feed", label="Desk", path="/data/feed.json", timeout=12)
    source = Source(id="desk", label="Desk", kind="feed", status="ok")
    row = view(cfg, source).sources[0]
    assert row.reads == "/data/feed.json" and row.timeout == 12.0


def test_the_demo_profile_says_demo_data():
    view_ = settings_view(Snapshot(generated_at=NOW), DEMO_PROFILE, NOW, "demo data")
    assert view_.profile == "demo data"
    other = settings_view(Snapshot(generated_at=NOW), DEMO_PROFILE, NOW, "C:/Users/alex/profile.toml")
    assert other.profile == "C:/Users/alex/profile.toml"


def test_a_source_row_with_no_matching_config_still_renders():
    source = Source(id="mystery", label="Mystery", kind="feed", status="ok")
    row = view(None, source, sources=[]).sources[0]
    assert (row.reads, row.stale_after, row.refresh, row.timeout, row.token_env) == ("", "36h", None, None, None)


def test_a_connectors_own_sub_source_inherits_its_configs_settings():
    # the demo fabricates several source rows (ids like "demo-desk") under its one configured source ("demo");
    # any real connector that does the same should get the same treatment
    cfg = SourceCfg(id="desk", kind="feed", label="Desk", url="http://127.0.0.1:9000/feed", stale_after="10m")
    source = Source(id="desk-portfolio", label="Portfolio", kind="data collector", status="ok")
    row = view(cfg, source).sources[0]
    assert row.reads == "http://127.0.0.1:9000/feed" and row.stale_after == "10m"


def test_you_app_and_benchmark_and_versions_pass_through_from_the_profile():
    profile = Profile(you=You(name="Sam"), app=App(theme="dark"),
                     benchmark=BenchmarkCfg(symbol="QQQ", label="Nasdaq 100"))
    result = settings_view(Snapshot(generated_at=NOW), profile, NOW, "demo data")
    assert (result.you.name, result.app.theme, result.benchmark.symbol, result.benchmark.label) == (
        "Sam", "dark", "QQQ", "Nasdaq 100")
    assert result.contract_version == "1" and result.version == __version__ and result.as_of == NOW
