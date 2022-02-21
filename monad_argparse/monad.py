import abc
import typing
from abc import ABC
from functools import partial
from typing import Any, Callable, Generator, Generic, Optional, TypeVar, Union, cast

from monad_argparse.stateless_iterator import StatelessIterator

A = TypeVar("A")
B = TypeVar("B", covariant=True)
MA = TypeVar("MA", contravariant=True)
MB = TypeVar("MB", covariant=True)
C = TypeVar("C", bound="M")


class M(ABC, Generic[A]):
    def __init__(self, a):
        self.a: A = self.unwrap(a)

    @abc.abstractmethod
    def __ge__(self, f: Callable[[A], Any]):
        raise NotImplementedError

    def __eq__(self, other):
        return self.a == other

    def __repr__(self) -> str:
        return f"M {self.unwrap(self)}"

    @classmethod
    def return_(cls, a: A):
        raise NotImplementedError

    @classmethod
    def unwrap(cls: typing.Type[C], x: Union[C, A]) -> A:
        if isinstance(x, M):
            return cls.unwrap(x.a)
        return cast(A, x)


class Monad(Generic[A, MA, MB]):
    """
    Monad laws:
    ```haskell
    return a >>= f = f a
    p >>= return = p
    p >>= (\\a -> (f a >>= g)) = (p >>= (\\a -> f a)) >>= g
    ```
    """

    @classmethod
    @abc.abstractmethod
    def bind(cls, x: MA, f: Callable[[A], MB]) -> MB:
        """
        ```haskell
        (>>=) :: m a -> (a -> m b) -> m b
        ```
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
        ```haskell
        return :: a -> m a
        ```
        """
        raise NotImplementedError


class BaseMonad(Monad[A, MA, Union[A, MB]], ABC):
    @classmethod
    def return_(cls, a: A) -> Union[A, MB]:
        return a
