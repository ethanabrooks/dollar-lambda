from dataclasses import replace
from typing import Any, Callable, Sequence

from monad_argparse.parser.apply import Apply
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Ok, Result


class Type(Apply[Sequence[KeyValue[str]], Sequence[KeyValue[Any]]]):
    """
    >>> from monad_argparse import Argument
    >>> Type(int, Argument("arg")).parse_args("1")
    [('arg', 1)]
    >>> Type(int, Argument("arg")).parse_args("one")
    ValueError("invalid literal for int() with base 10: 'one'")
    """

    def __init__(
        self, f: Callable[[str], Any], parser: Parser[Sequence[KeyValue[str]]]
    ):
        def g(
            kvs: Sequence[KeyValue[str]],
        ) -> Result[Sequence[KeyValue[Any]]]:
            head, *tail = kvs
            try:
                head = replace(head, value=f(head.value))
            except Exception as e:
                return Result(e)

            return Result(Ok([*tail, head]))

        super().__init__(g, parser)
