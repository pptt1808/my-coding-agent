from src.main import main


def test_main_mean(capsys):
    assert main(["1", "2", "3"]) == 0
    assert "mean: 2.0" in capsys.readouterr().out


def test_main_stats_flag(capsys):
    assert main(["--stats", "1", "2", "3", "4"]) == 0
    out = capsys.readouterr().out
    assert "mean: 2.5" in out
    assert "variance: 1.25" in out
    assert "median: 2.5" in out
