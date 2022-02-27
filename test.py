#! /usr/bin/env python
import doctest
import unittest
from abc import ABC, abstractmethod

from monad_argparse.monad import io, lst, monad, option, result
from monad_argparse.monad.io import I
from monad_argparse.monad.lst import L
from monad_argparse.monad.option import O
from monad_argparse.monad.result import R
from monad_argparse.parser import parser


def load_tests(_, tests, __):
    for mod in [monad, parser, lst, option, result, io]:
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
            self.assertEqual(self.return_(a) >= self.f1, self.m(self.f1(a)))

    def test_law2(self):
        for p in self.wrapped_values():
            p = self.m(p)
            self.assertEqual(p >= self.return_, p)

    def test_law3(self):
        for p in self.wrapped_values():

            p = self.m(p)
            x1 = p >= (lambda a: self.f1(a) >= self.f2)
            x2 = (p >= self.f1) >= self.f2
            self.assertEqual(x1, x2)

    @staticmethod
    @abstractmethod
    def unwrap(x):
        raise NotImplementedError


class TestOption(MonadLawTester, unittest.TestCase):
    def assertEqual(self, a, b):
        return unittest.TestCase.assertEqual(self, a, b)

    @staticmethod
    def m(a):
        return O(a)

    @staticmethod
    def return_(a):
        return O.return_(a)

    @staticmethod
    def wrapped_values():
        return [1, None]

    @staticmethod
    def unwrap(x):
        return O.unwrap(x)


class TestResult(MonadLawTester, unittest.TestCase):
    def assertEqual(self, a, b):
        return unittest.TestCase.assertEqual(self, a, b)

    @staticmethod
    def m(a):
        return R(a)

    @staticmethod
    def return_(a):
        return R.return_(a)

    @staticmethod
    def unwrap(x):
        return R.unwrap(x)

    @staticmethod
    def wrapped_values():
        return [1, AssertionError()]


class TestList(MonadLawTester, unittest.TestCase):
    def assertEqual(self, a, b):
        return unittest.TestCase.assertEqual(self, a, b)

    def f1(self, x):
        unwrapped = self.unwrap(x)
        assert isinstance(unwrapped, int)
        return L([unwrapped + 1])

    def f2(self, x):
        unwrapped = self.unwrap(x)
        assert isinstance(unwrapped, int)
        return L([unwrapped * 2])

    @staticmethod
    def m(a):
        return L(a)

    @staticmethod
    def return_(a):
        return L.return_(a)

    @staticmethod
    def unwrap(x):
        return L.unwrap(x)

    @staticmethod
    def wrapped_values():
        return [[], [1], [2, 3]]


class TestIO(MonadLawTester, unittest.TestCase):
    def assertEqual(self, a, b):
        return unittest.TestCase.assertEqual(self, a, b)

    def f1(self, x):
        assert isinstance(x, int)
        return self.m(lambda: x + 1)

    def f2(self, x):
        assert isinstance(x, int)
        return self.m(lambda: x * 2)

    @staticmethod
    def m(a):
        return I(a)

    @staticmethod
    def return_(a):
        return I.return_(a)

    @staticmethod
    def unwrap(x):
        return I.unwrap(x)

    @staticmethod
    def wrapped_values():
        return [lambda: 1, lambda: 2]


if __name__ == "__main__":
    TestIO().test_law1()
    unittest.main()
