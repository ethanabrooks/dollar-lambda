from dataclasses import dataclass
from typing import Callable, Generator, Generic, Sequence, Type, TypeVar, Union

from monad_argparse.monad.monoid import MonadPlus

A = TypeVar("A", covariant=True)
B = TypeVar("B", covariant=True)
C = TypeVar("C", covariant=True)


@dataclass
class Parsed(Generic[A]):
    get: A

    def __repr__(self):
        return f"Parsed({self.get})"

    def __rshift__(
        self: "Parsed[Sequence[B]]", other: "Parsed[Sequence[C]]"
    ) -> "Parsed[Sequence[Union[B, C]]]":
        def g() -> Generator[Union[B, C], None, None]:
            yield from self.get
            yield from other.get

        return Parsed(list(g()))


D = TypeVar("D", covariant=True)
E = TypeVar("E")


@dataclass
class Parse(MonadPlus[D, "Parse[D]"]):
    parsed: Parsed[D]
    unparsed: Sequence[str]

    def __or__(self, other: "Parse[E]") -> "Parse[Union[D, E]]":
        raise NotImplementedError

    @staticmethod
    def bind(x: "Parse[E]", f: Callable[[E], "Parse[E]"]) -> "Parse[E]":  # type: ignore[override]
        parse = f(x.parsed.get)
        return Parse(parse.parsed, max(parse.unparsed, x.unparsed, key=len))

    @staticmethod
    def return_(a: E) -> "Parse[E]":
        return Parse(Parsed(a), [])

    @classmethod
    def zero(cls: "Type[Parse[D]]") -> "Parse[D]":
        raise NotImplementedError
