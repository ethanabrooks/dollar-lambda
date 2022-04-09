"""
Defines :py:class:`Sequence <dollar_lambda.data_structures.Sequence>`,
a strongly-typed immutable list that implements
`MonadPlus <https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monoid.py#L24>`_.
"""
from __future__ import annotations

import typing
from collections import UserList
from dataclasses import dataclass
from itertools import filterfalse, tee
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
from pytypeclass.nonempty_list import NonemptyList

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
A_monoid = TypeVar("A_monoid", bound=Monoid)
B_monoid = TypeVar("B_monoid", bound=Monoid)


class _Colliding(UserList[A]):
    pass


def _partition(pred, iterable):
    "Use a predicate to partition entries into false entries and true entries"
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)


@dataclass
class _TreePath(Generic[A]):
    parents: NonemptyList[str]
    leaf: A

    @classmethod
    def make(cls, head: str, *tail: str, leaf: A) -> _TreePath[A]:
        return cls(parents=NonemptyList.make(head, *tail), leaf=leaf)

    @classmethod
    def merge(cls, *paths: _TreePath[A]) -> Dict[str, "A | List[A]"]:
        """
        Merge a list of paths into a nested dictionary, handling collisions with
        `Sequence.to_dict` (which uses `Sequence.to_collision_dict`).

        >>> from dollar_lambda.data_structures import _TreePath
        >>> tp1 = _TreePath.make("a", leaf=1)
        >>> tp2 = _TreePath.make("b", leaf=2)
        >>> _TreePath.merge(tp1, tp2)
        {'a': 1, 'b': 2}
        >>> tp1 = _TreePath.make("a", leaf=1)
        >>> tp2 = _TreePath.make("a", leaf=2)
        >>> _TreePath.merge(tp1, tp2)
        {'a': [1, 2]}
        >>> tp1 = _TreePath.make("a", "b", leaf=1)
        >>> tp2 = _TreePath.make("a", "c", leaf=2)
        >>> _TreePath.merge(tp1, tp2)
        {'a': {'b': 1, 'c': 2}}
        >>> tp1 = _TreePath.make("a", "b", leaf=1)
        >>> tp2 = _TreePath.make("a", "b", leaf=2)
        >>> _TreePath.merge(tp1, tp2)
        {'a': {'b': [1, 2]}}
        >>> tp1 = _TreePath.make("a", "b", leaf=1)
        >>> tp2 = _TreePath.make("b", leaf=1)
        >>> _TreePath.merge(tp1, tp2)
        {'a': {'b': 1}, 'b': 1}
        >>> tp1 = _TreePath.make("a", "b", leaf=1)
        >>> tp2 = _TreePath.make("a", leaf=2)
        >>> _TreePath.merge(tp1, tp2)
        {'a': [2, {'b': 1}]}
        >>> tp1 = _TreePath.make("a", "b", leaf=1)
        >>> tp2 = _TreePath.make("a", leaf="b")
        >>> _TreePath.merge(tp1, tp2)
        {'a': ['b', {'b': 1}]}
        >>> tp1 = _TreePath.make("a", "b", leaf=1)
        >>> tp2 = _TreePath.make("a", "b", leaf=2)
        >>> tp3 = _TreePath.make("a", leaf=2)
        >>> _TreePath.merge(tp1, tp2, tp3)
        {'a': [2, {'b': [1, 2]}]}
        """

        def get_seq():
            for path in paths:
                tail = path.parents.tail
                if tail:
                    tail2 = tail.tail if tail.tail else []
                    v = _TreePath.make(tail.head, *tail2, leaf=path.leaf)
                else:
                    v = path.leaf
                yield KeyValue(path.parents.head, v)

        return Sequence(list(get_seq())).to_dict()


@dataclass
class KeyValue(Generic[A_co]):
    """
    Simple dataclass for storing key-value pairs.
    """

    key: str
    value: A_co


@dataclass
class Sequence(MonadPlus[A_co], typing.Sequence[A_co]):
    """
    This class combines the functionality of `MonadPlus <https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monoid.py#L24>`_
    and :external:py:class:`typing.Sequence`

    >>> from dollar_lambda.data_structures import Sequence
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
    def return_(a: A) -> "Sequence[A]":  # type: ignore[override]
        """
        >>> Sequence.return_(1)
        Sequence(get=[1])
        """
        return Sequence([a])

    def to_colliding_dict(
        self: "Sequence[KeyValue[A]]",
    ) -> "Dict[str, A | _Colliding[A]]":
        """
        >>> from dollar_lambda import Sequence, KeyValue
        >>> Sequence([KeyValue("a", 1), KeyValue("b", 2), KeyValue("a", 3)]).to_colliding_dict()
        {'a': [1, 3], 'b': 2}
        >>> Sequence([KeyValue("a", [1]), KeyValue("b", 2), KeyValue("a", [3])]).to_colliding_dict()
        {'a': [[1], [3]], 'b': 2}
        """
        d: Dict[str, "A | _Colliding[A]"] = {}
        for kv in self:
            if kv.key in d:
                v = d[kv.key]
                if isinstance(v, _Colliding):
                    v.append(kv.value)
                else:
                    d[kv.key] = _Colliding([v, kv.value])
            else:
                d[kv.key] = kv.value
        return d

    def to_dict(self: "Sequence[KeyValue[A]]") -> "Dict[str, A | List[A]]":
        """
        >>> from dollar_lambda import Sequence, KeyValue
        >>> Sequence([KeyValue("a", 1), KeyValue("b", 2), KeyValue("a", 3)]).to_dict()
        {'a': [1, 3], 'b': 2}
        >>> from dollar_lambda import Sequence, KeyValue
        >>> Sequence([KeyValue("a", [1]), KeyValue("b", 2), KeyValue("a", [3])]).to_dict()
        {'a': [[1], [3]], 'b': 2}
        >>> from dollar_lambda.data_structures import _TreePath
        >>> Sequence([KeyValue("a", _TreePath.make("b", leaf="c"))]).to_dict()
        {'a': {'b': 'c'}}
        >>> Sequence(
        ...     [
        ...         KeyValue("a", "b"),
        ...         KeyValue("a", _TreePath.make("b", leaf="c")),
        ...         KeyValue("a", _TreePath.make("b", "c", leaf=1)),
        ...         KeyValue("a", _TreePath.make("b", "c", leaf=2)),
        ...     ]
        ... ).to_dict()
        {'a': ['b', {'b': ['c', {'c': [1, 2]}]}]}
        """

        def get_dict():
            for k, v in self.to_colliding_dict().items():
                if isinstance(v, _Colliding):
                    other, paths = _partition(lambda x: isinstance(x, _TreePath), v)
                    other = list(other)
                    merged = _TreePath.merge(*paths)
                    if merged and other:
                        yield k, [*other, merged]
                    elif other:
                        yield k, other
                    elif merged:
                        yield k, merged
                else:
                    if isinstance(v, _TreePath):
                        yield k, _TreePath.merge(v)
                    else:
                        yield k, v

        return dict(get_dict())

    def values(self: "Sequence[KeyValue[A]]") -> "Sequence[A]":
        return Sequence([kv.value for kv in self])

    @classmethod
    def zero(cls: Type["Sequence[A_co]"]) -> "Sequence[A_co]":
        return Sequence([])


A_co_monoid = TypeVar("A_co_monoid", covariant=True, bound=Monoid)


@dataclass
class Output(Monoid[A_co_monoid]):
    """
    This is the wrapper class for the output of :py:class:`Parser<dollar_lambda.parsers.Parser>`.
    """

    get: A_co_monoid

    def __or__(  # type: ignore[override]
        self: Output[A_monoid], other: Output[B_monoid]
    ) -> Output["A_monoid | B_monoid"]:
        c = cast("A_monoid | B_monoid", self.get | other.get)
        # cast is necessary because the type-system thinks that c has type Monoid[Unknown]
        return Output(c)

    def __add__(  # type: ignore[override]
        self: Output[A_monoid], other: Output[B_monoid]
    ) -> Output["A_monoid | B_monoid"]:
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
