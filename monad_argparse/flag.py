from typing import Optional

from monad_argparse.key_value import KeyValue
from monad_argparse.parse import Parse
from monad_argparse.parser import Parser
from monad_argparse.result import Result
from monad_argparse.sat import equals
from monad_argparse.sequence import Sequence


def flag(
    dest: str,
    string: Optional[str] = None,
    default: Optional[bool] = None,
) -> Parser[Sequence[KeyValue[bool]]]:
    """
    >>> p = flag("verbose", default=False)
    >>> p.parse_args("--verbose")
    [('verbose', True)]
    >>> p.parse_args()
    [('verbose', False)]
    >>> p.parse_args("--verbose", "--verbose", "--verbose")
    [('verbose', True)]
    >>> flag("v", string="--value").parse_args("--value")
    [('v', True)]
    """

    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[bool]]]]:
        if string is None:
            _string = f"--{dest}" if len(dest) > 1 else f"-{dest}"
        else:
            _string = string
        parser = equals(_string) >= (
            lambda _: Parser[Sequence[KeyValue[bool]]].key_values(**{dest: not default})
        )
        return parser.parse(cs)

    parser = Parser(f)
    if default is not None:
        parser = parser | parser.key_values(**{dest: default})
    return parser
