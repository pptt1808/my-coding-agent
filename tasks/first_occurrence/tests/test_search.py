from src.search import first_occurrence


def test_no_duplicates():
    assert first_occurrence([1, 2, 3, 4], 3) == 2


def test_duplicates_middle():
    assert first_occurrence([1, 2, 2, 2, 3], 2) == 1  # buggy returns 3


def test_duplicates_start():
    assert first_occurrence([2, 2, 2, 3], 2) == 0


def test_duplicates_end():
    assert first_occurrence([1, 2, 3, 3], 3) == 2


def test_not_found():
    assert first_occurrence([1, 3, 5], 2) == -1


def test_empty():
    assert first_occurrence([], 1) == -1


def test_single():
    assert first_occurrence([7], 7) == 0
    assert first_occurrence([7], 8) == -1


def test_all_same():
    assert first_occurrence([4, 4, 4], 4) == 0
