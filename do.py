#! /usr/bin/env python
import abc


class Monad:
    @abc.abstractmethod
    def bind(self, x, f):
        raise NotImplementedError

    def ret(self, x):
        return x

    def do(self, it):
        def _do(y):
            try:
                z = it.send(y)
            except StopIteration:
                return self.ret(y)
            return self.bind(z, _do)

        return _do(None)


class Option(Monad):
    def bind(self, x, f):
        if x is None:
            return None
        return f(x)


class Result(Monad):
    def bind(self, x, f):
        if type(x) is type and issubclass(x, Exception):
            return x
        return f(x)


class List(Monad):
    def bind(self, x, f):
        def g():
            for y in x:
                for z in f(y):
                    yield z

        return list(g())

    def ret(self, x):
        return [x]


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


print(Option().do(options()))
print(Result().do(results()))
print(List().do(lists()))
