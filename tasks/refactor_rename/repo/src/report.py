from src.billing import calc_total


def build_report(items):
    return {"total": calc_total(items), "count": len(items)}
