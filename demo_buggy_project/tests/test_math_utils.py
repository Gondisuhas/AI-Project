import pytest
from math_utils import average

def test_average_normal_values():
    assert average([2, 4, 6]) == 4

def test_average_single_value():
    assert average([7]) == 7

def test_average_empty_list_is_rejected():
    with pytest.raises(ValueError):
        average([])
