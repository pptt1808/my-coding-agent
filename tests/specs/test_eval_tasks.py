"""Contract tests for specs/eval-tasks.md — EV1-EV4.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

import pytest

from eval.tasks import load_tasks


@pytest.fixture
def valid_task(tmp_path):
    root = tmp_path / "fix_add_bug"
    (root / "repo").mkdir(parents=True)
    (root / "repo" / "util.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "DESCRIPTION.md").write_text("make add() return a - b", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_util.py").write_text("def test_x():\n    assert True", encoding="utf-8")
    return tmp_path


@pytest.fixture
def rubric_task(tmp_path):
    root = tmp_path / "with_rubric"
    (root / "repo").mkdir(parents=True)
    (root / "repo" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "DESCRIPTION.md").write_text("do something", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_a.py").write_text("def test_a():\n    assert True", encoding="utf-8")
    (root / "rubric.json").write_text('{"quality": "code quality", "minimal": "minimal change"}', encoding="utf-8")
    return tmp_path


def test_ev1_loads_task_with_fields(valid_task):
    tasks = load_tasks(valid_task)
    assert len(tasks) == 1
    t = tasks[0]
    assert t.id == "fix_add_bug"
    assert "a - b" in t.description
    assert t.repo_seed.is_dir()
    assert t.hidden_tests.is_dir()


def test_ev2_missing_required_field_raises(tmp_path):
    bad = tmp_path / "broken"
    (bad / "repo").mkdir(parents=True)  # no DESCRIPTION.md
    (bad / "tests").mkdir()
    with pytest.raises(ValueError, match="broken"):
        load_tasks(tmp_path)


def test_ev3_rubric_defaults_empty(valid_task):
    tasks = load_tasks(valid_task)
    assert tasks[0].rubric == {}


def test_ev3b_rubric_loaded_from_json(rubric_task):
    tasks = load_tasks(rubric_task)
    assert tasks[0].rubric == {"quality": "code quality", "minimal": "minimal change"}


def test_ev4_hidden_tests_exist(valid_task):
    tasks = load_tasks(valid_task)
    assert tasks[0].hidden_tests.is_dir()
