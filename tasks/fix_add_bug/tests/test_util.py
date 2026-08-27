import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from util import add, sub


def test_add_returns_difference():
    assert add(10, 4) == 6


def test_add_negative():
    assert add(2, 5) == -3


def test_sub_untouched():
    assert sub(10, 4) == 6
