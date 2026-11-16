"""Run the examples in the pprun module docstrings"""

import doctest

import pptools.pprun.sim
import pptools.pprun.runner

def test_docstring_examples():
    """`pptools.pprun.sim` and `pptools.pprun.runner` docstring examples reproduce their shown output"""
    for module in (pptools.pprun.sim,pptools.pprun.runner):
        failed,tried = doctest.testmod(module)
        assert tried > 0 and failed == 0, module.__name__
