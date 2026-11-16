"""Run the examples in module docstrings against the installed package"""

import doctest

import pptools.ppmodel.case

def test_case_examples():
    """`pptools.ppmodel.case` docstring examples reproduce their shown output"""
    failed,tried = doctest.testmod(pptools.ppmodel.case)
    assert tried > 0 and failed == 0
