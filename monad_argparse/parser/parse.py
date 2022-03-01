from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Type, TypeVar

from monad_argparse.monad.monoid import MonadPlus, Monoid
from monad_argparse.parser.sequence import Sequence

A = TypeVar("A", covariant=True, bound=Monoid)
B = TypeVar("B", bound=Monoid)


@dataclass
class Parse(MonadPlus[A]):
    parsed: A
    unparsed: Sequence[str]
    default: Optional[A] = None

    def __add__(self, other: "Parse[B]") -> Parse[A | B]:
        parsed = self.parsed | other.parsed
        if self.default is not None and other.default is not None:
            default = self.default | other.default
        elif self.default is not None:
            default = self.default
        elif other.default is not None:
            default = other.default
        else:
            assert self.default is None and other.default is None
            default = None
        return Parse(
            default=default,
            parsed=parsed,
            unparsed=max(self.unparsed, other.unparsed, key=len),
        )

    def bind(self, f: Callable[[A], Parse[B]]) -> Parse[B]:
        parse = f(self.parsed)
        return Parse(parse.parsed, max(parse.unparsed, self.unparsed, key=len))

    @classmethod
    def return_(cls: Type["Parse[B]"], a: B) -> "Parse[B]":  # type: ignore[override]
        return Parse(a, Sequence([]))

    @classmethod
    def zero(cls: "Type[Parse[A]]") -> "Parse[A]":
        raise NotImplementedError
