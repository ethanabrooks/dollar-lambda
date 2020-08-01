#! /usr/bin/env python
import abc
from functools import partial

from stateless_iterator import StatelessIterator


class Monad:
    @classmethod
    @abc.abstractmethod
    def bind(cls, x, f):
        raise NotImplementedError

    @classmethod
    def ret(cls, x):
        return x

    @classmethod
    def do(cls, it_func):
        def f(y, it):
            try:
                z, it2 = it.send(y)
            except StopIteration:
                return cls.ret(y)
            return cls.bind(z, partial(f, it=it2))

        return f(None, StatelessIterator(it_func))


class Option(Monad):
    @classmethod
    def bind(cls, x, f):
        if x is None:
            return None
        return f(x)


class Result(Monad):
    @classmethod
    def bind(cls, x, f):
        if type(x) is type and issubclass(x, Exception):
            return x
        return f(x)


class List(Monad):
    @classmethod
    def bind(cls, x, f):
        def g():
            for y in x:
                for z in f(y):
                    yield z

        return list(g())

    @classmethod
    def ret(cls, x):
        return [x]


class IO(Monad):
    @classmethod
    def bind(cls, x, f):
        return f(x())

    @classmethod
    def ret(cls, x):
        if x is not None:
            return x()

    @classmethod
    def do(cls, it_func):
        it = it_func()

        def f(y):
            try:
                z = it.send(y)
            except StopIteration:
                return cls.ret(y)
            return cls.bind(z, f)

        return f(None)


def options():
    x = yield 1
    y = yield 2
    yield x + y


def results():
    x = yield 1
    y = yield RuntimeError
    yield x + y


def lists():
    x = yield [1]
    y = yield [2, 3]
    yield [x + y]


def io():
    x = yield lambda: input("go:")
    y = yield lambda: input("go:")
    yield lambda: print(x + y)


if __name__ == "__main__":
    print(Option.do(options))
    print(Result.do(results))
    print(List.do(lists))
    IO().do(io)
