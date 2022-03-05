from typing import Optional

from monad_argparse.parser.item import item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sat import equals
from monad_argparse.parser.sequence import Sequence


def option(
    dest: str, flag: Optional[str] = None, default=None
) -> Parser[Sequence[KeyValue[str]]]:
    """
    >>> option("value").parse_args("--value", "x")
    [('value', 'x')]
    >>> option("value").parse_args("--value")
    MissingError(missing='value')
    >>> option("value").parse_args()
    MissingError(missing='--value')
    >>> option("value", default=1).parse_args()
    [('value', 1)]
    >>> option("value", default=1).parse_args("--value")
    [('value', 1)]
    >>> option("value", default=1).parse_args("--value", "x")
    [('value', 'x')]
    >>> option("v").parse_args("-v", "x")
    [('v', 'x')]
    >>> option("v", flag="--value").parse_args("--value", "x")
    [('v', 'x')]
    """

    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[str]]]]:
        if flag is None:
            _flag = f"--{dest}" if len(dest) > 1 else f"-{dest}"
        else:
            _flag = flag

        parser = equals(_flag) >= (lambda _: item(dest))
        return parser.parse(cs)

    parser = Parser(f)
    if default:
        parser = parser | parser.key_values(**{dest: default})
    return parser
