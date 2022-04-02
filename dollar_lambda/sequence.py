"""
Defines `Sequence`, a strongly-typed immutable list that implements `MonadPlus`.
"""
from __future__ import annotations

import typing
from collections import UserList
from dataclasses import dataclass
from typing import (
    Callable,
    Dict,
    Generator,
    Generic,
    Iterator,
    List,
    Optional,
    Type,
    TypeVar,
    cast,
    overload,
)

from pytypeclass import Monad, MonadPlus
from pytypeclass.monoid import Monoid

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
A_monoid = TypeVar("A_monoid", bound=Monoid)
B_monoid = TypeVar("B_monoid", bound=Monoid)


class Array(UserList[A]):
    pass


@dataclass
class KeyValue(Generic[A_co]):
    key: str
    value: A_co


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

    @classmethod
    def from_dict(
        cls: Type[Sequence[KeyValue[A]]], **kwargs
    ) -> "Sequence[KeyValue[A]]":
        return Sequence([KeyValue(k, v) for k, v in kwargs.items()])

    def keys(self: "Sequence[KeyValue[A]]") -> "Sequence[str]":
        return Sequence([kv.key for kv in self])

    @staticmethod
    def return_(a: A) -> "Sequence[A]":
        """
        >>> Sequence.return_(1)
        Sequence(get=[1])
        """
        return Sequence([a])

    def to_dict(self: "Sequence[KeyValue[A]]") -> "Dict[str, A | List[A]]":
        d: Dict[str, "A | Array[A]"] = {}
        for kv in self:
            if kv.key in d:
                v = d[kv.key]
                if isinstance(v, Array):
                    v.append(kv.value)
                else:
                    d[kv.key] = Array([v, kv.value])
            else:
                d[kv.key] = kv.value
        return {k: list(v) if isinstance(v, Array) else v for k, v in d.items()}

    def values(self: "Sequence[KeyValue[A]]") -> "Sequence[A]":
        return Sequence([kv.value for kv in self])

    @classmethod
    def zero(cls: Type["Sequence[A_co]"]) -> "Sequence[A_co]":
        return Sequence([])


A_co_monoid = TypeVar("A_co_monoid", covariant=True, bound=Monoid)


@dataclass
class Output(Monoid[A_co_monoid]):
    get: A_co_monoid

    def __or__(  # type: ignore[override]
        self: Output[A_monoid], other: Output[B_monoid]
    ) -> Output[A_monoid | B_monoid]:
        c = cast(A_monoid | B_monoid, self.get | other.get)
        # cast is necessary because the type-system thinks that c has type Monoid[Unknown]
        return Output(c)

    def __add__(  # type: ignore[override]
        self: Output[A_monoid], other: Output[B_monoid]
    ) -> Output[A_monoid | B_monoid]:
        return self | other

    @classmethod
    def from_dict(
        cls: Type[Output[Sequence[KeyValue[A]]]], **kwargs
    ) -> "Output[Sequence[KeyValue[A]]]":
        return Output[Sequence[KeyValue[A]]](Sequence[KeyValue[A]].from_dict(**kwargs))

    @classmethod
    def zero(
        cls: Type[Output[A_monoid]], a: Optional[Type[A_monoid]] = None
    ) -> Output[A_monoid]:
        zero = cast(A_monoid, Sequence.zero() if a is None else a.zero())
        # This will break the type-system if a is not provided and A_monoid is not a Sequence.
        # A bit of a hack to get around the lack of higher-kinded types in Python.
        return Output(zero)
