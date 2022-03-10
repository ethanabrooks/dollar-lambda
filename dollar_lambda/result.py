"""
Results represent either success or failure (an exception). This is how errors get bubbled up during the parsing process.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import Callable, Optional, Type, TypeVar

from pytypeclass import MonadPlus, Monoid
from pytypeclass.nonempty_list import NonemptyList

from dollar_lambda.error import ArgumentError, ZeroError
from dollar_lambda.sequence import Sequence

Monoid_co = TypeVar("Monoid_co", covariant=True, bound=Monoid)
Monoid1 = TypeVar("Monoid1", bound=Monoid)
A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")


@dataclass
class Result(MonadPlus[A_co]):
    get: NonemptyList[A_co] | ArgumentError

    def __or__(self, other: Result[B]) -> Result[A_co | B]:
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
        self: Result[Sequence[A]], other: Result[Sequence[B]]
    ) -> Result[Result[Sequence[A | B]]]:
        """
        Sequence cs >> ds for each (cs, ds) in self.get * other.get.
        Short circuit at Exceptions.
        """
        return self >= (lambda cs: other >= (lambda ds: Result(NonemptyList(cs + ds))))

    def bind(self, f: Callable[[A_co], Result[B]]) -> Result[B]:
        x = self.get
        if isinstance(x, ArgumentError):
            return Result(x)
        else:

            def g(acc: Result[B], new: A_co) -> Result[B]:  # type: ignore[misc]
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
    def return_(cls: "Type[Result[A]]", a: A) -> "Result[A]":
        return Result(NonemptyList(a))

    @classmethod
    def zero(
        cls: "Type[Result[Monoid_co]]", error: Optional[ArgumentError] = None
    ) -> "Result[Monoid_co]":
        return Result(ZeroError("zero") if error is None else error)
