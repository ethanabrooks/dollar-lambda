from dataclasses import replace
from typing import Any, Callable

from monad_argparse.apply import apply
from monad_argparse.key_value import KeyValue
from monad_argparse.parser import Parser
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence


def type_(
    f: Callable[[str], Any], parser: Parser[Sequence[KeyValue[str]]]
) -> Parser[Sequence[KeyValue[Any]]]:
    def g(
        kvs: Sequence[KeyValue[str]],
    ) -> Result[Sequence[KeyValue[Any]]]:
        head, *tail = kvs.get
        try:
            head = replace(head, value=f(head.value))
        except Exception as e:
            return Result(e)

        return Result(Sequence([*tail, head]))

    return apply(g, parser)
