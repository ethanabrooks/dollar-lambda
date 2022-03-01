from dataclasses import replace
from typing import Any, Callable

from monad_argparse.parser.apply import Apply
from monad_argparse.parser.key_value import KeyValues
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result


class Type(Apply[KeyValues[str], KeyValues[Any]]):
    """
    >>> from monad_argparse import Argument
    >>> Type(int, Argument("arg")).parse_args("1")
    [('arg', 1)]
    >>> Type(int, Argument("arg")).parse_args("one")
    ValueError("invalid literal for int() with base 10: 'one'")
    """

    def __init__(self, f: Callable[[str], Any], parser: Parser[KeyValues[str]]):
        def g(
            kvs: KeyValues[str],
        ) -> Result[KeyValues[Any]]:
            head, *tail = kvs.get
            try:
                head = replace(head, value=f(head.get_value()))
            except Exception as e:
                return Result(e)

            return Result(KeyValues([*tail, head]))

        super().__init__(g, parser)
