"""
Defines `Sequence`, a strongly-typed immutable list that implements `MonadPlus`.
"""
import typing
from dataclasses import dataclass
from typing import Callable, Generator, Iterator, Type, TypeVar, overload

from pytypeclass import Monad, MonadPlus

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")


@dataclass
class Sequence(MonadPlus[A_co], typing.Sequence[A_co]):
    """
    This class combines the functionality of [`MonadPlus`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monoid.py#L24)
    and [`typing.Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence).

    >>> s = Sequence([1, 2])
    >>> len(s)
    2
    >>> s[0]
    1
    >>> s[-1]
    2
    >>> s + s  # sequences emulate list behavior when added
    Sequence(get=[1, 2, 1, 2])
    >>> [x + 1 for x in s]  # sequences can be iterated over
    [2, 3]
    >>> Sequence([1, 2]) >= (lambda x: Sequence([x, -x]))
    Sequence(get=[1, -1, 2, -2])
    """

    get: typing.Sequence[A_co]

    @overload
    def __getitem__(self, i: int) -> "A_co":
        ...

    @overload
    def __getitem__(self, i: slice) -> "Sequence[A_co]":
        ...

    def __getitem__(self, i: "int | slice") -> "A_co | Sequence[A_co]":
        if isinstance(i, int):
            return self.get[i]
        return Sequence(self.get[i])

    def __iter__(self) -> Generator[A_co, None, None]:
        yield from self.get

    def __len__(self) -> int:
        return len(self.get)

    def __or__(self, other: "Sequence[A]") -> "Sequence[A_co | A]":  # type: ignore[override]
        return Sequence([*self, *other])

    def __add__(self, other: "Sequence[A]") -> "Sequence[A_co | A]":
        return self | other

    def bind(self, f: Callable[[A_co], Monad[A]]) -> "Sequence[A]":
        """
        >>> Sequence([1, 2]) >= (lambda x: Sequence([x, -x]))
        Sequence(get=[1, -1, 2, -2])
        """

        def g() -> Iterator[A]:
            for a in self:
                y = f(a)
                assert isinstance(y, Sequence), y
                yield from y

        return Sequence(list(g()))

    @staticmethod
    def return_(a: A) -> "Sequence[A]":
        """
        >>> Sequence.return_(1)
        Sequence(get=[1])
        """
        return Sequence([a])

    @classmethod
    def zero(cls: Type["Sequence[A_co]"]) -> "Sequence[A_co]":
        return Sequence([])
