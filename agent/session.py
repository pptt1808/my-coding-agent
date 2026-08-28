"""Session persistence (specs/session.md S1-S4, A2/P1).

Sessions are saved as JSON under `<workdir>/.coding-agent/sessions/<id>.json`
(dot-dir, skipped by grep/list_dir noise rules, so it never pollutes the
agent's view of the repository).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class Session:
    id: str
    model: str
    workdir: str
    messages: list[dict[str, Any]]
    steps: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    updated_at: float = 0.0


def new_session_id() -> str:
    return uuid4().hex[:12]


def sessions_dir(workdir: Path | str) -> Path:
    return Path(workdir) / ".coding-agent" / "sessions"


def save_session(session: Session, workdir: Path | str) -> Path:
    """Persist a session; returns the written path (S1)."""
    d = sessions_dir(workdir)
    d.mkdir(parents=True, exist_ok=True)
    session.updated_at = time.time()
    path = d / f"{session.id}.json"
    path.write_text(json.dumps(asdict(session), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_session(workdir: Path | str, session_id: str) -> Session:
    """Load a session by id (S3: FileNotFoundError when missing)."""
    path = sessions_dir(workdir) / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"session not found: {session_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return Session(**data)


def list_sessions(workdir: Path | str) -> list[Session]:
    """List saved sessions, newest first; corrupt files are skipped (S2)."""
    d = sessions_dir(workdir)
    if not d.exists():
        return []
    sessions: list[Session] = []
    for p in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            sessions.append(load_session(workdir, p.stem))
        except Exception:
            continue
    return sessions
