from typing import Optional, Sequence

from monad_argparse.monad.nonempty_list import NonemptyList
from monad_argparse.parser.error import ArgumentError
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse, Parsed
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
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


class Flag(Parser[Sequence[KeyValue[bool]]]):
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
        long: str,
        short: Optional[str] = None,
        dest: Optional[str] = None,
    ):

        if len(long) == 1 and short is None:
            short = long
        key: str = long if dest is None else dest

        def f(
            cs: Sequence[str],
        ) -> Result[NonemptyList[Parse[Sequence[KeyValue[bool]]]]]:
            parser = MatchesFlag(long=long, short=short) >= (
                lambda _: self.return_(Parsed([KeyValue(key, True)]))
            )
            return parser.parse(cs)

        super().__init__(f)
