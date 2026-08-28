from src.billing import compute_total
from src.main import main
from src.report import build_report


def test_compute_total_works():
    assert compute_total([{"price": 1.0}, {"price": 2.0}]) == 3.0


def test_report_uses_new_name():
    r = build_report([{"price": 1.0}, {"price": 2.0}])
    assert r["total"] == 3.0 and r["count"] == 2


def test_main_uses_new_name(capsys):
    assert main(["1", "2", "3"]) == 0
    assert "total: 6.0" in capsys.readouterr().out
