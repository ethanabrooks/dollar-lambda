"""
Defines the `command` decorator and the `CommandTree` class.
"""
from __future__ import annotations

import operator
import sys
import typing
from dataclasses import dataclass, field, replace
from functools import reduce
from inspect import Parameter, signature
from typing import Any, Callable, Iterator, List, Optional, Type, TypeVar

from pytypeclass import Monoid
from pytypeclass.nonempty_list import NonemptyList

from dollar_lambda import parser as parser_mod
from dollar_lambda.args import _ArgsField
from dollar_lambda.error import ArgumentError
from dollar_lambda.parser import Parse, Parser, matches
from dollar_lambda.result import Result
from dollar_lambda.sequence import KeyValue, Output, Sequence

A = TypeVar("A")
B = TypeVar("B")
A_co = TypeVar("A_co", covariant=True)


def _func_to_parser(
    func: Callable,
    exclude: Optional[List[str]],
    flip_bools: bool,
    help: Optional[typing.Dict[str, str]],
    parsers: Optional[typing.Dict[str, Parser[Output]]],
    repeated: Optional[Parser[Output]],
) -> Parser:
    _exclude = [] if exclude is None else exclude
    _help = {} if help is None else help
    _parsers = {} if parsers is None else parsers

    types = typing.get_type_hints(func)  # see https://peps.python.org/pep-0563/
    p = [
        _parsers.get(
            k,
            _ArgsField(
                name=k,
                default=None if v.default == Parameter.empty else v.default,
                help=_help.get(k),
                type=types.get(k, str),
            ),
        )
        for k, v in signature(func).parameters.items()
        if k not in _exclude
    ]
    return _ArgsField.parser(*p, flip_bools=flip_bools, repeated=repeated)


def command(
    flip_bools: bool = True,
    help: Optional[typing.Dict[str, str]] = None,
    parsers: Optional[typing.Dict[str, Parser[Output]]] = None,
    repeated: Optional[Parser[Output]] = None,
) -> Callable[[Callable], Callable]:
    """
    A succinct way to generate a simple `nonpositional` parser. `@command` derives the
    component parsers from the function's signature and automatically executes the function with
    the parsed arguments, if parsing succeeds:

    >>> @command(help=dict(a="something about a"))
    ... def f(a: int = 1, b: bool = False):
    ...     return dict(a=a, b=b)
    >>> f("-a", "2", "-b")
    {'a': 2, 'b': True}

    If the wrapped function receives no arguments (as in `f()`), the parser will take
    `sys.argv[1:]` as the input.

    Note that `@command` does not handle mutually exclusive arguments or alternative
    arguments.

    Parameters
    ----------
    flip_bools : bool
        For boolean arguments that default to true, this changes the flag from `--{dest}` to `--no-{dest}`:

    help : dict[str, str]
        A dictionary of help strings for the arguments.

    repeated: Optional[Parser[Sequence[KeyValue[Any]]]]
        If provided, this parser gets applied repeatedly (zero or more times) at all positions.

    strings : dict[str, str]
        This dictionary maps variable names to the strings that the parser will look for in the input.

    Examples
    --------

    >>> @command()
    ... def f(cuda: bool = True):
    ...     return dict(cuda=cuda)
    >>> f()
    {'cuda': True}
    >>> f("--no-cuda")  # flip_bools adds --no- to the flag
    {'cuda': False}

    As the following example demonstrates, when `flip_bools=False` output can be somewhat confusing:

    >>> @command(flip_bools=False)
    ... def f(cuda: bool = True):
    ...     return dict(cuda=cuda)
    >>> f("--cuda")
    {'cuda': False}

    Here is an example using the `help` parameter:

    >>> @command(help=dict(quiet="Be quiet"))
    ... def f(quiet: bool):
    ...     return dict(quiet=quiet)
    >>> f("--help")
    usage: --quiet
    quiet: Be quiet

    Here is an example using the `parser` parameter:

    TODO!
    """

    def wrapper(func: Callable) -> Callable:
        p = _func_to_parser(
            func,
            exclude=None,
            flip_bools=flip_bools,
            help=help,
            parsers=parsers,
            repeated=repeated,
        )
        p = p.wrap_help()

        def wrapped(*args) -> Any:
            parsed = p.parse_args(*args)
            if parsed is None:
                return
            return func(**parsed)

        return wrapped

    return wrapper


@dataclass
class _FunctionPair(Monoid[A_co]):
    seq: Sequence[KeyValue[A_co]]
    function: Optional[Callable]

    def __add__(self: "_FunctionPair[A]", other: "_FunctionPair[B] | Sequence[KeyValue[B]]") -> "_FunctionPair[A | B]":  # type: ignore[override]
        return self.add(other)

    def __or__(self: "_FunctionPair[A]", other: "_FunctionPair[B] | Sequence[KeyValue[B]]") -> "_FunctionPair[A | B]":  # type: ignore[override]
        return self.add(other)

    def add(self: "_FunctionPair[A]", other: "_FunctionPair[B] | Sequence[KeyValue[B]]") -> "_FunctionPair[A | B]":  # type: ignore[override]
        if isinstance(other, Sequence):
            function = self.function
            seq = other
        else:
            function = self.function if other.function is None else other.function
            seq = other.seq
        return _FunctionPair(seq=self.seq | seq, function=function)

    @classmethod
    def command(
        cls: Type["_FunctionPair[Sequence[KeyValue[Any]]]"],
        func: Callable,
        usage: Optional[str] = None,
        help: Optional[typing.Dict[str, str]] = None,
    ) -> Parser[Output["_FunctionPair[Any]"]]:
        _help = {} if help is None else help

        def f(
            cs: Sequence[str],
        ) -> Result[Parse[Output[_FunctionPair[Sequence[KeyValue[Any]]]]]]:
            return Result.return_(
                Parse(
                    parsed=Output(_FunctionPair(Sequence[KeyValue[Any]].zero(), func)),
                    unparsed=cs,
                )
            )

        return Parser(f, usage=usage, helps=_help)

    @classmethod
    def subcommand(
        cls: Type["_FunctionPair[A]"],
        func: Callable,
        usage: Optional[str] = None,
        help: Optional[typing.Dict[str, str]] = None,
    ) -> Parser[Output["_FunctionPair[str]"]]:
        _help = {} if help is None else help

        # def f(
        #     _: Sequence[KeyValue[str]],
        # ) -> Parser[FunctionPair[KeyValue[str]]]:
        #     return Parser[FunctionPair[KeyValue[str]]](g, usage=usage, helps=_help)

        def g(
            cs: Sequence[str],
        ) -> Result[Parse[Output[_FunctionPair[str]]]]:
            return Result.return_(
                Parse(
                    parsed=Output(_FunctionPair(Sequence[KeyValue[str]].zero(), func)),
                    unparsed=cs,
                )
            )

        eq = matches(func.__name__)
        p = eq >= (
            lambda _: Parser[Output[_FunctionPair[str]]](g, usage=usage, helps=_help)
        )
        return replace(p, usage=eq.usage, helps=eq.helps)

    @classmethod
    def zero(cls: Type[Monoid[A]]) -> Monoid[A]:
        return _FunctionPair(Sequence[KeyValue[A]].zero(), function=None)


@dataclass
class _Node:
    can_run: bool
    function: Callable
    flip_bools: bool
    help: Optional[typing.Dict[str, str]]
    parsers: Optional[typing.Dict[str, Parser[Output]]]
    repeated: Optional[Parser[Output]]
    subcommand: bool
    tree: Optional["CommandTree"]

    def parser(self, *exclude: str) -> Parser[Output[_FunctionPair[Any]]]:
        p1: Parser[Output[_FunctionPair[str]]] = (
            _FunctionPair.subcommand(self.function)
            if self.subcommand
            else _FunctionPair[Any].command(self.function)
        )
        p2: Parser[Output[_FunctionPair[str]]] = _func_to_parser(
            self.function,
            exclude=list(exclude),
            flip_bools=self.flip_bools,
            help=self.help,
            parsers=self.parsers,
            repeated=self.repeated,
        )
        return p1 >> p2

    def variable_names(self) -> Iterator[str]:
        yield from signature(self.function).parameters.keys()


@dataclass
class CommandTree:
    """
    Allows parsers to dynamically dispatch their results based on the input. For usage details,
    see the [`CommandTree` tutorial](#commandtree-tutorial).
    """

    _children: List[_Node] = field(default_factory=list)
    _can_run: bool = True

    def command(
        self,
        can_run: bool = True,
        flip_bools: bool = True,
        help: Optional[typing.Dict[str, str]] = None,
        parsers: Optional[typing.Dict[str, Parser[Output]]] = None,
        repeated: Optional[Parser[Output]] = None,
    ) -> Callable:
        """
        A decorator for adding a function as a child of this tree.

        Parameters
        ----------

        can_run: bool
            Whether the parser will permit the decorated function to run if no further arguments are supplied.

        flip_bools: bool
            Whether to add `--no-<argument>` before arguments that default to `True`.

        help: dict
            A dictionary of help strings for the arguments.

        repeated: Optional[Parser[Sequence[KeyValue[Any]]]]
            If provided, this parser gets applied repeatedly (zero or more times) at all positions.

        parsers: dict
            TODO

        Examples
        --------
        With `flip_bools` set to `True`:
        >>> tree = CommandTree()
        ...
        >>> @tree.command(flip_bools=True)
        ... def f1(b: bool = True):
        ...     return dict(f1=dict(b=b))
        ...
        >>> tree("-h")
        usage: --no-b
        b: (default: True)

        With `flip_bools` set to `False`:

        >>> tree = CommandTree()
        ...
        >>> @tree.command(flip_bools=False)
        ... def f1(b: bool = True):
        ...     return dict(f1=dict(b=b))
        ...
        >>> tree("-h")
        usage: -b
        b: (default: True)


        With `can_run` set to `True` (the default), we can run `f1` by not passing arguments
        for the `f1`'s children:

        >>> tree = CommandTree()
        ...
        >>> @tree.command(can_run=True)  # <-
        ... def f1(b: bool):
        ...     return dict(f1=dict(b=b))
        ...
        >>> @f1.command()
        ... def g1(n: int):
        ...     return dict(g1=dict(b=b, n=n))
        ...
        >>> tree("-h")
        usage: -b -n N

        >>> tree("-b")
        {'f1': {'b': True}}

        With `can_run` set to `False`, the parser will fail if the child function arguments
        are not supplied:


        >>> tree = CommandTree()
        ...
        >>> @tree.command(can_run=False)  # <-
        ... def f1(b: bool):
        ...     return dict(f1=dict(b=b))
        ...
        >>> @f1.command()
        ... def g1(n: int):
        ...     return dict(g1=dict(b=b, n=n))
        ...
        >>> tree("-h")
        usage: -b -n N

        >>> tree("f1", "-b")
        usage: -b -n N
        Expected '-b'. Got 'f1'
        """
        return self._decorator(
            can_run=can_run,
            flip_bools=flip_bools,
            help=help,
            parsers=parsers,
            repeated=repeated,
            subcommand=False,
        )

    def _decorator(self, **kwargs) -> Callable:
        def wrapper(function: Callable):
            tree = CommandTree()
            self._children.append(_Node(function=function, tree=tree, **kwargs))
            return tree

        return wrapper

    def _parser(self, *variables: str) -> Parser[Output[_FunctionPair[Any]]]:
        if not self._children:
            raise RuntimeError(
                "You must assign children to a CommandTree object in order to use it as a parser."
            )

        def get_alternatives() -> Iterator[Parser[Output[_FunctionPair[Any]]]]:
            for child in self._children:
                parser: Parser[Output[_FunctionPair[Any]]] = child.parser(*variables)
                if child.tree is not None and child.tree._children:
                    child_parser = child.tree._parser(
                        *variables, *child.variable_names()
                    )
                    if child.can_run:
                        child_parser = (
                            child_parser | Parser[Output[_FunctionPair[Any]]].done()
                        )
                    parser = parser >> child_parser
                yield parser

        return reduce(operator.or_, get_alternatives()).wrap_help()

    def __call__(self, *args: str) -> Any:
        """
        Run the parser associated with this tree and execute the
        function associated with a succeeding parser.

        If `args` is empty, uses `sys.argv[1:]`.
        """
        _args = args if args or parser_mod.TESTING else sys.argv[1:]
        p = self._parser() >> Parser[Output[_FunctionPair[Any]]].done()
        result = p.parse(Sequence(list(_args))).get
        if isinstance(result, ArgumentError):
            p.handle_error(result)
            if parser_mod.TESTING:
                return  # type: ignore[return-value]
            else:
                exit()
        assert isinstance(result, NonemptyList)
        pair = result.head.parsed.get
        assert pair.function is not None
        return pair.function(**pair.seq.to_dict())

    def subcommand(
        self,
        can_run: bool = True,
        flip_bools: bool = True,
        help: Optional[typing.Dict[str, str]] = None,
        parsers: Optional[typing.Dict[str, Optional[Parser[Output]]]] = None,
        repeated: Optional[Parser[Output]] = None,
    ) -> Callable:
        """
        A decorator for adding a function as a child of this tree.
        As a subcommand, the function's name must be invoked on the command
        line for the function to be called.

        Parameters
        ----------

        can_run: bool
            Whether the parser will permit the decorated function to run if no further arguments are supplied.

        flip_bools: bool
            Whether to add `--no-<argument>` before arguments that default to `True`.

        help: Dict[str, str]
            A dictionary of help strings for the arguments.

        repeated: Optional[Parser[Sequence[KeyValue[Any]]]]
            If provided, this parser gets applied repeatedly (zero or more times) at all positions.
            See `nonpositional` for examples.

        parsers: Dict[str, Parser]
            A dictionary reserving arguments for custom parsers. See below for examples.
            See `command` for examples.

        Examples
        --------
        With `flip_bools` set to `True`:
        >>> tree = CommandTree()
        ...
        >>> @tree.subcommand(flip_bools=True)
        ... def f1(b: bool = True):
        ...     return dict(f1=dict(b=b))
        ...
        >>> tree("-h")
        usage: f1 --no-b
        b: (default: True)

        With `flip_bools` set to `False`:

        >>> tree = CommandTree()
        ...
        >>> @tree.subcommand(flip_bools=False)
        ... def f1(b: bool = True):
        ...     return dict(f1=dict(b=b))
        ...
        >>> tree("-h")
        usage: f1 -b
        b: (default: True)

        With `can_run` set to `True` (the default), we can run `f1` by not passing arguments
        for the `f1`'s children:

        >>> tree = CommandTree()
        ...
        >>> @tree.subcommand(can_run=True)  # <-
        ... def f1(b: bool):
        ...     return dict(f1=dict(b=b))
        ...
        >>> @f1.subcommand()
        ... def g1(b: bool, n: int):
        ...     return dict(g1=dict(b=b, n=n))
        ...
        >>> tree("-h")
        usage: f1 -b g1 -n N

        >>> tree("f1", "-b")
        {'f1': {'b': True}}

        With `can_run` set to `False`, the parser will fail if the child function arguments
        are not supplied:

        >>> tree = CommandTree()
        ...
        >>> @tree.subcommand(can_run=False)  # <-
        ... def f1(b: bool):
        ...     return dict(f1=dict(b=b))
        ...
        >>> @f1.subcommand()
        ... def g1(b: bool, n: int):
        ...     return dict(g1=dict(b=b, n=n))
        ...
        >>> tree("-h")
        usage: f1 -b g1 -n N

        >>> tree("f1", "-b")
        usage: f1 -b g1 -n N
        The following arguments are required: g1
        """
        return self._decorator(
            can_run=can_run,
            flip_bools=flip_bools,
            help=help,
            repeated=repeated,
            parsers=parsers,
            subcommand=True,
        )
