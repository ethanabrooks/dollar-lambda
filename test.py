#! /usr/bin/env python
import doctest
import unittest
from abc import ABC, abstractmethod

import dollar_lambda
from dollar_lambda import args, parser, result, sequence


def load_tests(_, tests, __):

    parser.TESTING = True
    for mod in [
        parser,
        sequence,
        result,
        dollar_lambda,
        args,
    ]:
        tests.addTests(doctest.DocTestSuite(mod))
    return tests


class MonadLawTester(ABC):
    @abstractmethod
    def assertEqual(self, a, b):
        raise NotImplementedError

    def f1(self, x):
        unwrapped = self.unwrap(x)
        if isinstance(x, int):
            return self.m(unwrapped + 1)
        else:
            return self.m(unwrapped)

    def f2(self, x):
        unwrapped = self.unwrap(x)
        if isinstance(unwrapped, int):
            return self.m(unwrapped * 2)
        else:
            return self.m(unwrapped)

    @staticmethod
    @abstractmethod
    def m(a):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def return_(a):
        raise NotImplementedError

    @staticmethod
    def unwrapped_values():
        return [1]

    @staticmethod
    @abstractmethod
    def wrapped_values():
        raise NotImplementedError

    def test_law1(self):
        for a in self.unwrapped_values():
            x1 = self.return_(a) >= self.f1
            x2 = self.m(self.f1(a))
            self.assertEqual(self.unwrap(x1), self.unwrap(x2))

    def test_law2(self):
        for p in self.wrapped_values():
            p = self.m(p)
            a = p >= self.return_
            self.assertEqual(self.unwrap(a), self.unwrap(p))

    def test_law3(self):
        for p in self.wrapped_values():
            p = self.m(p)
            x1 = p >= (lambda a: self.f1(a) >= self.f2)
            x2 = (p >= self.f1) >= self.f2
            self.assertEqual(self.unwrap(x1), self.unwrap(x2))

    @staticmethod
    @abstractmethod
    def unwrap(x):
        raise NotImplementedError


if __name__ == "__main__":
    unittest.main()
