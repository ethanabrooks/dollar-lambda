"""
Results represent either success or failure (an exception). This is how errors get bubbled up during the parsing process.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type, TypeVar

from pytypeclass import MonadPlus, Monoid

from monad_argparse.error import ZeroError

A = TypeVar("A", covariant=True, bound=Monoid)
B = TypeVar("B", bound=Monoid)


@dataclass
class Result(MonadPlus[A]):
    get: A | Exception

    def __or__(self, other: Result[B]) -> Result[A | B]:
        if not isinstance(self.get, Exception):
            return self
        if not isinstance(other.get, Exception):
            return other
        return self

    def bind(self, f: Callable[[A], Result[B]]) -> Result[B]:
        y = self.get
        if isinstance(y, Exception):
            return Result(y)
        return f(y)

    @classmethod
    def return_(cls: "Type[Result[A]]", a: B) -> "Result[B]":
        return Result(a)

    @classmethod
    def zero(cls: "Type[Result[A]]") -> "Result[A]":
        return Result(ZeroError())
