from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sat import equals
from monad_argparse.parser.sequence import Sequence


def flag(dest: str, long: bool = True, default=None):
    """
    >>> flag("verbose").parse_args("--verbose")
    [('verbose', True)]
    >>> flag("verbose").parse_args()
    MissingError(missing='--verbose')
    >>> flag("verbose").parse_args("--verbose", "--verbose", "--verbose")
    [('verbose', True)]
    """

    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[bool]]]]:
        flag_str = f"--{dest}" if long else f"-{dest}"
        parser = equals(flag_str) >= (
            lambda _: Parser[Sequence[KeyValue[bool]]].key_values(**{dest: True})
        )
        return parser.parse(cs)

    parser = Parser(f)
    if default:
        parser = parser | parser.key_values(**{dest: default})
    return parser
