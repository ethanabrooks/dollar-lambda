from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Callable, Generator, TypeVar

from monad_argparse.monad.monad import Monad

A = TypeVar("A", covariant=True)
B = TypeVar("B")
C = TypeVar("C", contravariant=True)


@dataclass
class List(Monad[A]):
    """
    >>> def lists():
    ...     x = yield List([])
    ...     y = yield List([2, 3])
    ...     yield List([x + y])
    ...
    >>> List.do(lists)
    List([])
    >>> def lists():
    ...     x = yield List([1])
    ...     y = yield List([2, 3])
    ...     yield List([x + y])
    ...
    >>> List.do(lists)
    List([3, 4])
    >>> def lists():
    ...     x = yield List([1, 2])
    ...     y = yield List([2, 3])
    ...     yield List([x + y])
    ...
    >>> List.do(lists)
    List([3, 4, 4, 5])
    """

    get: typing.List[A]

    def __iter__(self):
        yield from self.get

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.get)})"

    def bind(  # type: ignore[override]
        self: List[A], f: Callable[[A], List[B]]
    ) -> List[B]:
        def g() -> Generator[B, None, None]:
            for y in self:
                yield from f(y)

        return List(list(g()))

    @classmethod
    def return_(cls, a: C) -> List[C]:
        return List([a])


class L(List[A]):
    pass
