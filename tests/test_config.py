import pytest

from src.utils.config import resolve_env


def test_literal_string_passthrough():
    assert resolve_env("https://api.example.com") == "https://api.example.com"


def test_required_var_resolves(monkeypatch):
    monkeypatch.setenv("MY_VAR", "secret")
    assert resolve_env("${MY_VAR}") == "secret"


def test_required_var_missing_raises(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(EnvironmentError):
        resolve_env("${MISSING_VAR}")


def test_default_used_when_unset(monkeypatch):
    monkeypatch.delenv("OPT_VAR", raising=False)
    assert resolve_env("${OPT_VAR:-fallback}") == "fallback"


def test_default_overridden_when_set(monkeypatch):
    monkeypatch.setenv("OPT_VAR", "actual")
    assert resolve_env("${OPT_VAR:-fallback}") == "actual"


# ── Edge cases ──────────────────────────────────────────────────

def test_empty_string_default(monkeypatch):
    """A ${VAR:-} with no set value yields an empty string, not an error."""
    monkeypatch.delenv("OPT_VAR", raising=False)
    assert resolve_env("${OPT_VAR:-}") == ""


def test_url_default_with_colon_slash(monkeypatch):
    """Defaults containing ':-'-adjacent characters (URLs) split only on first ':-'."""
    monkeypatch.delenv("API", raising=False)
    assert resolve_env("${API:-https://api.example.com}") == "https://api.example.com"


def test_non_string_int_coerced():
    assert resolve_env(6940468) == "6940468"


def test_none_becomes_empty_string():
    assert resolve_env(None) == ""


def test_bare_dollar_brace_not_matched():
    """Only values that both start with '${' and end with '}' are treated as refs."""
    assert resolve_env("prefix ${VAR}") == "prefix ${VAR}"
