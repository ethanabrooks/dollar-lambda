"""
Defines the `command` decorator and the `CommandTree` class.
"""
import operator
import sys
from dataclasses import dataclass, field, replace
from functools import reduce
from inspect import Parameter, signature
from typing import Any, Callable, Dict, Iterator, List, Optional, TypeVar, cast

from pytypeclass.nonempty_list import NonemptyList

from dollar_lambda import parser as parser_mod
from dollar_lambda.args import ArgsField
from dollar_lambda.error import ArgumentError
from dollar_lambda.key_value import KeyValue
from dollar_lambda.parser import Parse, Parser, done, equals, wrap_help
from dollar_lambda.result import Result
from dollar_lambda.sequence import Sequence

A = TypeVar("A")
B = TypeVar("B")
A_co = TypeVar("A_co", covariant=True)


def func_to_parser(
    func: Callable,
    exclude: Optional[List[str]] = None,
    flip_bools: bool = True,
    help: Optional[Dict[str, str]] = None,
    strings: Optional[Dict[str, str]] = None,
    types: Optional[Dict[str, Callable[[str], Any]]] = None,
) -> Parser[Sequence[KeyValue[Any]]]:
    _exclude = [] if exclude is None else exclude
    _help = {} if help is None else help
    _strings = {} if strings is None else strings
    _types = {} if types is None else types

    return ArgsField.nonpositional(
        *[
            ArgsField(
                name=k,
                default=None if v.default == Parameter.empty else v.default,
                help=_help.get(k),
                string=_strings.get(k),
                type=_types.get(k, v.annotation),
            )
            for k, v in signature(func).parameters.items()
            if k not in _exclude
        ],
        flip_bools=flip_bools,
    )


def command(
    flip_bools: bool = True,
    help: Optional[Dict[str, str]] = None,
    strings: Optional[Dict[str, str]] = None,
    types: Optional[Dict[str, Callable[[str], Any]]] = None,
) -> Callable[[Callable], Callable]:
    """
    A succinct way to generate a simple `nonpositional` parser. `@command` derives the
    component parsers from the function's signature and automatically executes the function with
    the parsed arguments, if parsing succeeds:

    >>> @command(help=dict(a="something about a"), types=dict(a=lambda x: int(x) + 1))
    ... def f(a: int = 1, b: bool = False):
    ...     return dict(a=a, b=b)
    >>> f("-a", "2", "-b")
    {'a': 3, 'b': True}

    If the wrapped function receives no arguments (as in `f()`), the parser will take
    `sys.argv[1:]` as the input.

    Note that `@command` does not handle mutually exclusive arguments or alternative
    arguments.

    Parameters
    ----------
    flip_bools : bool
        For boolean arguments that default to true, this changes the flag from `--{dest}` to `--no-{dest}`:

    >>> @command(flip_bools=True)
    ... def f(cuda: bool = True):
    ...     return dict(cuda=cuda)
    >>> f()
    {'cuda': True}
    >>> f("--no-cuda")
    {'cuda': False}

    As the following example demonstrates, when `flip_bools=False` output can be somewhat confusing:

    >>> @command(flip_bools=False)
    ... def f(cuda: bool = True):
    ...     return dict(cuda=cuda)
    >>> f("--cuda")
    {'cuda': False}

    help : dict[str, str]
        A dictionary of help strings for the arguments.

    >>> @command(help=dict(quiet="Be quiet"))
    ... def f(quiet: bool):
    ...     return dict(quiet=quiet)
    >>> f("--help")
    usage: --quiet
    quiet: Be quiet

    strings : dict[str, str]
        This dictionary maps variable names to the strings that the parser will look for in the input. For example:

    >>> @command(strings=dict(quiet="--quiet-mode"))
    ... def f(quiet: bool):
    ...     return dict(quiet=quiet)
    >>> f("--quiet-mode")
    {'quiet': True}
    >>> f("--quiet")
    usage: --quiet-mode
    Expected '--quiet-mode'. Got '--quiet'

    types: dict[str, Callable[[str], Any]]
        This dictionary maps variable names to custom type converters. For example:

    >>> @command(types=dict(x=lambda x: int(x) + 1))
    ... def f(x: int):
    ...     return dict(x=x)
    >>> f("-x", "0")
    {'x': 1}
    """

    def wrapper(func: Callable) -> Callable:
        p = func_to_parser(
            func, flip_bools=flip_bools, help=help, strings=strings, types=types
        )
        p = wrap_help(p)

        def wrapped(*args) -> Any:
            parsed = p.parse_args(*args)
            if parsed is None:
                return
            assert isinstance(parsed, Dict), parsed
            return func(**parsed)

        return wrapped

    return wrapper


@dataclass
class FunctionPair(Sequence[A]):
    function: Callable

    def __or__(self, other: Sequence[B]) -> "FunctionPair[A | B]":
        function = other.function if isinstance(other, FunctionPair) else self.function
        return FunctionPair(get=[*self, *other], function=function)


def command_parser(
    func: Callable,
    usage: Optional[str] = None,
    help: Optional[Dict[str, str]] = None,
) -> Parser[FunctionPair[A]]:
    _help = {} if help is None else help
    return Parser[FunctionPair[A]](
        lambda cs: Result.return_(
            Parse(parsed=FunctionPair(Sequence[A]([]), func), unparsed=cs)
        ),
        usage=usage,
        helps=_help,
    )


def subcommand_parser(
    func: Callable,
    usage: Optional[str] = None,
    help: Optional[Dict[str, str]] = None,
) -> Parser[FunctionPair[KeyValue[str]]]:
    _help = {} if help is None else help

    # def f(
    #     _: Sequence[KeyValue[str]],
    # ) -> Parser[FunctionPair[KeyValue[str]]]:
    #     return Parser[FunctionPair[KeyValue[str]]](g, usage=usage, helps=_help)

    def g(
        cs: Sequence[str],
    ) -> Result[Parse[FunctionPair[KeyValue[str]]]]:
        return Result.return_(
            Parse(parsed=FunctionPair(Sequence([]), func), unparsed=cs)
        )

    eq = equals(func.__name__)
    p = eq >= (
        lambda _: Parser[FunctionPair[KeyValue[str]]](g, usage=usage, helps=_help)
    )
    return replace(p, usage=eq.usage, helps=eq.helps)


@dataclass
class Node:
    function: Callable
    flip_bools: bool
    help: Optional[Dict[str, str]]
    required: bool
    strings: Optional[Dict[str, str]]
    types: Optional[Dict[str, Callable[[str], Any]]]
    subcommand: bool
    tree: Optional["CommandTree"]

    def parser(self, *exclude: str) -> Parser[FunctionPair[KeyValue[Any]]]:
        p1 = (
            subcommand_parser(self.function)
            if self.subcommand
            else command_parser(self.function)
        )
        p2 = func_to_parser(
            self.function,
            exclude=list(exclude),
            flip_bools=self.flip_bools,
            help=self.help,
            strings=self.strings,
            types=self.types,
        )
        p = p1 >> p2
        return p if self.required else p.optional()  # type: ignore[return-value]

    def variable_names(self) -> Iterator[str]:
        yield from signature(self.function).parameters.keys()


@dataclass
class CommandTree:
    """
    >>> tree = CommandTree()

    >>> @tree.command()
    ... def f1(a: int):
    ...     return dict(f1=dict(a=a))

    >>> @tree.subcommand()
    ... def f2(b: bool):
    ...     return dict(f2=dict(b=b))

    >>> tree.main("-h")
    usage: [-a A | f2 -b]
    >>> tree.main("-a", "1")
    {'f1': {'a': 1}}
    >>> tree.main("f2", "-b")
    {'f2': {'b': True}}

    >>> tree = CommandTree()

    >>> @tree.command()
    ... def f1(a: int):
    ...     return dict(f1=dict(a=a))

    >>> @f1.subcommand()
    ... def f2(a: int, b: bool):
    ...     return dict(f2=dict(a=a, b=b))

    >>> @f1.subcommand()
    ... def f3(a: int, c: str):
    ...     return dict(f3=dict(a=a, c=c))

    >>> tree.main("-h")
    usage: -a A [f2 -b | f3 -c C]
    >>> tree.main("-a", "1")
    {'f1': {'a': 1}}
    >>> tree.main("-a", "1", "f2", "-b")
    {'f2': {'a': 1, 'b': True}}
    >>> tree.main("-a", "1", "f3", "-c", "x")
    {'f3': {'a': 1, 'c': 'x'}}
    """

    children: List[Node] = field(default_factory=list)
    required: bool = False

    def command(
        self,
        flip_bools: bool = True,
        help: Optional[Dict[str, str]] = None,
        required: bool = False,
        strings: Optional[Dict[str, str]] = None,
        types: Optional[Dict[str, Callable[[str], Any]]] = None,
    ) -> Callable:
        return self.decorator(
            flip_bools=flip_bools,
            help=help,
            required=required,
            strings=strings,
            subcommand=False,
            types=types,
        )

    def decorator(self, **kwargs) -> Callable:
        def wrapper(function: Callable):
            tree = CommandTree()
            self.children.append(Node(function=function, tree=tree, **kwargs))
            return tree

        return wrapper

    def parser(self, *variables: str) -> Parser[FunctionPair[KeyValue[Any]]]:
        if not self.children:
            raise RuntimeError(
                "You must assign children to a CommandTree object in order to use it as a parser."
            )

        def get_alternatives() -> Iterator[Parser[FunctionPair[KeyValue[Any]]]]:
            for child in self.children:
                parser: Parser[FunctionPair[KeyValue[Any]]] = child.parser(*variables)
                if child.tree is not None and child.tree.children:
                    parser = cast(
                        Parser[FunctionPair[KeyValue[Any]]],
                        parser
                        >> child.tree.parser(*variables, *child.variable_names()),
                    )
                yield parser

        return wrap_help(reduce(operator.or_, get_alternatives()))

    def main(self, *args: str) -> Any:
        _args = args if args or parser_mod.TESTING else sys.argv[1:]
        p = self.parser() >> done()
        result = p.parse(Sequence(list(_args))).get
        if isinstance(result, ArgumentError):
            p.handle_error(result)
            if parser_mod.TESTING:
                return  # type: ignore[return-value]
            else:
                exit()
        assert isinstance(result, NonemptyList)
        pair = cast(FunctionPair, result.head.parsed)
        return pair.function(**{kv.key: kv.value for kv in pair.get})

    def subcommand(
        self,
        flip_bools: bool = True,
        help: Optional[Dict[str, str]] = None,
        required: bool = False,
        strings: Optional[Dict[str, str]] = None,
        types: Optional[Dict[str, Callable[[str], Any]]] = None,
    ) -> Callable:
        return self.decorator(
            flip_bools=flip_bools,
            help=help,
            required=required,
            types=types,
            strings=strings,
            subcommand=True,
        )
