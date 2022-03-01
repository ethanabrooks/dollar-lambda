from dataclasses import dataclass
from typing import Callable, Generator, Type, TypeVar, Union

from monad_argparse.monad.monoid import MonadPlus, Monoid
from monad_argparse.parser.sequence import Sequence

A = TypeVar("A", covariant=True, bound=Monoid)
B = TypeVar("B", covariant=True, bound=Monoid)
C = TypeVar("C", covariant=True)


@dataclass
class Parsed(Monoid[A, "Parsed[A]"]):
    get: A

    def __or__(self, other: "Parsed[B]") -> "Parsed[Union[A, B]]":
        return Parsed(self.get | other.get)

    def __repr__(self):
        return f"Parsed({self.get})"

    def __rshift__(
        self: "Parsed[Sequence[B]]", other: "Parsed[Sequence[C]]"
    ) -> "Parsed[Sequence[Union[B, C]]]":
        def g() -> Generator[Union[B, C], None, None]:
            yield from self.get
            yield from other.get

        return Parsed(Sequence(list(g())))

    @staticmethod
    def zero() -> "Parsed[A]":
        raise NotImplementedError


D = TypeVar("D", covariant=True, bound=Monoid)
E = TypeVar("E", bound=Monoid)


@dataclass
class Parse(MonadPlus[D, "Parse[D]"]):
    parsed: Parsed[D]
    unparsed: Sequence[str]

    def __or__(self, other: "Parse[E]") -> "Parse[Union[D, E]]":
        return Parse(
            parsed=self.parsed | other.parsed,
            unparsed=max(self.unparsed, other.unparsed, key=len),
        )

    @staticmethod
    def bind(x: "Parse[E]", f: Callable[[E], "Parse[E]"]) -> "Parse[E]":  # type: ignore[override]
        parse = f(x.parsed.get)
        return Parse(parse.parsed, max(parse.unparsed, x.unparsed, key=len))

    @staticmethod
    def return_(a: E) -> "Parse[E]":
        return Parse(Parsed(a), Sequence([]))

    @classmethod
    def zero(cls: "Type[Parse[D]]") -> "Parse[D]":
        raise NotImplementedError
