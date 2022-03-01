#! /usr/bin/env python
import doctest
import unittest
from abc import ABC, abstractmethod

from monad_argparse.monad import io, lst, monad, option, result
from monad_argparse.monad.io import IO
from monad_argparse.monad.lst import List
from monad_argparse.monad.option import Option
from monad_argparse.monad.result import Result
from monad_argparse.parser import apply, argument, empty, flag, nonpositional
from monad_argparse.parser import option as parser_option
from monad_argparse.parser import parser, sat, type_


def load_tests(_, tests, __):
    for mod in [
        monad,
        parser,
        lst,
        option,
        result,
        io,
        apply,
        argument,
        empty,
        flag,
        parser_option,
        sat,
        type_,
        nonpositional,
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


class TestOption(MonadLawTester, unittest.TestCase):
    def assertEqual(self, a, b):
        return unittest.TestCase.assertEqual(self, a, b)

    @staticmethod
    def m(a):
        return Option(a)

    @staticmethod
    def return_(a):
        return Option.return_(a)

    @staticmethod
    def wrapped_values():
        return [1, None]

    @staticmethod
    def unwrap(x):
        while isinstance(x, Option):
            x = x.get
        return x


class TestResult(MonadLawTester, unittest.TestCase):
    def assertEqual(self, a, b):
        return unittest.TestCase.assertEqual(self, a, b)

    @staticmethod
    def m(a):
        return Result(a)

    @staticmethod
    def return_(a):
        return Result.return_(a)

    @staticmethod
    def unwrap(x):
        while isinstance(x, Result):
            x = x.get
        return x

    @staticmethod
    def wrapped_values():
        return [1, AssertionError()]


class TestList(MonadLawTester, unittest.TestCase):
    def assertEqual(self, a, b):
        return unittest.TestCase.assertEqual(self, a, b)

    def f1(self, x):
        unwrapped = self.unwrap(x)
        assert isinstance(unwrapped, int)
        return List([unwrapped])

    def f2(self, x):
        unwrapped = self.unwrap(x)
        assert isinstance(unwrapped, int)
        return List([unwrapped * 2])

    @staticmethod
    def m(a):
        return List(a)

    @staticmethod
    def return_(a):
        return List.return_(a)

    @staticmethod
    def unwrap(x):
        while isinstance(x, List):
            x = x.get
        return x

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
        return IO(a)

    @staticmethod
    def return_(a):
        return IO.return_(a)

    @staticmethod
    def unwrap(x):
        while isinstance(x, IO):
            x = x.get
        return x()

    @staticmethod
    def wrapped_values():
        return [lambda: 1, lambda: 2]


if __name__ == "__main__":
    unittest.main()
