
def average(values):
    """Return the arithmetic mean of a non-empty list."""
    if not values:
        raise ValueError('values must not be empty')
    return sum(values) / len(values)
