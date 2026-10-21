import pytest

from app import add, average, divide, multiply


def test_add():
    assert add(2, 3) == 5


def test_multiply():
    assert multiply(4, 5) == 20


def test_divide_rejects_zero():
    with pytest.raises(ValueError):
        divide(10, 0)


def test_average_rejects_empty_values():
    with pytest.raises(ValueError):
        average([])
