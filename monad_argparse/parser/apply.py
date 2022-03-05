from typing import Callable, TypeVar

from monad_argparse.monad.monoid import MonadPlus
from monad_argparse.parser.item import item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence

D = TypeVar("D", covariant=True, bound=MonadPlus)
E = TypeVar("E", covariant=True, bound=MonadPlus)
F = TypeVar("F", bound=MonadPlus)


def apply(f: Callable[[F], Result[E]], parser: Parser[F]):
    def h(parsed: F) -> Parser[E]:
        y = f(parsed)
        if isinstance(y.get, Exception):
            return Parser[E].zero(y.get)
        return Parser[E].return_(y.get)

    def g(
        cs: Sequence[str],
    ) -> Result[Parse[E]]:
        p: Parser[E] = parser >= h
        return p.parse(cs)

    return Parser(g)


def apply_item(f: Callable[[str], E], description: str):
    def g(parsed: Sequence[KeyValue[str]]) -> Result[E]:
        [kv] = parsed
        try:
            y = f(kv.value)
        except Exception as e:
            return Result(e)
        return Result(y)

    return apply(g, item(description))
