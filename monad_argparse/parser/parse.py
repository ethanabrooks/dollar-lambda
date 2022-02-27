from dataclasses import dataclass
from typing import Generator, Generic, Sequence, TypeVar, Union

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


@dataclass
class Parse(Generic[D]):
    parsed: Parsed[D]
    unparsed: Sequence[str]
