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
STEPS = ["vision", "story", "mvp", "polish", "pitch"]

PM_PERSONA = (
    "You are a PRODUCT-MANAGER-minded demo builder working in: {workdir}.\n"
    "You turn ideas into quick, runnable demos that TELL A STORY — not production "
    "code. You think like a PM:\n"
    "  - Clarify the AUDIENCE, what ONE thing it must prove, and the demo "
    "    WOW-moment before building (JTBD / Double-diamond).\n"
    "  - Build the SMALLEST runnable thing (Lean MVP) and FAKE/STUB anything "
    "    external (backends, hard data) instead of engineering it.\n"
    "  - No over-engineering: no premature architecture, CI, tests-for-tests, "
    "    or polish on non-demo paths.\n"
    "  - Time-box: prefer a crisp happy-path demo over breadth.\n"
    "  - Every step must leave something runnable or showable.\n"
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
        "DEMO STORY: Distill a 30-second narrative (problem -> solution -> payoff) "
        "from the vision + the user's goal. Write it to "
        f"{DEMO_DIR}/{ARTIFACTS['story']} as talking points a human would say out "
        "loud while showing the demo."
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
        "PITCH: Write a short pitch to " f"{DEMO_DIR}/{ARTIFACTS['pitch']}" ": the "
        "value proposition in one paragraph, the demo's wow moment, limitations, "
        "and 1-2 next steps. Address the audience from the vision."
    ),
}


@dataclass
class PmSession:
    """One PM demo session: keeps the product context; writes artifacts to the demo dir."""

    _agent: CodingAgent
    _workdir: Path
    _messages: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(cls, config: Config, llm: LLMClient | None = None, model: str | None = None) -> "PmSession":
        return cls(_agent=CodingAgent(config, llm=llm, model=model,
                                      system_prompt=PM_PERSONA.format(workdir=config.workdir)),
                   _workdir=config.workdir)

    def demo_dir(self) -> Path:
        d = self._workdir / DEMO_DIR
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _artifact(self, step: str) -> Path:
        return self.demo_dir() / ARTIFACTS[step]

    def turn(self, line: str) -> list[str]:
        """A plain conversational turn in the PM persona (describe the idea, answer questions)."""
        self._messages.append({"role": "user", "content": line})
        answer, self._messages = self._agent.run_turn(self._messages)
        return [answer]

    def run_step(self, step: str, task: str) -> list[str]:
        """Run one PM step with the persona + step-specific instruction; persist its artifact."""
        if step not in STEPS:
            return [f"unknown pm step: {step} (use /vision /story /mvp /polish /pitch)"]
        self.demo_dir()  # ensure the PM workspace exists for every step
        # include the persona + step instruction + the accumulated product context
        extra = STEP_PROMPTS[step]
        self._messages.append({"role": "user", "content": task})
        answer, self._messages = self._agent.run_turn(self._messages, extra_system=extra)
        # persist the artifact (vision/story/pitch write text; mvp/polish write code + a note)
        if step in ARTIFACTS:
            self._artifact(step).write_text(answer, encoding="utf-8")
            return [f"[pm:{step}] wrote {self._artifact(step).name} ({len(answer)} chars)", answer[:800]]
        return [f"[pm:{step}] {answer[:800]}"]
