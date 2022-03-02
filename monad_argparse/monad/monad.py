from __future__ import annotations

import abc
from functools import partial
from typing import Callable, Generator, Optional, Protocol, Type, TypeVar

from monad_argparse.monad.stateless_iterator import StatelessIterator

A = TypeVar("A")
B = TypeVar("B", bound="Monad")
C = TypeVar("C", contravariant=True)
D = TypeVar("D", bound="Monad")


class Monad(Protocol[A]):
    """
    Monad laws:
    ```haskell
    return a >>= f = f a
    p >>= return = p
    p >>= (\\a -> (f a >>= g)) = (p >>= (\\a -> f a)) >>= g
    ```
    """

    def __ge__(self, f):
        return self.bind(f)

    @abc.abstractmethod
    def bind(self: B, f: Callable[[A], B]) -> B:
        ...
        """
        ```haskell
        (>>=) :: m a -> (a -> m b) -> m b
        ```
        """
        raise NotImplementedError

    @classmethod
    def do(
        cls: Type[D],
        generator: Callable[[], Generator[D, B, None]],
    ) -> D:
        def f(a: Optional[B], it: StatelessIterator[D, B]) -> D:
            try:
                it2: StatelessIterator[D, B]
                if a is None:
                    ma, it2 = it.__next__()
                else:
                    ma, it2 = it.send(a)
            except StopIteration:
                if a is None:
                    raise RuntimeError("Cannot use an empty iterator with do.")
                return cls.return_(a)
            return ma.bind(partial(f, it=it2))

        return f(None, StatelessIterator(generator))

    @classmethod
    @abc.abstractmethod
    def return_(cls: Type[D], a: A) -> D:  # type: ignore[misc]
        # see https://github.com/python/mypy/issues/6178#issuecomment-1057111790
        """
        ```haskell
        return :: a -> m a
        ```
        """
        raise NotImplementedError
