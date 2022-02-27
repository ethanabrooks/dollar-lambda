from dataclasses import dataclass
from typing import Callable, Generic, Type, TypeVar, Union, cast

from monad_argparse.monad.monad_plus import MonadPlus
from monad_argparse.parser.parser import ArgumentError

A = TypeVar("A", covariant=True)


@dataclass
class Ok(Generic[A]):
    get: A

    def __repr__(self):
        return f"Ok({self.get})"


B = TypeVar("B", covariant=True)
C = TypeVar("C")
D = TypeVar("D")


@dataclass
class Result(MonadPlus[B, "Result[B]"]):
    get: Union[Ok[B], Exception]

    def __add__(self, other: "Result[C]") -> "Result[Union[B, C]]":
        if isinstance(self.get, Ok):
            return self
        if isinstance(other.get, Ok):
            return other
        return Result(RuntimeError("__add__"))

    def __ge__(self, other: Callable[[B], "Result"]) -> "Result":
        return Result.bind(self, other)

    def __repr__(self):
        return f"Result({self.get})"

    @classmethod
    def bind(  # type: ignore[override]
        cls,
        x: "Result[A]",
        f: Callable[[A], "Result[A]"],
    ) -> "Result[A]":
        y = x.get
        if isinstance(y, Exception):
            return cast(Result[A], x)
        z: A = y.get
        return f(z)

    @classmethod
    def return_(cls: "Type[Result[B]]", a: C) -> "Result[C]":
        return Result(Ok(a))

    @classmethod
    def zero(cls: "Type[Result[B]]") -> "Result[B]":
        return Result(ArgumentError(description="zero"))
