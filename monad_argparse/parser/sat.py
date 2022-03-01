from typing import Callable, Sequence, TypeVar

from monad_argparse.monad.monad_plus import MonadPlus
from monad_argparse.parser.apply import Apply
from monad_argparse.parser.error import ArgumentError
from monad_argparse.parser.item import Item
from monad_argparse.parser.key_value import KeyValue, KeyValues
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result

F = TypeVar("F", bound=MonadPlus)


class Sat(Apply[F, F]):
    def __init__(
        self,
        parser: Parser[F],
        predicate: Callable[[F], bool],
        on_fail: Callable[[F], ArgumentError],
    ):
        def f(x: F) -> Result[F]:
            return Result(x if predicate(x) else on_fail(x))

        super().__init__(f, parser)


class SatItem(Sat[KeyValues[str]]):
    def __init__(
        self,
        predicate: Callable[[str], bool],
        on_fail: Callable[[str], ArgumentError],
        description: str,
    ):
        def _predicate(parsed: Sequence[KeyValue[str]]) -> bool:
            [kv] = parsed
            return predicate(kv.value)

        def _on_fail(parsed: Sequence[KeyValue[str]]) -> ArgumentError:
            [kv] = parsed
            return on_fail(kv.value)

        super().__init__(Item(description), _predicate, _on_fail)
