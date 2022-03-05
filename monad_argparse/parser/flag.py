from typing import Optional

from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sat import equals
from monad_argparse.parser.sequence import Sequence


def flag(
    dest: str,
    string: Optional[str] = None,
    default: bool = False,
    require: bool = False,
) -> Parser[Sequence[KeyValue[bool]]]:
    """
    >>> flag("verbose").parse_args("--verbose")
    [('verbose', True)]
    >>> flag("verbose").parse_args()
    [('verbose', False)]
    >>> flag("verbose", default=True).parse_args()
    [('verbose', True)]
    >>> flag("verbose").parse_args("--verbose", "--verbose", "--verbose")
    [('verbose', True)]
    >>> flag("value", default=False).parse_args("--value")
    [('value', True)]
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
    if not require:
        parser = parser | parser.key_values(**{dest: default})
    return parser
