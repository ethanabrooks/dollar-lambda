from typing import Generator, Sequence

from monad_argparse.parser.do_parser import DoParser
from monad_argparse.parser.item import Item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parsed
from monad_argparse.parser.parser import Parser


class Argument(DoParser[str]):
    """
    >>> Argument("name").parse_args("Alice")
    [('name', 'Alice')]
    >>> Argument("name").parse_args()
    ArgumentError(token=None, description='Missing: name')
    """

    def __init__(self, dest: str):
        def g() -> Generator[
            Parser[Sequence[KeyValue[str]]], Parsed[Sequence[KeyValue[str]]], None
        ]:
            yield Item(dest)

        super().__init__(g)
