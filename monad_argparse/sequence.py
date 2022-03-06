"""
A `Sequence` is a strongly-typed immutable list that implements `MonadPlus`.
"""
from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Callable, Generator, Iterator, Type, TypeVar, overload

from pytypeclass import MonadPlus

A = TypeVar("A", covariant=True)
B = TypeVar("B")


@dataclass
class Sequence(MonadPlus[A], typing.Sequence[A]):
    """
    >>> s = Sequence([1, 2])
    >>> len(s)
    2
    >>> s[0]
    1
    >>> s[-1]
    2
    >>> s + s
    Sequence(get=[1, 2, 1, 2])
    >>> [x + 1 for x in s]
    [2, 3]
    >>> Sequence([1, 2]) >= (lambda x: Sequence([x, -x]))
    Sequence(get=[1, -1, 2, -2])
    """

    get: typing.Sequence[A]

    @overload
    def __getitem__(self, i: int) -> "A":
        ...

    @overload
    def __getitem__(self, i: slice) -> Sequence[A]:
        ...

    def __getitem__(self, i: int | slice) -> A | Sequence[A]:
        if isinstance(i, int):
            return self.get[i]
        return Sequence(self.get[i])

    def __iter__(self) -> Generator[A, None, None]:
        yield from self.get

    def __len__(self) -> int:
        return len(self.get)

    def __or__(self, other: Sequence[B]) -> Sequence[A | B]:
        return Sequence([*self, *other])

    def __add__(self, other: Sequence[B]) -> Sequence[A | B]:
        return self | other

    def bind(self, f: Callable[[A], Sequence[B]]) -> Sequence[B]:
        def g() -> Iterator[B]:
            for a in self:
                yield from f(a)

        return Sequence(list(g()))

    @staticmethod
    def return_(a: B) -> Sequence[B]:
        return Sequence([a])

    @classmethod
    def zero(cls: Type[Sequence[A]]) -> Sequence[A]:
        return Sequence([])