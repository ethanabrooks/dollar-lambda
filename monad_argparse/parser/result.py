from dataclasses import dataclass
from typing import Callable, Type, TypeVar, Union

from monad_argparse.monad.monad_plus import MonadPlus
from monad_argparse.parser.error import ArgumentError

A = TypeVar("A", covariant=True)
B = TypeVar("B", covariant=True, bound=MonadPlus)
C = TypeVar("C", bound=MonadPlus)
D = TypeVar("D")


@dataclass
class Result(MonadPlus[B, "Result[B]"]):
    get: Union[B, Exception]

    def __or__(self, other: "Result[C]") -> "Result[Union[B, C]]":
        if not isinstance(self.get, Exception):
            return self
        if not isinstance(other.get, Exception):
            return other
        return Result(RuntimeError("__or__"))

    def __ge__(self, other: Callable[[B], "Result"]) -> "Result":
        return Result.bind(self, other)

    def __repr__(self):
        return f"Result({self.get})"

    @classmethod
    def bind(  # type: ignore[override]
        cls,
        x: "Result[C]",
        f: Callable[[C], "Result[C]"],
    ) -> "Result[C]":
        y = x.get
        if isinstance(y, Exception):
            return x
        return f(y)

    @classmethod
    def return_(cls: "Type[Result[B]]", a: C) -> "Result[C]":
        return Result(a)

    @classmethod
    def zero(cls: "Type[Result[B]]") -> "Result[B]":
        return Result(ArgumentError(description="zero"))
