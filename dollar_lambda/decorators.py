"""
Defines the `command` decorator and the `CommandTree` class.
"""
import operator
import sys
from dataclasses import dataclass, field, replace
from functools import reduce
from inspect import Parameter, signature
from typing import Any, Callable, Dict, Iterator, List, Optional, Type, TypeVar, cast

from pytypeclass.nonempty_list import NonemptyList

from dollar_lambda import parser as parser_mod
from dollar_lambda.args import _ArgsField
from dollar_lambda.error import ArgumentError
from dollar_lambda.key_value import KeyValue
from dollar_lambda.parser import Parse, Parser, done, equals, wrap_help
from dollar_lambda.result import Result
from dollar_lambda.sequence import Sequence

A = TypeVar("A")
B = TypeVar("B")
A_co = TypeVar("A_co", covariant=True)


def _func_to_parser(
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

    parsers = [
        _ArgsField(
            name=k,
            default=None if v.default == Parameter.empty else v.default,
            help=_help.get(k),
            string=_strings.get(k),
            type=_types.get(k, v.annotation),
        )
        for k, v in signature(func).parameters.items()
        if k not in _exclude
    ]
    return _ArgsField.nonpositional(
        *parsers,
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

    help : dict[str, str]
        A dictionary of help strings for the arguments.

    strings : dict[str, str]
        This dictionary maps variable names to the strings that the parser will look for in the input.

    types: dict[str, Callable[[str], Any]]
        This dictionary maps variable names to custom type converters.

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

    Here is an example using the `strings` parameter:

    >>> @command(strings=dict(quiet="--quiet-mode"))
    ... def f(quiet: bool):
    ...     return dict(quiet=quiet)
    >>> f("--quiet-mode")
    {'quiet': True}
    >>> f("--quiet")
    usage: --quiet-mode
    Expected '--quiet-mode'. Got '--quiet'

    Here is an example using the `type` parameter:

    >>> @command(types=dict(x=lambda x: int(x) + 1))
    ... def f(x: int):
    ...     return dict(x=x)
    >>> f("-x", "0")
    {'x': 1}
    """

    def wrapper(func: Callable) -> Callable:
        p = (
            _func_to_parser(
                func, flip_bools=flip_bools, help=help, strings=strings, types=types
            )
            >> done()
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
class _FunctionPair(Sequence[A]):
    function: Callable

    def __or__(self, other: Sequence[B]) -> "_FunctionPair[A | B]":  # type: ignore[override]
        function = other.function if isinstance(other, _FunctionPair) else self.function
        return _FunctionPair(get=[*self, *other], function=function)

    @classmethod
    def command(
        cls: Type["_FunctionPair[A]"],
        func: Callable,
        usage: Optional[str] = None,
        help: Optional[Dict[str, str]] = None,
    ) -> Parser["_FunctionPair[A]"]:
        _help = {} if help is None else help
        return Parser[_FunctionPair[A]](
            lambda cs: Result.return_(
                Parse(parsed=_FunctionPair(Sequence[A]([]), func), unparsed=cs)
            ),
            usage=usage,
            helps=_help,
        )

    @classmethod
    def subcommand(
        cls: Type["_FunctionPair[A]"],
        func: Callable,
        usage: Optional[str] = None,
        help: Optional[Dict[str, str]] = None,
    ) -> Parser["_FunctionPair[KeyValue[str]]"]:
        _help = {} if help is None else help

        # def f(
        #     _: Sequence[KeyValue[str]],
        # ) -> Parser[FunctionPair[KeyValue[str]]]:
        #     return Parser[FunctionPair[KeyValue[str]]](g, usage=usage, helps=_help)

        def g(
            cs: Sequence[str],
        ) -> Result[Parse[_FunctionPair[KeyValue[str]]]]:
            return Result.return_(
                Parse(parsed=_FunctionPair(Sequence([]), func), unparsed=cs)
            )

        eq = equals(func.__name__)
        p = eq >= (
            lambda _: Parser[_FunctionPair[KeyValue[str]]](g, usage=usage, helps=_help)
        )
        return replace(p, usage=eq.usage, helps=eq.helps)


@dataclass
class _Node:
    function: Callable
    flip_bools: bool
    help: Optional[Dict[str, str]]
    required: bool
    strings: Optional[Dict[str, str]]
    types: Optional[Dict[str, Callable[[str], Any]]]
    subcommand: bool
    tree: Optional["CommandTree"]

    def parser(self, *exclude: str) -> Parser[_FunctionPair[KeyValue[Any]]]:
        p1 = (
            _FunctionPair[KeyValue[Any]].subcommand(self.function)
            if self.subcommand
            else _FunctionPair[KeyValue[Any]].command(self.function)
        )
        p2 = _func_to_parser(
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
    Allows parsers to dynamically dispatch their results based on the input. For usage details,
    see the [`CommandTree` tutorial](#commandtree-tutorial).
    """

    _children: List[_Node] = field(default_factory=list)
    _required: bool = False

    def command(
        self,
        flip_bools: bool = True,
        help: Optional[Dict[str, str]] = None,
        required: bool = True,
        strings: Optional[Dict[str, str]] = None,
        types: Optional[Dict[str, Callable[[str], Any]]] = None,
    ) -> Callable:
        """
        A decorator for adding a function as a child of this tree.

        Parameters
        ----------

        flip_bools: bool
            Whether to add `--no-<argument>` before arguments that default to `True`.

        help: dict
            A dictionary of help strings for the arguments.

        required: bool
            If any sibling child functions are not required, then the user will be
            able to invoke the parent function by not selecting any of the child functions.

        strings: dict
            A dictionary of strings to use for the arguments.

        types: dict
            A dictionary of types to use for the arguments.

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


        Here is an example of how the `required` argument works:

        >>> tree = CommandTree()
        ...
        >>> @tree.command()
        ... def f1(a: int):
        ...     # this function can be called because one of the children (f2) is not required
        ...     return dict(f1=dict(a=a))
        ...
        >>> @f1.command(required=False)
        ... def f2(a:int, b: bool):
        ...     return dict(f2=dict(b=b))
        ...
        >>> @f1.command()
        ... def f3(a: int, c: str):
        ...     return dict(f3=dict(c=c))

        Now we invoke `tree` without calling `f2` or `f3`:
        >>> tree("-a", "1")
        {'f1': {'a': 1}}
        """
        return self._decorator(
            flip_bools=flip_bools,
            help=help,
            required=required,
            strings=strings,
            subcommand=False,
            types=types,
        )

    def _decorator(self, **kwargs) -> Callable:
        def wrapper(function: Callable):
            tree = CommandTree()
            self._children.append(_Node(function=function, tree=tree, **kwargs))
            return tree

        return wrapper

    def _parser(self, *variables: str) -> Parser[_FunctionPair[KeyValue[Any]]]:
        if not self._children:
            raise RuntimeError(
                "You must assign children to a CommandTree object in order to use it as a parser."
            )

        def get_alternatives() -> Iterator[Parser[_FunctionPair[KeyValue[Any]]]]:
            for child in self._children:
                parser: Parser[_FunctionPair[KeyValue[Any]]] = child.parser(*variables)
                if child.tree is not None and child.tree._children:
                    parser = cast(
                        Parser[_FunctionPair[KeyValue[Any]]],
                        parser
                        >> child.tree._parser(*variables, *child.variable_names()),
                    )
                yield parser

        return wrap_help(reduce(operator.or_, get_alternatives()))

    def __call__(self, *args: str) -> Any:
        """
        Run the parser associated with this tree and execute the
        function associated with a succeeding parser.

        If `args` is empty, uses `sys.argv[1:]`.
        """
        _args = args if args or parser_mod.TESTING else sys.argv[1:]
        p = self._parser() >> done()
        result = p.parse(Sequence(list(_args))).get
        if isinstance(result, ArgumentError):
            p.handle_error(result)
            if parser_mod.TESTING:
                return  # type: ignore[return-value]
            else:
                exit()
        assert isinstance(result, NonemptyList)
        pair = cast(_FunctionPair, result.head.parsed)
        return pair.function(**{kv.key: kv.value for kv in pair.get})

    def subcommand(
        self,
        flip_bools: bool = True,
        help: Optional[Dict[str, str]] = None,
        required: bool = False,
        strings: Optional[Dict[str, str]] = None,
        types: Optional[Dict[str, Callable[[str], Any]]] = None,
    ) -> Callable:
        """
        A decorator for adding a function as a child of this tree.
        As a subcommand, the function's name must be invoked on the command
        line for the function to be called.

        Parameters
        ----------

        flip_bools: bool
            Whether to add `--no-<argument>` before arguments that default to `True`.

        help: dict
            A dictionary of help strings for the arguments.

        required: bool
            If any sibling child functions are not required, then the user will be
            able to invoke the parent function by not selecting any of the child functions.

        strings: dict
            A dictionary of strings to use for the arguments.

        types: dict
            A dictionary of types to use for the arguments.

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


        Here is an example of how the `required` argument works:

        >>> tree = CommandTree()
        ...
        >>> @tree.command()
        ... def f1(a: int):
        ...     # this function can be called because one of the children (f2) is not required
        ...     return dict(f1=dict(a=a))
        ...
        >>> @f1.subcommand(required=False)
        ... def f2(a:int, b: bool):
        ...     return dict(f2=dict(b=b))
        ...
        >>> @f1.subcommand()
        ... def f3(a: int, c: str):
        ...     return dict(f3=dict(c=c))

        Now we invoke `tree` without calling `f2` or `f3`:
        >>> tree("-a", "1")
        {'f1': {'a': 1}}
        """
        return self._decorator(
            flip_bools=flip_bools,
            help=help,
            required=required,
            types=types,
            strings=strings,
            subcommand=True,
        )
