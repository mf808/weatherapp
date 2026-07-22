import pytest

from src import main


# ── _validate_subdir (path-traversal guard) ─────────────────────

def test_validate_subdir_accepts_child():
    assert main._validate_subdir("/app", "fonts", "fonts_dir") == "/app/fonts"


def test_validate_subdir_accepts_nested_child():
    assert main._validate_subdir("/app", "assets/icons", "icons_dir") == "/app/assets/icons"


@pytest.mark.parametrize("subdir", ["../etc", "../../root", "/etc"])
def test_validate_subdir_rejects_escape(subdir):
    with pytest.raises(ValueError, match="escapes base directory"):
        main._validate_subdir("/app", subdir, "fonts_dir")


def test_validate_subdir_rejects_sneaky_traversal():
    with pytest.raises(ValueError):
        main._validate_subdir("/app", "fonts/../../etc", "fonts_dir")


# ── load_config ─────────────────────────────────────────────────

def test_load_config_reads_yaml(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("device: eink_landscape\nport: 9090\n")
    loaded = main.load_config(str(cfg))
    assert loaded["device"] == "eink_landscape"
    assert loaded["port"] == 9090


def test_load_config_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main.load_config(str(tmp_path / "nope.yaml"))
    assert exc.value.code == 1


# ── fetch_all_data degradation ──────────────────────────────────

def test_fetch_all_data_unknown_type_skipped():
    config = {"datasources": {"weird": {"type": "nonexistent"}}}
    assert main.fetch_all_data(config) == {}


def test_fetch_all_data_source_error_degrades_to_empty(monkeypatch):
    class Boom:
        def __init__(self, *a, **k): ...
        def fetch(self): raise RuntimeError("network down")

    monkeypatch.setitem(main.DATASOURCE_TYPES, "boom", Boom)
    config = {"datasources": {"src": {"type": "boom"}}}
    # A failing source must not propagate — it degrades to {} so the render proceeds.
    assert main.fetch_all_data(config) == {"src": {}}
