from typing import Generator, Optional, Sequence

from monad_argparse.parser.do_parser import DoParser
from monad_argparse.parser.flag import MatchesFlag, flags
from monad_argparse.parser.item import Item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parsed
from monad_argparse.parser.parser import Parser


class Option(DoParser[str]):
    """
    >>> Option("value").parse_args("--value", "x")
    [('value', 'x')]
    >>> Option("value").parse_args("--value")
    ArgumentError(token=None, description='Missing: argument for --value')
    >>> Option("value").parse_args()
    ArgumentError(token=None, description='Missing: --value')
    """

    def __init__(
        self,
        long: Optional[str] = None,
        short: Optional[str] = None,
        dest: Optional[str] = None,
    ):
        def g() -> Generator[Parser, Parsed[Sequence[KeyValue[str]]], None]:
            yield MatchesFlag(long=long, short=short)
            parsed = yield Item(f"argument for {next(flags(short=short, long=long))}")
            [kv] = parsed.get

            key = dest or long or short
            assert key is not None, "Either dest or long or short must be specified."
            yield self.return_(Parsed([KeyValue(key, kv.value)]))

        super().__init__(g)
