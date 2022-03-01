from typing import Optional, TypeVar

from monad_argparse.parser.flag import MatchesFlag, flags
from monad_argparse.parser.item import Item
from monad_argparse.parser.key_value import KeyValues
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence

A = TypeVar("A", covariant=True)


class Option(Parser[KeyValues[str]]):
    """
    >>> Option("value").parse_args("--value", "x")
    [('value', 'x')]
    >>> Option("value").parse_args("--value")
    ArgumentError(token=None, description='Missing: value')
    >>> Option("value").parse_args()
    ArgumentError(token=None, description='Missing: --value')
    """

    def __init__(
        self,
        long: str,
        short: Optional[str] = None,
        dest: Optional[str] = None,
    ):
        if len(long) == 1 and short is None:
            short = long
        name: str = long if dest is None else dest

        def f(
            cs: Sequence[str],
        ) -> Result[Parse[KeyValues[str]]]:
            parser = MatchesFlag(long=long, short=short) >= (
                lambda _: Item(
                    name,
                    description=f"argument for {next(flags(short=short, long=long))}",
                )
            )
            return parser.parse(cs)

        super().__init__(f)
