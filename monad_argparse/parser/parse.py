from dataclasses import dataclass
from typing import Callable, Optional, Type, TypeVar, Union

from monad_argparse.monad.monoid import MonadPlus, Monoid
from monad_argparse.parser.sequence import Sequence

A = TypeVar("A", covariant=True, bound=Monoid)
B = TypeVar("B", bound=Monoid)


@dataclass
class Parse(MonadPlus[A, "Parse[A]"]):
    parsed: A
    unparsed: Sequence[str]
    default: Optional[A] = None

    def __or__(self, other: "Parse[B]") -> "Parse[Union[A, B]]":  # type: ignore[override]
        parsed = self.parsed | other.parsed
        return Parse(
            parsed=parsed,
            unparsed=max(self.unparsed, other.unparsed, key=len),
        )

    @staticmethod
    def bind(x: "Parse[B]", f: Callable[[B], "Parse[B]"]) -> "Parse[B]":  # type: ignore[override]
        parse = f(x.parsed)
        return Parse(parse.parsed, max(parse.unparsed, x.unparsed, key=len))

    @classmethod
    def return_(cls: Type["Parse[B]"], a: B) -> "Parse[B]":  # type: ignore[override]
        return Parse(a, Sequence([]))

    @classmethod
    def zero(cls: "Type[Parse[A]]") -> "Parse[A]":
        raise NotImplementedError
