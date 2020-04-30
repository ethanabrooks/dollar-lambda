#! /usr/bin/env python
import abc


class Monad:
    @abc.abstractmethod
    def bind(self, x, f):
        raise NotImplementedError

    def ret(x):
        return x

    def do(self, it):
        def _do(y):
            try:
                z = it.send(y)
            except StopIteration:
                return y
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


def options():
    x = yield 1
    y = yield 2
    yield x + y


def results():
    x = yield 1
    y = yield RuntimeError
    yield x + y


print(Option().do(options()))
print(Result().do(results()))
