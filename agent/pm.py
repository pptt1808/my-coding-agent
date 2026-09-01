"""Personalized PM demo-development mode (specs/pm-mode.md).

A product-manager-flavored development mode for **vibe-coding demos** — our own
synthesis of PM methodology (no open-source coding agent does this). The agent
acts as a product-minded demo builder who:

  1. asks WHO it's for, WHAT one thing it must prove, and the demo WOW-moment
     (Clarify / JTBD / Double-diamond) -> DEMO_SPEC.md
  2. distills a 30s story (problem -> solution -> payoff) -> DEMO_SCRIPT.md
  3. scaffolds the smallest RUNNABLE thing (Lean MVP, fake/stub the rest) -> demo code
  4. polishes the happy-path demo moment
  5. writes a pitch (why it matters / next steps) -> PITCH.md

Guardrails (PM skill): time-box; NO over-engineering (no premature architecture
/CI/tests-for-tests); external deps are stubbed; every step leaves something
runnable/showable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Config
from .llm import LLMClient
from .loop import CodingAgent

DEMO_DIR = "demo"
ARTIFACTS = {
    "vision": "DEMO_SPEC.md",
    "story": "DEMO_SCRIPT.md",
    "pitch": "PITCH.md",
}
STEPS = ["vision", "story", "mvp", "polish", "pitch", "validate"]

PM_PERSONA = (
    "You are a PRODUCT-MANAGER-minded demo builder working in: {workdir}.\n"
    "You run a REAL product process with the user, in order — never skip ahead:\n"
    "  1. CLARIFY: ask the user about their REAL goal, ONE key product question at a\n"
    "     time (audience / what to prove / demo wow-moment / what to cut). Do NOT build.\n"
    "  2. SPEC: once clarified, write demo/DEMO_SPEC.md and ASK THE USER TO CONFIRM it\n"
    "     before any code. Do NOT write demo code until the user confirms.\n"
    "  3. MVP: only after confirmation, build the SMALLEST runnable thing (Lean MVP),\n"
    "     FAKING/stubbing anything external. Time-boxed.\n"
    "  4. VALIDATE: run it for the user, get real feedback, iterate.\n"
    "  5. STORY & PITCH: only after the demo works, produce the 30s narrative + pitch.\n"
    "Guardrails: no over-engineering (no architecture/CI/tests-for-tests); external deps\n"
    "stubbed; every step leaves something runnable/showable; clarify before building.\n"
    "PLATFORM: Windows cmd; use python -c / dir / the glob/grep tools.\n"
)

# one-line instruction per step, appended on top of the persona
STEP_PROMPTS = {
    "vision": (
        "PRODUCT CLARIFY: Ask the user the 1-3 most important product questions "
        "(audience / what to prove / demo wow-moment) in plain language. If the "
        "user already answered them (or after they do), write the result to "
        f"{DEMO_DIR}/{ARTIFACTS['vision']} as a one-page spec: Vision, Audience, "
        "Key claim, Demo moment, Acceptance criteria. Keep it crisp."
    ),
    "story": (
        "DEMO STORY: Write the 30-second narrative (problem -> solution -> payoff) as "
        "clear talking points. Reply with ONLY the markdown content for "
        f"{DEMO_DIR}/{ARTIFACTS['story']} — the entire reply IS the file. Do NOT include "
        "any preamble, file listings, or 'all done / no action needed' notes."
    ),
    "mvp": (
        "BUILD MVP: In this workspace, scaffold the SMALLEST runnable demo that "
        "shows the demo moment. Fake/stub any external services or real data. Make "
        "it actually run (e.g. a small CLI/HTML page) and run it to confirm. Do not "
        "over-engineer. Leave a short README in the demo dir."
    ),
    "polish": (
        "POLISH: Make the demo's happy path crisp and error-free. Remove anything "
        "that breaks the demo moment. Do not add features beyond the story."
    ),
    "pitch": (
        "PITCH: Write a short pitch (value proposition, demo wow moment, limitations, "
        "1-2 next steps) addressing the audience from the vision. Reply with ONLY the "
        f"markdown content for {DEMO_DIR}/{ARTIFACTS['pitch']} — the entire reply IS "
        "the file. No preamble or 'all set' notes."
    ),
    "validate": (
        "VALIDATE: Run the demo (e.g. `python <demo>`, or open the page) and show the "
        "user the result. Ask ONE question about what to improve. Do not add scope "
        "unprompted."
    ),
}


_META_MARKERS = (
    "all set", "no action needed", "nothing new", "no worries", "noted",
    "just say the word", "waiting", "so where", "no problem", "all good",
    "where things stand", "what's left", "since your", "just reply", "the demo is done",
    "still green", "pick one", "which one?",
)


def _first_content_line(text: str) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def _extract_markdown_doc(text: str) -> str | None:
    """If a reply embeds a markdown document (a '# heading' block), return that block."""
    lines = (text or "").splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip().startswith("# ")), None)
    if start is None:
        return None
    return "\n".join(lines[start:]).strip()


def _looks_like_meta(text: str) -> bool:
    """True if a reply is conversational meta, not a markdown artifact document."""
    low = (text or "").lower()
    stripped = (text or "").strip()
    if any(m in low for m in _META_MARKERS):
        return True
    # a real artifact is a markdown document that opens with a # heading
    first = _first_content_line(text)
    if not first.startswith("#"):
        return True
    return len(stripped) < 20


def build_pm_persona(workdir: Path | str) -> str:
    """The PM persona, optionally enriched with a persistent PM_PROFILE.md."""
    persona = PM_PERSONA.format(workdir=workdir)
    profile = Path(workdir) / "PM_PROFILE.md"
    if profile.exists():
        try:
            persona += "\n\nUSER PM PROFILE (follow the user's preference):\n" + \
                profile.read_text(encoding="utf-8")[:2000]
        except Exception:
            pass
    return persona


def apply_pm_mode(agent: CodingAgent) -> str:
    """Switch the SAME agent into PM mode (persona override) — a mode, not a new agent."""
    agent._system_prompt_override = build_pm_persona(agent._workdir)
    return "PM mode on — I'll clarify before building. Steps: /vision /story /mvp /validate /polish /pitch. /pm again to exit."


def exit_pm_mode(agent: CodingAgent) -> str:
    agent._system_prompt_override = None
    return "back to normal coding mode."


def demo_dir(workdir: Path | str) -> Path:
    d = Path(workdir) / DEMO_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def artifact_path(workdir: Path | str, step: str) -> Path:
    return demo_dir(workdir) / ARTIFACTS[step]


def pm_turn(agent: CodingAgent, messages: list[dict[str, Any]], line: str,
            ) -> tuple[list[dict[str, Any]], list[str]]:
    """A normal turn inside PM mode: the agent (with the PM persona) converses/clarifies."""
    messages = list(messages) + [{"role": "user", "content": line}]
    answer, messages = agent.run_turn(messages)
    return messages, [answer]


def pm_step(agent: CodingAgent, messages: list[dict[str, Any]], workdir: Path | str,
            step: str, task: str, stream: bool = False,
            on_delta: Any | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """Run one PM step against the SAME agent; persist its artifact; enforces gates.

    `stream=True` + `on_delta` streams the step's answer text as it arrives, so
    `/vision` etc. display incrementally instead of appearing all at once.
    """
    if step not in STEPS:
        return messages, [f"unknown pm step: {step} (use /vision /story /mvp /polish /pitch /validate)"]
    demo_dir(workdir)
    mvp_gate = ("mvp", "vision")
    if step == "mvp" and not artifact_path(workdir, "vision").exists():
        return messages, ["[pm:mvp] gate refused: run /vision first to align the spec, then I'll build "
                          "the smallest demo. We won't skip product clarity."]
    if step in ("story", "pitch") and not artifact_path(workdir, "vision").exists():
        return messages, [f"[pm:{step}] gate refused: no spec yet — run /vision to define the demo first."]
    messages = list(messages) + [{"role": "user", "content": task}]
    answer, messages = agent.run_turn(messages, extra_system=STEP_PROMPTS[step],
                                      stream=stream, on_delta=on_delta)
    if step in ARTIFACTS:
        return _write_artifact(agent, messages, workdir, step, answer)
    return messages, [f"[pm:{step}] {answer[:800]}"]


def _write_artifact(agent: CodingAgent, messages: list[dict[str, Any]], workdir: Path | str,
                    step: str, answer: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Persist a clean artifact; warn + let the user confirm if the model keeps replying with meta."""
    path = artifact_path(workdir, step)
    doc = _extract_markdown_doc(answer)
    if doc and not _looks_like_meta(doc):
        answer = doc
    if _looks_like_meta(answer):
        for _ in range(2):
            messages = list(messages) + [{"role": "user", "content":
                f"Reply with ONLY the markdown content for {ARTIFACTS[step]}. "
                f"Start with a heading like '# {ARTIFACTS[step]}'. No preamble, no "
                "'done / all set / where things stand' notes. The entire reply IS the file."}]
            answer2, messages = agent.run_turn(messages)
            doc2 = _extract_markdown_doc(answer2)
            if doc2 and not _looks_like_meta(doc2):
                answer = doc2
                break
            if not _looks_like_meta(answer2):
                answer = answer2
                break
    path.write_text(answer, encoding="utf-8")
    if _looks_like_meta(answer):
        return messages, [f"[pm:{step}] ⚠ wrote {path.name} ({len(answer)} chars) — the model kept "
                          f"replying with meta, so please review {path.name} manually or re-run the step.",
                          answer[:400]]
    return messages, [f"[pm:{step}] wrote {path.name} ({len(answer)} chars)", answer[:1000]]


@dataclass
class PmSession:
    """Thin wrapper over the shared PM functions (a single agent in PM mode)."""

    _agent: CodingAgent
    _workdir: Path
    _messages: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(cls, config: Config, llm: LLMClient | None = None, model: str | None = None) -> "PmSession":
        persona = build_pm_persona(config.workdir)
        return cls(_agent=CodingAgent(config, llm=llm, model=model, system_prompt=persona),
                   _workdir=config.workdir)

    def turn(self, line: str) -> list[str]:
        self._messages, out = pm_turn(self._agent, self._messages, line)
        return out

    def run_step(self, step: str, task: str) -> list[str]:
        self._messages, out = pm_step(self._agent, self._messages, self._workdir, step, task)
        return out
