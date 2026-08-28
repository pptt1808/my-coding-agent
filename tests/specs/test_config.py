"""Contract tests for the config spec (specs/config.md -> to be written).

These encode the config acceptance criteria and are GREEN now, because
`agent/config.py` is the scaffold's one fully-implemented module (Phase 0/N1).

Criteria (see agent/config.py docstring):
  C1  loads key from API_KEY or OPENAI_API_KEY;
  C2  raises a clear error when no key is present;
  C3  applies defaults when optional vars are absent;
  C4  workdir resolved to an absolute path.
"""
from __future__ import annotations

import pytest

from agent.config import Config


@pytest.fixture(autouse=True)
def _no_dotenv_interference(monkeypatch, tmp_path):
    """Force Config.from_env to use an empty/generated env file, not a committed one."""
    monkeypatch.setenv("CODING_AGENT_ENV", str(tmp_path / "nonexistent.env"))


def test_c1_loads_key_from_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("API_KEY", "sk-test")
    cfg = Config.from_env()
    assert cfg.api_key == "sk-test"


def test_c1_loads_key_from_openai_api_key(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    cfg = Config.from_env()
    assert cfg.api_key == "sk-openai"


def test_c2_raises_without_key(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        Config.from_env()


def test_c3_applies_defaults(monkeypatch):
    monkeypatch.setenv("API_KEY", "sk-test")
    monkeypatch.delenv("MODEL", raising=False)
    cfg = Config.from_env()
    assert cfg.model == "gpt-4o-mini"
    assert cfg.base_url == "https://api.openai.com/v1"
    assert cfg.max_steps == 25


def test_c4_workdir_is_absolute(monkeypatch):
    monkeypatch.setenv("API_KEY", "sk-test")
    monkeypatch.setenv("WORKDIR", ".")
    cfg = Config.from_env()
    assert cfg.workdir.is_absolute()


def test_c5_eval_model_falls_back_to_model(monkeypatch):
    monkeypatch.setenv("API_KEY", "sk-test")
    monkeypatch.setenv("MODEL", "deepseek-v4-flash")
    monkeypatch.delenv("EVAL_MODEL", raising=False)
    cfg = Config.from_env()
    assert cfg.model == "deepseek-v4-flash"
    assert cfg.eval_model_name == "deepseek-v4-flash"


def test_c6_eval_model_from_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "sk-test")
    monkeypatch.setenv("MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("EVAL_MODEL", "deepseek-v4-pro")
    cfg = Config.from_env()
    assert cfg.eval_model == "deepseek-v4-pro"
    assert cfg.eval_model_name == "deepseek-v4-pro"


def test_c7_env_file_found_in_cwd(monkeypatch, tmp_path):
    """Launch-inside-your-project convention: <cwd>/.env is found."""
    monkeypatch.delenv("CODING_AGENT_ENV", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "API_KEY=sk-cwd\nMODEL=deepseek-v4-flash\n", encoding="utf-8")
    cfg = Config.from_env()
    assert cfg.api_key == "sk-cwd"
    assert cfg.model == "deepseek-v4-flash"


def test_c8_workdir_override(tmp_path):
    """--workdir flag overrides the workspace explicitly."""
    from agent.cli import apply_workdir

    cfg = Config(api_key="x")
    assert apply_workdir(cfg, None) is cfg  # no override -> unchanged
    new_cfg = apply_workdir(cfg, str(tmp_path))
    assert new_cfg.workdir == tmp_path.resolve()


def test_c9_stream_default_on(monkeypatch):
    monkeypatch.setenv("API_KEY", "sk-test")
    monkeypatch.delenv("STREAM", raising=False)
    assert Config.from_env().stream is True
    monkeypatch.setenv("STREAM", "0")
    assert Config.from_env().stream is False
