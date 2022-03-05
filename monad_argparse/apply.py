from typing import Callable, TypeVar

from pytypeclass import MonadPlus

from monad_argparse.item import item
from monad_argparse.key_value import KeyValue
from monad_argparse.parse import Parse
from monad_argparse.parser import Parser
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence

A = TypeVar("A", covariant=True, bound=MonadPlus)
B = TypeVar("B", bound=MonadPlus)


def apply(f: Callable[[B], Result[A]], parser: Parser[B]) -> Parser[A]:
    def h(parsed: B) -> Parser[A]:
        y = f(parsed)
        if isinstance(y.get, Exception):
            return Parser[A].zero(y.get)
        return Parser[A].return_(y.get)

    def g(
        cs: Sequence[str],
    ) -> Result[Parse[A]]:
        p: Parser[A] = parser >= h
        return p.parse(cs)

    return Parser(g)


def apply_item(f: Callable[[str], A], description: str) -> Parser[A]:
    def g(parsed: Sequence[KeyValue[str]]) -> Result[A]:
        [kv] = parsed
        try:
            y = f(kv.value)
        except Exception as e:
            return Result(e)
        return Result(y)

    return apply(g, item(description))
