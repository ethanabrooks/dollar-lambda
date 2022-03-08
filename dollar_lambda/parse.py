"""
A `Parse` is the output of parsing, separating inputs into a parsed component and a yet-to-be parsed (`unparsed`) component.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type, TypeVar

from pytypeclass import MonadPlus, Monoid

from dollar_lambda.sequence import Sequence

A = TypeVar("A", covariant=True, bound=Monoid)
B = TypeVar("B", bound=Monoid)


@dataclass
class Parse(MonadPlus[A]):
    """
    A `Parse` is the output of parsing.

    Parameters
    ----------
    parsed : A
        Component parsed by the parsed
    unparsed : Sequence[str]
        Component yet to be parsed
    """

    parsed: A
    unparsed: Sequence[str]

    def __or__(self, other: "Parse[B]") -> Parse[A | B]:
        return Parse(
            parsed=self.parsed | other.parsed,
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
