def calc_total(items):
    """Sum the 'price' field of each item."""
    return sum(item.get("price", 0) for item in items)
