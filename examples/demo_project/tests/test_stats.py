from src.stats import mean, median, variance


def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_variance_population():
    assert abs(variance([1, 2, 3, 4]) - 1.25) < 1e-9


def test_variance_single_element():
    assert variance([5]) == 0.0


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    assert median([4, 1, 3, 2]) == 2.5
