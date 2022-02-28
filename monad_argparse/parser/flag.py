from typing import Generator, Optional

from monad_argparse.parser.do_parser import DoParser
from monad_argparse.parser.error import ArgumentError
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parsed
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.sat import SatItem


def flags(long: Optional[str] = None, short: Optional[str] = None):
    if short:
        yield f"-{short}"
    if long:
        yield f"--{long}"


class MatchesFlag(SatItem):
    def __init__(
        self,
        long: Optional[str] = None,
        short: Optional[str] = None,
    ):
        assert long or short, "Either long or short must be provided."

        def matches(x: str) -> bool:
            if short is not None and x == f"-{short}":
                return True
            if long is not None and x == f"--{long}":
                return True
            return False

        flags_string = f"{' or '.join(list(flags(short=short, long=long)))}"

        super().__init__(
            matches,
            on_fail=lambda a: ArgumentError(
                a, description=f"Input '{a}' does not match '{flags_string}"
            ),
            description=flags_string,
        )


class Flag(DoParser[bool]):
    """
    >>> Flag("verbose").parse_args("--verbose")
    [('verbose', True)]
    >>> Flag("verbose").parse_args()
    ArgumentError(token=None, description='Missing: --verbose')
    >>> Flag("verbose").parse_args("--verbose", "--verbose", "--verbose")
    [('verbose', True)]
    """

    def __init__(
        self,
        long: Optional[str] = None,
        short: Optional[str] = None,
        dest: Optional[str] = None,
        value: bool = True,
    ):
        def g() -> Generator[Parser, Parsed, None]:
            yield MatchesFlag(long=long, short=short)

            key = dest or long or short
            assert key is not None, "Either dest or long or short must be specified."
            yield self.return_(Parsed([KeyValue(key, value)]))

        super().__init__(g)
