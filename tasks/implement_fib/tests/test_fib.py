import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from fib import fib


def test_fib_base_cases():
    assert fib(0) == 0
    assert fib(1) == 1


def test_fib_small():
    assert fib(2) == 1
    assert fib(5) == 5
    assert fib(6) == 8


def test_fib_larger():
    assert fib(10) == 55
    assert fib(15) == 610
