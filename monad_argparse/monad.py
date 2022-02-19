#! /usr/bin/env python
import abc
import typing
from abc import ABC
from functools import partial
from typing import Callable, Generator, Generic, Optional, TypeVar, Union

from monad_argparse.stateless_iterator import StatelessIterator

A = TypeVar("A", contravariant=True)
B = TypeVar("B", covariant=True)
MA = TypeVar("MA", contravariant=True)
MB = TypeVar("MB", covariant=True)
C = TypeVar("C", bound="M")


class M(ABC, Generic[A]):
    def __init__(self, a: A):
        self.a = self.unwrap(a)

    @abc.abstractmethod
    def __ge__(self, f: Callable[[A], MB]):
        raise NotImplementedError

    def __eq__(self, other):
        return self.a == other

    def __repr__(self) -> str:
        return f"M {self.unwrap(self)}"

    @classmethod
    def return_(cls, a: A):
        raise NotImplementedError

    @classmethod
    def unwrap(cls: typing.Type[C], x: Union[C, A]):
        while isinstance(x, cls):
            x = x.a
        return x


class Monad(Generic[A, MA, MB]):
    """
    Monad laws
    return a >>= f = f a
    p >>= return = p
    p >>= (\a -> (f a >>= g)) = (p >>= (\a -> f a)) >>= g
    """

    @classmethod
    @abc.abstractmethod
    def bind(cls, x: MA, f: Callable[[A], MB]) -> MB:
        """
        (>>=) :: m a -> (a -> m b) -> m b
        """
        raise NotImplementedError

    @classmethod
    def do(cls, generator: Callable[[], Generator[MA, A, None]]):
        def f(a: Optional[A], it: StatelessIterator[MA, A]) -> MB:
            try:
                ma: MA
                it2: StatelessIterator[MA, A]
                if a is None:
                    ma, it2 = it.__next__()
                else:
                    ma, it2 = it.send(a)
            except StopIteration:
                if a is None:
                    raise RuntimeError("Cannot use an empty iterator with do.")
                return cls.return_(a)
            return cls.bind(ma, partial(f, it=it2))

        return f(None, StatelessIterator(generator))

    @classmethod
    @abc.abstractmethod
    def return_(cls, a: A) -> MB:
        """
        return :: a -> m a
        """
        raise NotImplementedError


class BaseMonad(Monad[A, MA, Union[A, MB]], ABC):
    @classmethod
    def return_(cls, a: A) -> Union[A, MB]:
        return a
