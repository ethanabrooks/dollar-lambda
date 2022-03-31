"""
Defines `Sequence`, a strongly-typed immutable list that implements `MonadPlus`.
"""
from __future__ import annotations

import operator
import typing
from collections import UserDict
from copy import copy
from dataclasses import dataclass
from functools import reduce
from typing import (
    Callable,
    Generator,
    Iterator,
    Tuple,
    Type,
    TypeAlias,
    TypeVar,
    overload,
)

from pytypeclass import Monad, MonadPlus
from pytypeclass.monad import C
from pytypeclass.monoid import B

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


Key: TypeAlias = "str | int"
Value: TypeAlias = "A_co | CollisionDict[A_co]"


class CollisionDict(MonadPlus[A_co], UserDict[Key, Value]):
    """
    >>> d = CollisionDict[int]({})
    >>> d = d.set("a", 1)
    >>> d
    {'a': 1}
    >>> d = d.set("a", 2)
    >>> d
    {'a': {0: 1, 1: 2}}
    >>> d = d.set("a", d)
    >>> d
    {'a': {0: 1, 1: 2, 'a': {0: 1, 1: 2}}}
    >>> d.to_json()
    {'a': [1, 2, {'a': [1, 2]}]}
    """

    def bind(  # type: ignore[override]
        self: "CollisionDict[B]",
        f: Callable[[Tuple[Key, UserDict[Key, Value]]], "CollisionDict[C]"],
    ) -> "CollisionDict[C]":
        return reduce(operator.add, [f((k, v)) for k, v in self.items()])

    @classmethod
    def return_(  # type: ignore[override]
        cls: Type[CollisionDict[A]], a: Tuple[Key, UserDict[str, A]]
    ) -> CollisionDict[A]:
        return CollisionDict(dict([a]))

    def __add__(
        self: CollisionDict[A], other: CollisionDict[B]
    ) -> CollisionDict[A | B]:
        cd = copy(self)
        for k, v in other.items():
            if k in cd:
                if isinstance(cd[k], CollisionDict):
                    if isinstance(v, CollisionDict):
                        _v = v
                    else:
                        _v = CollisionDict({len(cd): v})
                        assert len(cd) not in cd[k]
                    cd[k] = cd[k] + _v  # recurse
                else:
                    cd[k] = CollisionDict({0: cd[k], 1: v})
            else:
                cd[k] = v
        return cd

    def __or__(self: CollisionDict[A], other: CollisionDict[B]) -> CollisionDict[A | B]:  # type: ignore[override]
        return self + other

    def set(self, key: str, value: Value[A_co]) -> "CollisionDict[A_co]":
        assert isinstance(key, str)
        return self + CollisionDict({key: value})

    def to_json(self):
        cd = {
            k: v.to_json() if isinstance(v, CollisionDict) else v
            for k, v in self.items()
        }
        int_keys = [(k, v) for k, v in cd.items() if isinstance(k, int)]
        int_keys = [v for k, v in sorted(int_keys)]
        str_keys = {k: v for k, v in cd.items() if isinstance(k, str)}
        if int_keys and str_keys:
            return [*int_keys, str_keys]
        elif int_keys:
            return int_keys
        else:
            return str_keys

    @classmethod
    def zero(cls: Type[CollisionDict[A]]) -> CollisionDict[A]:
        return CollisionDict({})
