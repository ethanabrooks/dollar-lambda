#! /usr/bin/env python

import doctest
import unittest

from monad_argparse import monad, parser


def load_tests(_, tests, __):
    tests.addTests(doctest.DocTestSuite(monad))
    tests.addTests(doctest.DocTestSuite(parser))
    return tests


if __name__ == "__main__":
    unittest.main()
