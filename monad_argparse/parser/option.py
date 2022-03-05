from typing import TypeVar

from monad_argparse.parser.item import item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sat import equals
from monad_argparse.parser.sequence import Sequence

A = TypeVar("A", covariant=True)


def option(dest: str, long: bool = True, default=None):
    """
    >>> option("value").parse_args("--value", "x")
    [('value', 'x')]
    >>> option("value").parse_args("--value")
    MissingError(missing='value')
    >>> option("value").parse_args()
    MissingError(missing='--value')
    """

    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[bool]]]]:
        flag_str = f"--{dest}" if long else f"-{dest}"
        parser = equals(flag_str) >= (lambda _: item(dest))
        return parser.parse(cs)

    parser = Parser(f)
    if default:
        parser = parser | parser.key_values(**{dest: default})
    return parser
