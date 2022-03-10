from dataclasses import dataclass
from inspect import signature
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

from dollar_lambda import parser
from dollar_lambda.args import ArgsField
from dollar_lambda.key_value import KeyValue
from dollar_lambda.parser import Parser, apply, equals
from dollar_lambda.result import Result
from dollar_lambda.sequence import Sequence

A = TypeVar("A")
A_co = TypeVar("A_co", covariant=True)


def func_to_parser(
    func: Callable,
    flip_bools: bool = True,
    help: Optional[Dict[str, str]] = None,
    types: Optional[Dict[str, Callable[[str], Any]]] = None,
) -> Parser[Sequence[KeyValue[Any]]]:
    _help = {} if help is None else help
    _types = {} if types is None else types
    return ArgsField.nonpositional(
        *[
            ArgsField(
                name=k,
                default=v.default,
                help=_help.get(k),
                type=_types.get(k, v.annotation),
            )
            for k, v in signature(func).parameters.items()
        ],
        flip_bools=flip_bools,
    )


@dataclass
class Parse(parser.Parse[A_co]):
    """
    A `Parse` is the output of parsing.

    Parameters
    ----------
    function :
    """

    function: Callable


def command(
    flip_bools: bool = True,
    help: Optional[Dict[str, str]] = None,
    types: Optional[Dict[str, Callable[[str], Any]]] = None,
) -> Callable[[Callable], Callable]:
    """
    >>> @command(help=dict(a="something about a"), types=dict(a=lambda x: int(x) + 1))
    ... def f(a: int = 1, b: bool = False):
    ...     print(dict(a=a, b=b))
    >>> f("-a", "2", "-b")
    {'a': 3, 'b': True}
    """

    def wrapper(func: Callable) -> Callable:
        parser = func_to_parser(func, flip_bools=flip_bools, help=help, types=types)

        def wrapped(*args) -> Any:
            parsed = parser.parse_args(*args)
            assert isinstance(parsed, Dict)
            return func(**parsed)

        return wrapped

    return wrapper


# def subcommand(func: Callable):
#     def f(
#         kvs: Sequence[KeyValue[str]],
#     ) -> Parser[Tuple[Callable, Sequence[KeyValue[str]]]]:
#         return Result.return_(
#             Parse(
#                 function=func,
#                 parsed=parse.parsed,
#                 unparsed=parse.unparsed,
#             )
#         )

#     return equals(func.__name__) >= f


# @dataclass
# class FuncParserPair:
#     function: Callable
#     parser: Parser[Sequence[KeyValue[Any]]]


# @dataclass
# class CommandGroup:
#     parser: Parser[Sequence[KeyValue[Any]]]
#     func_parser_pairs: List[FuncParserPair] = field(default_factory=list)

#     def main(self, *args: str):
#         def get_subparsers() -> Iterator[Parser[Sequence[KeyValue[str]]]]:
#             for pair in self.func_parser_pairs:
#                 arg: Parser[Sequence[KeyValue[Any]]] = argument(pair.function.__name__)
#                 subparser: Parser[Sequence[KeyValue[Any]]] = pair.parser
#                 yield arg >> subparser

#         parser = self.parser >> reduce(operator.or_, get_subparsers())
#         parsed = parser.parse_args(*args)
#         assert isinstance(parsed, Dict)
#         for pair in self.func_parser_pairs:
#             name = pair.function.__name__
#             if name in parsed:
#                 del parsed[name]
#                 return pair.function(**parsed)
#         raise RuntimeError(
#             "Mismatch between self.func_parser_pairs and parser in self.parse_args"
#         )

#     def subcommand(
#         self,
#         flip_bools: bool = True,
#         help: Optional[Dict[str, str]] = None,
#         types: Optional[Dict[str, Callable[[str], Any]]] = None,
#     ):
#         def wrapper(func: Callable) -> Callable:
#             subparser = func_to_parser(
#                 func, flip_bools=flip_bools, help=help, types=types
#             )
#             existing_names = [p.function.__name__ for p in self.func_parser_pairs]
#             assert (
#                 func.__name__ not in existing_names
#             ), f"Duplicate function name: {func.__name__}"
#             self.func_parser_pairs.append(FuncParserPair(func, subparser))
#             return func

#         return wrapper
