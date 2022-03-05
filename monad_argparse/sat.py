from typing import Callable, TypeVar

from pytypeclass import MonadPlus

from monad_argparse.apply import apply
from monad_argparse.error import ArgumentError, UnequalError
from monad_argparse.item import item
from monad_argparse.key_value import KeyValue
from monad_argparse.parser import Parser
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence

A = TypeVar("A", bound=MonadPlus)


def sat(
    parser: Parser[A],
    predicate: Callable[[A], bool],
    on_fail: Callable[[A], ArgumentError],
) -> Parser[A]:
    def f(x: A) -> Result[A]:
        return Result(x if predicate(x) else on_fail(x))

    return apply(f, parser)


def sat_item(
    predicate: Callable[[str], bool],
    on_fail: Callable[[str], ArgumentError],
    description: str,
) -> Parser[Sequence[KeyValue[str]]]:
    def _predicate(parsed: Sequence[KeyValue[str]]) -> bool:
        [kv] = parsed
        return predicate(kv.value)

    def _on_fail(parsed: Sequence[KeyValue[str]]) -> ArgumentError:
        [kv] = parsed
        return on_fail(kv.value)

    return sat(item(description), _predicate, _on_fail)


def equals(s: str) -> Parser[Sequence[KeyValue[str]]]:
    return sat_item(
        predicate=lambda _s: _s == s,
        on_fail=lambda _s: UnequalError(s, _s),
        description=s,
    )
