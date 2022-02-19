#! /usr/bin/env python
import abc
import typing
from abc import ABC
from functools import partial
from typing import (
    Any,
    Callable,
    Generator,
    Generic,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from monad_argparse.stateless_iterator import A, B, StatelessIterator

MA = TypeVar("MA")
MB = TypeVar("MB")


class Monad(Generic[A, MA, MB]):
    @classmethod
    @abc.abstractmethod
    def bind(cls, x: MA, f: Callable[[A], MB]) -> MB:
        raise NotImplementedError

    @classmethod
    def do(
        cls,
        generator: Callable[[], Generator[A, Any, None]],
        *args,
        **kwargs,
    ):
        def f(y: Optional[A], it: StatelessIterator) -> MB:
            try:
                z, it2 = it.send(y)
            except StopIteration:
                if y is None:
                    raise RuntimeError("Cannot use an empty iterator with do.")
                return cls.ret(y)
            return cls.bind(z, partial(f, it=it2))

        def gen() -> Generator[A, Tuple[Any, StatelessIterator], None]:
            return generator(*args, **kwargs)

        return f(None, StatelessIterator(gen))

    @classmethod
    @abc.abstractmethod
    def ret(cls, x: A) -> MB:
        raise NotImplementedError


class BaseMonad(Monad[A, MA, Union[A, MB]], ABC):
    @classmethod
    def ret(cls, x: A) -> Union[A, MB]:
        return x


class Option(BaseMonad[A, Optional[A], Optional[B]]):
    @classmethod
    def bind(  # type: ignore[override]
        cls,
        x: Optional[A],
        f: Callable[[A], Optional[B]],
    ) -> Optional[B]:
        if x is None:
            return None
        return f(x)


class Result(BaseMonad[A, Union[A, Type[Exception]], Union[A, Type[Exception]]]):
    @classmethod
    def bind(  # type: ignore[override]
        cls,
        x: Union[A, Type[Exception]],
        f: Callable[[A], Type[Exception]],
    ) -> Union[A, Type[Exception]]:
        if type(x) is type and issubclass(x, Exception):
            return x
        y = f(x)  # type: ignore[arg-type]
        return y


class List(BaseMonad[A, typing.List[A], Union[typing.List[A], typing.List[B]]]):
    @classmethod
    def bind(  # type: ignore[override]
        cls, x: typing.List[A], f: Callable[[A], typing.List[B]]
    ) -> typing.List[B]:
        def g() -> Generator[B, None, None]:
            for y in x:
                for z in f(y):
                    yield z

        return list(g())

    @classmethod
    def ret(cls, x: A) -> Union[typing.List[A], typing.List[B]]:
        return [x]


class IO(BaseMonad[A, Callable[[], A], MB]):
    @classmethod
    def bind(cls, x: Callable[[], A], f: Callable[[A], None]) -> None:  # type: ignore[override]
        return f(x())

    @classmethod
    def do(  # type: ignore[override]
        cls,
        generator: Callable[[Any], Generator[Callable[[], A], Optional[A], None]],
        *args,
        **kwargs,
    ):
        it = generator(*args, **kwargs)

        def f(y: Optional[A]) -> None:
            try:
                z = it.send(y)
            except StopIteration:
                return None

            return cls.bind(z, f)

        return f(None)

    @classmethod
    def ret(cls, x):
        raise RuntimeError("IO does not use ret method.")


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
    x = yield lambda: print("1") or 1
    y = yield lambda: print("2") or 2
    yield lambda: print(x + y)


#
#
# if __name__ == "__main__":
#     print(Option.do(options))
#     print(Result.do(results))
#     print(List.do(lists))
#     IO().do(io)
