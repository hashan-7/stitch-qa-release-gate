import pytest

from app import add, average, divide


def test_add_returns_sum():
    assert add(2, 3) == 5


def test_divide_returns_result():
    assert divide(10, 2) == 5


def test_divide_rejects_zero():
    with pytest.raises(ValueError):
        divide(10, 0)


def test_average_returns_mean():
    assert average([2, 4, 6]) == 4


def test_average_rejects_empty_values():
    with pytest.raises(ValueError):
        average([])
