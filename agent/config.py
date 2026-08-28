"""Configuration loading from environment variables / `.env`.

Phase 0 (N1). Reads API key, gateway base URL, model, workdir and loop limits.
This is one of the few *fully implemented* files in the scaffold, because the
config contract is stable and everything else depends on it.

Spec: see specs/config.md (to be written) — acceptance criteria:
  C1  loads key from API_KEY or OPENAI_API_KEY env;
  C2  raises a clear error when no key is present;
  C3  defaults applied when optional vars are absent;
  C4  workdir resolved to an absolute path.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _find_env_file() -> Path:
    """Locate the .env file.

    Search order (other coding agents' convention: launch in the project dir):
      1. explicit CODING_AGENT_ENV (if set, use ONLY it);
      2. <cwd>/.env                       (launch inside your project -> its .env);
      3. <package root>/.env              (this project's own .env as a fallback);
      4. ~/.coding-agent/.env             (user-level config).
    """
    explicit = os.environ.get("CODING_AGENT_ENV")
    if explicit:
        return Path(explicit)
    candidates = [Path.cwd() / ".env"]
    candidates.append(Path(__file__).resolve().parents[1] / ".env")
    candidates.append(Path.home() / ".coding-agent" / ".env")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]  # missing file is a harmless no-op for load_dotenv


@dataclass(frozen=True)
class Config:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    eval_model: str = ""  # stronger model for the eval harness; falls back to `model`
    workdir: Path = Path(".")
    max_steps: int = 25
    max_tool_calls: int = 50
    command_timeout: int = 60
    output_cap_chars: int = 8000
    max_consecutive_failures: int = 3
    no_progress_limit: int = 3
    max_elapsed_s: float = 600.0
    auto_compact_at_tokens: int = 0  # >0 enables auto-compaction above this history size
    stream: bool = True  # stream model tokens to the terminal (R11/C9)

    @property
    def eval_model_name(self) -> str:
        """The model used by the evaluation harness (分层: eval uses the strong tier)."""
        return self.eval_model or self.model

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Config":
        """Build a Config from environment (optionally loading a .env file)."""
        if env_file is None:
            env_file = _find_env_file()
        load_dotenv(dotenv_path=env_file)

        api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "No API key found. Set API_KEY (or OPENAI_API_KEY) or provide a .env "
                "file — see .env.example. Keys must never be committed."
            )

        return cls(
            api_key=api_key,
            base_url=os.environ.get("BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("MODEL", "gpt-4o-mini"),
            eval_model=os.environ.get("EVAL_MODEL", ""),
            workdir=Path(os.environ.get("WORKDIR", ".")).resolve(),
            max_steps=int(os.environ.get("MAX_STEPS", "25")),
            max_tool_calls=int(os.environ.get("MAX_TOOL_CALLS", "50")),
            command_timeout=int(os.environ.get("COMMAND_TIMEOUT", "60")),
            output_cap_chars=int(os.environ.get("OUTPUT_CAP_CHARS", "8000")),
            max_consecutive_failures=int(os.environ.get("MAX_CONSECUTIVE_FAILURES", "3")),
            no_progress_limit=int(os.environ.get("NO_PROGRESS_LIMIT", "3")),
            max_elapsed_s=float(os.environ.get("MAX_ELAPSED_S", "600")),
            auto_compact_at_tokens=int(os.environ.get("AUTO_COMPACT_AT_TOKENS", "0")),
            stream=os.environ.get("STREAM", "1") != "0",
        )
