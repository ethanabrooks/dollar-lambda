import typing
from dataclasses import dataclass
from typing import Callable, Generator, TypeVar, Union, overload

from monad_argparse.monad.monoid import MonadPlus

A = TypeVar("A", covariant=True)
B = TypeVar("B")


@dataclass
class Sequence(MonadPlus[A, "Sequence[A]"], typing.Sequence[A]):
    get: typing.Sequence[A]

    @overload
    def __getitem__(self, i: int) -> "A":
        ...

    @overload
    def __getitem__(self, i: slice) -> "Sequence[A]":
        ...

    def __getitem__(self, i: Union[int, slice]) -> Union[A, "Sequence[A]"]:
        if isinstance(i, int):
            return self.get[i]
        return Sequence(self.get[i])

    def __iter__(self) -> Generator[A, None, None]:
        yield from self.get

    def __len__(self) -> int:
        return len(self.get)

    def __or__(self, other: "Sequence[B]") -> "Sequence[Union[A, B]]":
        return Sequence([*self.get, *other.get])

    @staticmethod
    def bind(  # type: ignore[override]
        x: "Sequence[A]",
        f: Callable[[A], "Sequence[A]"],
    ) -> "Sequence[A]":
        def g() -> Generator[A, None, None]:
            for a in x:
                yield from f(a)

        return Sequence(list(g()))

    @staticmethod
    def return_(a: B) -> "Sequence[B]":
        return Sequence([a])

    @staticmethod
    def zero() -> "Sequence[A]":
        return Sequence([])
