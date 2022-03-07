"""
Results represent either success or failure (an exception). This is how errors get bubbled up during the parsing process.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Callable, Optional, Type, TypeVar

from pytypeclass import MonadPlus, Monoid
from pytypeclass.nonempty_list import NonemptyList

from monad_argparse.error import ArgumentError, ZeroError
from monad_argparse.sequence import Sequence

A = TypeVar("A", covariant=True, bound=Monoid)
B = TypeVar("B", bound=Monoid)
C = TypeVar("C")
D = TypeVar("D")


@dataclass
class Result(MonadPlus[A]):
    get: NonemptyList[A] | ArgumentError

    def __or__(self, other: Result[B]) -> Result[A | B]:
        a = self.get
        b = other.get
        if isinstance(a, NonemptyList) and isinstance(b, NonemptyList):
            return Result(a + b)
        if isinstance(b, ArgumentError):
            return self
        if isinstance(a, ArgumentError):
            return other
        raise RuntimeError("unreachable")

    def __rshift__(
        self: Result[Sequence[C]], other: Result[Sequence[D]]
    ) -> Result[Result[Sequence[C | D]]]:
        """
        Sequence cs >> ds for each (cs, ds) in self.get * other.get.
        Short circuit at Exceptions.
        """
        return self >= (lambda cs: other >= (lambda ds: Result(NonemptyList(cs + ds))))

    def bind(self, f: Callable[[A], Result[B]]) -> Result[B]:
        x = self.get
        if isinstance(x, ArgumentError):
            return Result(x)
        else:

            def g(acc: Result[B], new: A) -> Result[B]:  # type: ignore[misc]
                y = f(new)
                a = acc.get
                b = y.get

                if isinstance(a, NonemptyList) and isinstance(b, NonemptyList):
                    return Result(a + b)

                return next(
                    (x for x in (acc, y) if isinstance(x.get, NonemptyList)),
                    acc,
                )

            tail = [] if x.tail is None else list(x.tail)
            return reduce(g, tail, f(x.head))

    @classmethod
    def return_(cls: "Type[Result[A]]", a: B) -> "Result[B]":
        return Result(NonemptyList(a))

    @classmethod
    def zero(
        cls: "Type[Result[A]]", error: Optional[ArgumentError] = None
    ) -> "Result[A]":
        return Result(ZeroError("zero") if error is None else error)
