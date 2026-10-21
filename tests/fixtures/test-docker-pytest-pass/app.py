def add(a, b):
    return a + b


def divide(a, b):
    if b == 0:
        raise ValueError("b must not be zero")
    return a / b


def average(values):
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) / len(values)
