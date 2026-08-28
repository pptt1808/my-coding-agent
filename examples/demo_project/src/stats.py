def mean(values):
    return sum(values) / len(values)


def variance(values):
    # BUG: should use population variance (divide by n), not sample variance
    m = mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def median(values):
    # TODO: implement: sort and return the middle value (average of the two
    # middle values for an even-length list)
    raise NotImplementedError
