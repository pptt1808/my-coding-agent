def first_occurrence(sorted_list, target):
    """Return the index of the FIRST occurrence of target in a sorted list
    (which may contain duplicates), or -1 if absent.

    THERE IS A BUG in this implementation — find and fix it.
    """
    lo, hi = 0, len(sorted_list) - 1
    result = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_list[mid] == target:
            result = mid
            lo = mid + 1  # ??? continues searching to the RIGHT
        elif sorted_list[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return result
