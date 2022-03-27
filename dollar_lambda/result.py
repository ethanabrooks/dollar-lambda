"""
Defines the `Result` dataclass, representing success or failure, output by parsers.
"""
from dataclasses import dataclass
from functools import reduce
from typing import Callable, Optional, Type, TypeVar

from pytypeclass import Monad, MonadPlus, Monoid
from pytypeclass.nonempty_list import NonemptyList

from dollar_lambda.error import ArgumentError, HelpError, ZeroError
from dollar_lambda.sequence import Sequence

Monoid_co = TypeVar("Monoid_co", covariant=True, bound=Monoid)
Monoid1 = TypeVar("Monoid1", bound=Monoid)
A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")


@dataclass
class Result(MonadPlus[A_co]):
    get: "NonemptyList[A_co] | ArgumentError"

    def __or__(self, other: "Result[B]") -> "Result[A_co | B]":  # type: ignore[override]
        a = self.get
        b = other.get
        if isinstance(a, NonemptyList) and isinstance(b, NonemptyList):
            return Result(a + b)

        for get in [a, b]:
            if isinstance(get, NonemptyList):
                return Result(get)
        for get in [a, b]:
            if isinstance(get, HelpError):
                return Result(get)
        for get in [a, b]:
            if isinstance(get, ArgumentError):
                return Result(get)
        raise RuntimeError("Unreachable")

    def __rshift__(
        self: "Result[Sequence[A]]", other: "Result[Sequence[B]]"
    ) -> "Result[Sequence[A | B]]":
        """
        Sequence cs >> ds for each (cs, ds) in self.get * other.get.
        Short circuit at Exceptions.
        """

        return self >= (lambda cs: other >= (lambda ds: Result(NonemptyList(cs + ds))))

    def __ge__(self, f: Callable[[A_co], Monad[B]]) -> "Result[B]":
        return self.bind(f)

    def bind(self, f: Callable[[A_co], Monad[B]]) -> "Result[B]":
        x = self.get
        if isinstance(x, ArgumentError):
            return Result(x)
        else:

            def g(acc: Result[B], new: A_co) -> Result[B]:  # type: ignore[misc]
                y = f(new)
                assert isinstance(y, Result), y
                a = acc.get
                b = y.get

                if isinstance(a, NonemptyList) and isinstance(b, NonemptyList):
                    return Result(a + b)

                return next(
                    (x for x in (acc, y) if isinstance(x.get, NonemptyList)),
                    acc,
                )

            tail = [] if x.tail is None else list(x.tail)
            y = f(x.head)
            assert isinstance(y, Result), y
            return reduce(g, tail, y)

    @classmethod
    def return_(cls: "Type[Result[A]]", a: A) -> "Result[A]":
        return Result(NonemptyList(a))

    @classmethod
    def zero(
        cls: "Type[Result[Monoid_co]]", error: Optional[ArgumentError] = None
    ) -> "Result[Monoid_co]":
        return Result(ZeroError("zero") if error is None else error)
