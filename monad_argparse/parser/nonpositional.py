# from dataclasses import Field, dataclass, fields
# from email.generator import Generator
from functools import reduce
from typing import Sequence, TypeVar

# from monad_argparse.parser.flag import Flag
# from monad_argparse.parser.option import Option
from monad_argparse.parser.parser import Parser

A = TypeVar("A")


def nonpositional(*parsers: "Parser[Sequence[A]]") -> "Parser[Sequence[A]]":
    """
    >>> from monad_argparse import Argument, Flag
    >>> p = nonpositional(Flag("verbose"), Flag("debug"))
    >>> p.parse_args("--verbose", "--debug")
    [('verbose', True), ('debug', True)]
    >>> p.parse_args("--debug", "--verbose")
    [('debug', True), ('verbose', True)]
    >>> p.parse_args()
    ArgumentError(token=None, description='Missing: --debug')
    >>> p.parse_args("--debug")
    ArgumentError(token=None, description='Missing: --verbose')
    >>> p.parse_args("--verbose")
    ArgumentError(token='--verbose', description="Input '--verbose' does not match '--debug")
    >>> p = nonpositional(Flag("verbose"), Flag("debug"), Argument("a"))
    >>> p.parse_args("--debug", "hello", "--verbose")
    [('debug', True), ('a', 'hello'), ('verbose', True)]
    """
    if not parsers:
        return Parser[Sequence[A]].empty()

    def get_alternatives():
        for i, head in enumerate(parsers):
            tail = [p for j, p in enumerate(parsers) if j != i]
            yield head >> nonpositional(*tail)

    def _or(p1: Parser[Sequence[A]], p2: Parser[Sequence[A]]) -> Parser[Sequence[A]]:
        return p1 | p2

    return reduce(_or, get_alternatives())


# @dataclass
# class Nonpositional(Parser[Sequence[A]]):
#     def __post_init__(self):
#         def get_parsers() -> Generator[Parser[Sequence[A]], None, None]:
#             field: Field
#             for field in fields(self):
#                 if field.type == bool:
#                     assert isinstance(
#                         field.default, bool
#                     ), f"If field.type == bool, field.default must be a bool, not {field.default}"
#                     long = field.name if field.default == True else f"no-{field.name}"
#                     yield Flag(long=long, dest=field.name, value=field.default)
#                 else:
#                     yield Option(field.name)

#         def f(cs: Sequence[str]):
#             parser = nonpositional(*self.parsers)

#         super().__init__(f)
