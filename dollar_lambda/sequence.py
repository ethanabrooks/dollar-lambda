"""
Defines `Sequence`, a strongly-typed immutable list that implements `MonadPlus`.
"""
from __future__ import annotations

import typing
from collections import UserDict, UserList
from copy import copy
from dataclasses import astuple, dataclass
from typing import (
    Callable,
    Dict,
    Generator,
    Generic,
    Iterator,
    Optional,
    Tuple,
    Type,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

from pytypeclass import Monad, MonadPlus
from pytypeclass.monad import C
from pytypeclass.monoid import B, Monoid
from pytypeclass.nonempty_list import NonemptyList

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

    def to_dict(self: "Sequence[KeyValue[A]]") -> "Dict[str, A | Array[A]]":
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
        return d

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
        return Output(zero)


Key: TypeAlias = "str | int"
Value: TypeAlias = "A_co | Tree[A_co]"


class Tree(Monoid[A_co], UserDict[Key, Value]):
    """
    >>> d = Tree[int]({})
    >>> d = d + Tree({"a": 1})
    >>> d
    {'a': 1}
    >>> d = d + Tree({"a": 2})
    >>> d
    {'a': {0: 1, 1: 2}}
    >>> d = d + Tree({"a": d})
    >>> d
    {'a': {0: 1, 1: 2, 'a': {0: 1, 1: 2}}}
    >>> d.to_json()
    {'a': [1, 2, {'a': [1, 2]}]}
    """

    def bind(  # type: ignore[override]
        self: "Tree[B]",
        f: Callable[[Tuple[Sequence[Key], B]], "Tree[C]"],
    ) -> "Tree[C]":
        raise NotImplementedError

    @classmethod
    def return_(  # type: ignore[override]
        cls: Type[Tree[A]], a: Tuple[Key, UserDict[str, A]]
    ) -> Tree[A]:
        raise NotImplementedError
        # return Tree(dict([a]))

    def __add__(self: Tree[A], other: Tree[B]) -> Tree[A | B]:
        cd = copy(self)
        for k, v in other.items():
            if k in cd:
                inner = cd[k]
                if isinstance(inner, Tree):
                    if isinstance(v, Tree):
                        _v = v
                    else:
                        _v = Tree({len(cd): v})
                        assert len(cd) not in inner
                    cd[k] = inner + _v  # recurse
                else:
                    cd[k] = Tree({0: cd[k], 1: v})
            else:
                cd[k] = v
        return cd

    def __or__(self: Tree[A], other: Tree[B]) -> Tree[A | B]:  # type: ignore[override]
        return self + other

    @classmethod
    def from_path(cls: Type["Tree[A]"], path: NonemptyList[Key], leaf: A) -> "Tree[A]":
        head, tail = astuple(path)
        if tail:
            return Tree({head: cls.from_path(tail, leaf)})
        else:
            return Tree({head: leaf})

    def last_leaf(self) -> "A_co | None":
        if not self:
            return None
        *_, (_, v) = super().items()
        return v.last_leaf() if isinstance(v, Tree) else v

    def path_to_last_leaf(self) -> "Sequence[Key]":
        if not self:
            return Sequence([])
        *_, (k, v) = super().items()
        if isinstance(v, Tree):
            return Sequence([k, *v.path_to_last_leaf()])
        else:
            return Sequence([k])

    def set(self, other: "Tree[A_co]") -> "Tree[A_co]":
        cd = copy(self)
        for k, v in other.items():
            if k in cd:
                inner = cd[k]
                if isinstance(v, Tree) and isinstance(inner, Tree):
                    cd[k] = inner.set(v)  # recurse
                else:
                    # clobber the existing value
                    cd[k] = v
            else:
                # k is a new key so just add to cd
                cd[k] = v
        return cd

    def to_json(self):
        cd = {k: v.to_json() if isinstance(v, Tree) else v for k, v in super().items()}
        int_keys = [(k, v) for k, v in cd.items() if isinstance(k, int)]
        int_keys = [v for k, v in sorted(int_keys)]
        str_keys = {k: v for k, v in cd.items() if isinstance(k, str)}
        if int_keys and str_keys:
            return [*int_keys, str_keys]
        elif int_keys:
            return int_keys
        else:
            return str_keys

    def leaves(self) -> "Iterator[A_co]":
        if not self:
            return
        for v in super().values():
            if isinstance(v, Tree):
                yield from v.leaves()
            else:
                yield v

    @classmethod
    def zero(cls: Type[Tree[A]]) -> Tree[A]:
        return Tree({})
