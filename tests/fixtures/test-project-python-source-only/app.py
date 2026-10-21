def add(a, b):
    return a + b


def divide(a, b):
    return a / b


def average(values):
    return sum(values) / len(values)


def calculate_report(values):
    total = sum(values)
    avg = average(values)

    return {
        "total": total,
        "average": avg,
        "count": len(values)
    }


if __name__ == "__main__":
    numbers = [10, 20, 30, 40]

    print("Add:", add(10, 5))
    print("Divide:", divide(10, 2))
    print("Report:", calculate_report(numbers))
