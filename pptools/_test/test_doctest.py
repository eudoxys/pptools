"""Run the examples in module docstrings against the installed package"""

import doctest

import pptools.project
import pptools.tools

def test_docstring_examples():
    """`pptools.project` and `pptools.tools` docstring examples reproduce their shown output"""
    for module in (pptools.project,pptools.tools):
        failed,tried = doctest.testmod(module)
        assert tried > 0 and failed == 0, module.__name__
