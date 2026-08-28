import pytest

from src.calc import evaluate


def test_precedence():
    assert evaluate("2 + 3 * 4") == 14.0


def test_parentheses():
    assert evaluate("(2 + 3) * 4") == 20.0


def test_left_assoc():
    assert evaluate("20 - 5 - 5") == 10.0
    assert evaluate("20 / 2 / 5") == 2.0


def test_floats():
    assert abs(evaluate("10 / 4") - 2.5) < 1e-9


def test_whitespace():
    assert evaluate("  1 +  2  ") == 3.0


def test_nested_parens():
    assert evaluate("((1 + 2) * (3 + 4))") == 21.0


def test_single_number():
    assert evaluate("42") == 42.0


def test_invalid_raises():
    with pytest.raises(ValueError):
        evaluate("")
    with pytest.raises(ValueError):
        evaluate("1 +")
    with pytest.raises(ValueError):
        evaluate("(1 + 2")


def test_division_by_zero_raises():
    with pytest.raises(ValueError):
        evaluate("1 / 0")
