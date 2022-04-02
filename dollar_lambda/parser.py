"""
Defines parsing functions and the `Parser` class that they instantiate.
"""
# pyright: reportGeneralTypeIssues=false
from __future__ import annotations

import operator
import os
import re
import sys
from dataclasses import astuple, dataclass, replace
from functools import lru_cache, partial, reduce
from typing import Any, Callable, Dict, Generic, Optional, Type, TypeVar

from pytypeclass import Monad, MonadPlus, Monoid
from pytypeclass.nonempty_list import NonemptyList

from dollar_lambda.error import (
    ArgumentError,
    BinaryError,
    HelpError,
    MissingError,
    UnequalError,
    UnexpectedError,
)
from dollar_lambda.result import Result
from dollar_lambda.sequence import KeyValue, Output, Sequence, TreePath

A_co = TypeVar("A_co", covariant=True)
A_monoid = TypeVar("A_monoid", bound=Monoid)
B_monoid = TypeVar("B_monoid", bound=Monoid)
A = TypeVar("A")
B = TypeVar("B")

global TESTING
TESTING = os.environ.get("DOLLAR_LAMBDA_TESTING", False)


@dataclass
class Parse(Generic[A_co]):
    """
    A `Parse` is the output of parsing.

    Parameters
    ----------
    parsed : A
        Component parsed by the parsed
    unparsed : Sequence[str]
        Component yet to be parsed
    """

    parsed: A_co
    unparsed: Sequence[str]


@dataclass
class SuccessError(ArgumentError, Generic[A_monoid]):
    input: Sequence[str]
    output: NonemptyList[Parse[A_monoid]]


def binary_usage(a: Optional[str], op: str, b: Optional[str], add_brackets=True):
    """
    Utility for generating usage strings for binary operators.
    """
    no_nones = [x for x in (a, b) if x is not None]
    usage = op.join(no_nones)
    if len(no_nones) > 1 and add_brackets:
        usage = f"[{usage}]"
    return usage or None


@dataclass
class Parser(MonadPlus[A_co]):
    """
    Main class powering the argument parser.
    """

    f: Callable[[Sequence[str]], Result[Parse[A_co]]]
    usage: Optional[str]
    helps: Dict[str, str]

    def __add__(
        self: "Parser[Output[A_monoid]]", other: "Parser[Output[B_monoid]]"
    ) -> "Parser[Output[A_monoid | B_monoid]]":
        """
        Parse two arguments in either order.
        >>> p = flag("verbose") + flag("debug")
        >>> p.parse_args("--verbose", "--debug")
        {'verbose': True, 'debug': True}
        >>> p.parse_args("--debug", "--verbose")
        {'debug': True, 'verbose': True}
        >>> p.parse_args("--debug")
        usage: --verbose --debug
        Expected '--verbose'. Got '--debug'

        Note that if more than two arguments are chained together with `+`, some combinations will not parse:
        >>> p = flag("a") + flag("b") + flag("c")
        >>> p.parse_args("-c", "-a", "-b")   # this works
        {'c': True, 'a': True, 'b': True}
        >>> p.parse_args("-a", "-c", "-b")   # this doesn't
        usage: -a -b -c
        Expected '-b'. Got '-c'

        This makes more sense when one supplies the implicit parentheses:
        >>> p = (flag("a") + flag("b")) + flag("c")

        In order to chain together more than two arguments, use `nonpositional`:
        >>> p = nonpositional(flag("a"), flag("b"), flag("c"))
        >>> p.parse_args("-a", "-c", "-b")
        {'a': True, 'c': True, 'b': True}
        """
        p = (self >> other) | (other.rshift(self))
        usage = binary_usage(self.usage, " ", other.usage, add_brackets=False)
        return replace(p, usage=usage)

    def __ge__(self, f: Callable[[A_co], Monad[B_monoid]]) -> "Parser[B_monoid]":  # type: ignore[override]
        return self.bind(f)

    def __or__(  # type: ignore[override]
        self: "Parser[A_monoid]",
        other: "Parser[B_monoid]",
    ) -> "Parser[A_monoid | B_monoid]":
        """
        Tries apply the first parser. If it fails, tries the second. If that fails, the parser fails.

        >>> from dollar_lambda import argument, option, flag
        >>> p = option("option") | flag("verbose")
        >>> p.parse_args("--option", "x")
        {'option': 'x'}
        >>> p.parse_args("--verbose")
        {'verbose': True}

        Note that by default, `parse_args` adds `>> Parser.done()` to the end of parsers, causing
        `p` to fail when both arguments are supplied:

        >>> p.parse_args("--verbose", "--option", "x")
        usage: [--option OPTION | --verbose]
        Unrecognized argument: --option

        To disable this behavior, use `allow_unparsed`:
        >>> p.parse_args("--verbose", "--option", "x", allow_unparsed=True)
        {'verbose': True}
        """

        def f(cs: Sequence[str]) -> Result[Parse["A_monoid | B_monoid"]]:
            return self.parse(cs) | other.parse(cs)

        return Parser(
            f,
            usage=binary_usage(self.usage, " | ", other.usage),
            helps={**self.helps, **other.helps},
        )

    def rshift(
        self: "Parser[Output[A_monoid]]", p: "Parser[Output[B_monoid]]"
    ) -> "Parser[Output[A_monoid | B_monoid]]":
        return self >> p

    def __rshift__(
        self: "Parser[Output[A_monoid]]", p: "Parser[Output[B_monoid]]"
    ) -> "Parser[Output[A_monoid | B_monoid]]":
        """
        This applies parsers in sequence. If the first parser succeeds, the unparsed remainder
        gets handed off to the second parser. If either parser fails, the whole thing fails.

        >>> from dollar_lambda import argument, flag
        >>> p = argument("first") >> argument("second")
        >>> p.parse_args("a", "b")
        {'first': 'a', 'second': 'b'}
        >>> p.parse_args("a")
        usage: FIRST SECOND
        The following arguments are required: second
        >>> p.parse_args("b")
        usage: FIRST SECOND
        The following arguments are required: second
        """

        def f(p1: Output[A_monoid]) -> Parser[Output[A_monoid | B_monoid]]:
            def g(p2: Output[B_monoid]) -> Parser[Output[A_monoid | B_monoid]]:
                # _p1 = p1 if isinstance(p1, Sequence) else Sequence(p1)
                # _p2 = p2 if isinstance(p2, Sequence) else Sequence(p2)
                return Parser.return_(p1 + p2)

            return p >= g

        parser = self >= f
        # parser = self >= (lambda p1: (p >= (lambda p2: Parser.return_(p1 + p2))))
        return replace(
            parser,
            usage=binary_usage(self.usage, " ", p.usage, add_brackets=False),
            helps={**self.helps, **p.helps},
        )

    def __xor__(
        self: "Parser[Output[A_monoid]]", other: "Parser[Output[B_monoid]]"
    ) -> "Parser[Output[A_monoid | B_monoid]]":
        """
        This is the same as `__or__`, but it succeeds only if one of the two parsers fails.

        >>> p = argument("int", type=int) ^ argument("div", type=lambda x: 1 / float(x))
        >>> p.parse_args("inf")  # succeeds because int("inf") fails
        {'div': 0.0}
        >>> p.parse_args("0")  # succeeds because 1 / 0 throws an error
        {'int': 0}
        >>> p.parse_args("1")  # fails because both parsers succeed
        Both parsers succeeded. This causes ^ to fail.
        """
        p = (self.fails() >> other) | (other.fails() >> self)

        def f(error: ArgumentError) -> ArgumentError:
            if isinstance(error, BinaryError):
                return ArgumentError("Both parsers succeeded. This causes ^ to fail.")
            return error

        return p.map_error(f)

    def apply(self: "Parser[A_monoid]", f: Callable[[A_monoid], Result[B_monoid]]) -> "Parser[B_monoid]":  # type: ignore[misc]
        # see https://github.com/python/mypy/issues/6178#issuecomment-1057111790
        """
        Takes the output of `parser` and applies `f` to it. Convert any errors that arise into `ArgumentError`.

        >>> p1 = flag("hello")
        >>> p1.parse_args("--hello")
        {'hello': True}

        This will double `p1`'s output:
        >>> p2 = p1.apply(lambda out: Result.return_(out + out))
        >>> p2.parse_args("--hello")
        {'hello': [True, True]}
        """

        def g(a: A_monoid) -> Parser[B_monoid]:
            try:
                y = f(a)
            except Exception as e:
                usage = f"An argument {a}: raised exception {e}"
                y = Result(ArgumentError(usage))
            return Parser(
                lambda cs: y >= (lambda parsed: Result.return_(Parse(parsed, cs))),
                usage=self.usage,
                helps=self.helps,
            )

        p = self >= g
        return replace(p, usage=self.usage, helps=self.helps)

    def bind(self, f: Callable[[A_co], Monad[B_monoid]]) -> "Parser[B_monoid]":  # type: ignore[override]
        """
        Returns a new parser that

        1. applies `self`;
        2. if this succeeds, applies `f` to the parsed component of the result.

        `bind` is one of the functions that makes `Parser` a [`Monad`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monad.py#L16). But most users will
        avoid using it directly, preferring higher level combinators like `>>` (`Parser.__rshift__`),
        `|` (`Parser.__or__`) and `+` (`Parser.__add__`).

        Note that `>=` as a synonym for `bind` (as defined in [`pytypeclass`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monad.py#L26))
        and we typically prefer using the infix operator to the spelled out method.

        Let's start with our simplest parser, `argument`:
        >>> p1 = argument("some_dest")

        Now let's use the `matches` parser to write a function that takes the output of `p1` and fails unless
        the next argument is the same as the first:
        >>> def f(out: Output[Sequence[KeyValue[Any]]]) -> Parser[Output[str]]:
        ...     *_, kv = out.get
        ...     return matches(kv.value)

        >>> p = p1 >= f
        >>> p.parse_args("a", "a")
        {'a': 'a'}
        >>> p.parse_args("a", "b")
        Expected 'a'. Got 'b'
        """

        def h(parse: Parse[A_co]) -> Result[Parse[B_monoid]]:
            y = f(parse.parsed)
            assert isinstance(y, Parser), y
            return y.parse(parse.unparsed)

        def g(cs: Sequence[str]) -> Result[Parse[B_monoid]]:
            return self.parse(cs) >= h

        return Parser(g, usage=None, helps=self.helps)

    @classmethod
    def done(
        cls: Type["Parser[Output[A_monoid]]"], a: Optional[Type[A_monoid]] = None
    ) -> Parser[Output[Any]]:
        """
        `done` succeds on the end of input and fails on everything else.
        >>> Parser.done().parse_args()
        {}
        >>> Parser.done().parse_args("arg")
        Unrecognized argument: arg

        Without `done` the parser will not complain about leftover (unparsed) input:

        >>> flag("verbose").parse_args("--verbose", "--quiet", allow_unparsed=True)
        {'verbose': True}

        When `allow_unparsed=False` (the default), `parse_args` adds `>> Parser.done()`
        to the end of the parser:
        """

        def f(cs: Sequence[str]) -> Result[Parse[Output[Any]]]:
            if cs:
                c, *_ = cs
                return Result(
                    UnexpectedError(unexpected=c, usage=f"Unrecognized argument: {c}")
                )
            return Result(NonemptyList(Parse(parsed=Output.zero(a), unparsed=cs)))

        return Parser(f, usage=None, helps={})

    @classmethod
    def empty(
        cls: Type["Parser[Output[A_monoid]]"], a: Optional[Type[A_monoid]] = None
    ) -> "Parser[Output[A_monoid]]":
        """
        Always returns {}, no matter the input. Mostly useful for use in `nonpositional`.
        >>> Parser.empty().parse_args("any", "arguments", allow_unparsed=True)
        {}
        """
        return cls.return_(Output.zero(a))

    def fails(
        self: "Parser[Output[A_monoid]]", a: Optional[Type[A_monoid]] = None
    ) -> "Parser[Output[A_monoid]]":
        """
        Succeeds only if self fails. Does not consume any input.

        >>> flag("x").fails().parse_args("not x", allow_unparsed=True)  # succeeds
        {}
        >>> flag("x").fails().parse_args("-x", allow_unparsed=True)  # fails
        Parser unexpectedly succeeded.
        """

        def g(cs: Sequence[str]) -> Result[Parse[Output[A_monoid]]]:
            parse = self.parse(cs).get
            if isinstance(parse, Exception):
                return Result.return_(Parse(Output.zero(a), cs))
            else:
                return Result.zero(
                    error=SuccessError(
                        "Parser unexpectedly succeeded.", input=cs, output=parse
                    )
                )

        return Parser(g, usage=None, helps=self.helps)

    def handle_error(self, error: ArgumentError) -> None:
        def print_usage(usage: str):
            print("usage:", end="\n" if "\n" in usage else " ")
            if "\n" in usage:
                usage = "\n".join(["    " + u for u in usage.split("\n")])
            print(usage)
            if self.helps:
                for k, v in self.helps.items():
                    print(f"{k}: {v}")

        if isinstance(error, HelpError):
            print_usage(error.usage)
        else:
            if self.usage:
                print_usage(self.usage)
            if error.usage:
                print(error.usage)
        if TESTING:
            return
        else:
            exit()

    def ignore(
        self: "Parser[Output[A_monoid]]", a: Optional[Type[A_monoid]] = None
    ) -> "Parser[Output[A_monoid]]":
        """
        Ignores the output from a parser. This is useful when you expect
        to give arguments to the command line that some other utility will
        handle.

        >>> p = flag("hello").ignore()

        This will not bind any value to `"hello"`:
        >>> p.parse_args("--hello")
        {}

        But `--hello` is still required:
        >>> p.parse_args()
        The following arguments are required: --hello
        """

        def g(keep: Parse[Output[A_monoid]]) -> Result[Parse[Output[A_monoid]]]:
            return Result(NonemptyList(Parse(Output.zero(a), keep.unparsed)))

        def f(cs: Sequence[str]) -> Result[Parse[Output[A_monoid]]]:
            return self.parse(cs) >= g

        return Parser(f, usage=None, helps={})

    def many(
        self: "Parser[Output[A_monoid]]", max: Optional[int] = None
    ) -> "Parser[Output[A_monoid]]":
        """
        Applies `self` zero or more times (like `*` in regexes).

        >>> from dollar_lambda import argument, flag
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args()
        {}
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a")
        {'as-many-as-you-like': 'a'}
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a", "b")
        {'as-many-as-you-like': ['a', 'b']}

        Note that if `self` contains `Parser.__or__`, the arguments can be
        heterogenous:
        >>> p = flag("verbose") | flag("quiet")
        >>> p = p.many()
        >>> p.parse_args("--verbose", "--quiet") # mix --verbose and --quiet
        {'verbose': True, 'quiet': True}
        """
        if max == 0:
            p = self.empty()
        else:
            if max is not None:
                max -= 1
                assert max >= 0, max
            p = self.many1(max=max) | self.empty()
        return replace(p, usage=f"[{self.usage} ...]")

    def many1(
        self: "Parser[Output[A_monoid]]", max: Optional[int] = None
    ) -> "Parser[Output[A_monoid]]":
        """
        Applies `self` one or more times (like `+` in regexes).

        >>> from dollar_lambda import argument, flag
        >>> p = argument("1-or-more").many1()
        >>> p.parse_args("1")
        {'1-or-more': '1'}
        >>> p.parse_args("1", "2")
        {'1-or-more': ['1', '2']}
        >>> p.parse_args()
        usage: 1-OR-MORE [1-OR-MORE ...]
        The following arguments are required: 1-or-more
        """

        @lru_cache()
        def f(cs: tuple):
            y = self >> self.many(max=max)
            return y.parse(Sequence(list(cs)))

        return Parser(
            lambda cs: f(tuple(cs)),
            usage=f"{self.usage} [{self.usage} ...]",
            helps=self.helps,
        )

    def map_error(self, f: Callable[[ArgumentError], ArgumentError]) -> "Parser[A_co]":
        def g(cs: Sequence[str]) -> Result[Parse[A_co]]:
            parse = self.parse(cs)
            if isinstance(parse.get, ArgumentError):
                return Result.zero(error=f(parse.get))
            else:
                return parse

        return Parser(g, usage=None, helps=self.helps)

    def optional(self: "Parser[Output[A_monoid]]") -> "Parser[Output[A_monoid]]":
        """
        Allows arguments to be optional:
        >>> p1 = flag("optional")
        >>> p = p1.optional()
        >>> p.parse_args("--optional")
        {'optional': True}
        >>> p.parse_args("--misspelled", allow_unparsed=True)  # succeeds with no output
        {}
        >>> p1.parse_args("--misspelled")
        usage: --optional
        Expected '--optional'. Got '--misspelled'
        """
        return self | self.empty()

    def parse(self, cs: Sequence[str]) -> Result[Parse[A_co]]:
        """
        Applies the parser to the input sequence `cs`.
        """
        return self.f(cs)

    def parse_args(
        self: "Parser[Output]",
        *args: str,
        allow_unparsed: bool = False,
        check_help: bool = True,
    ) -> "Optional[Dict[str, Any]]":
        """
        The main way the user extracts parsed results from the parser.

        Parameters
        ----------
        args : str
            A sequence of strings to parse. If empty, defaults to `sys.argv[1:]`.
        allow_unparsed : bool
            Whether to cause parser to fail if there are unparsed inputs. Note that setting this to false
            may cause unexpected behavior when using `nonpositional` or `Args`.
        check_help : bool
            Before running the parser, checks if the input string is `--help` or `-h`.
            If it is, returns the usage message.

        Examples
        --------

        >>> argument("a").parse_args("-h")
        usage: A
        >>> argument("a").parse_args("--help")
        usage: A
        """
        _args = args if args or TESTING else sys.argv[1:]
        if not allow_unparsed:
            return (self >> Parser[Output].done()).parse_args(
                *_args,
                allow_unparsed=True,
                check_help=check_help,
            )
        if check_help:
            return self.wrap_help().parse_args(
                *_args,
                allow_unparsed=allow_unparsed,
                check_help=False,
            )
        result = self.parse(Sequence(list(_args))).get
        if isinstance(result, ArgumentError):
            self.handle_error(result)
            return None
        get = result.head.parsed.get
        assert isinstance(get, Sequence), get
        return get.to_dict()

    @classmethod
    def return_(cls, a: A_co) -> "Parser[A_co]":  # type: ignore[misc]
        # see https://github.com/python/mypy/issues/6178#issuecomment-1057111790
        """
        This method is required to make `Parser` a [`Monad`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monad.py#L16). It consumes none of the input
        and always returns `a` as the result. For the most part, the user will not use
        this method unless building custom parsers.

        >>> Parser.return_(Output.from_dict(some_key="some_value")).parse_args()
        {'some_key': 'some_value'}
        """

        def f(cs: Sequence[str]) -> Result[Parse[A_co]]:
            return Result.return_(Parse(a, cs))

        return Parser(f, usage=None, helps={})

    def sat(
        self: "Parser[A_monoid]",
        predicate: Callable[[A_monoid], bool],
        on_fail: Callable[[A_monoid], ArgumentError],
    ) -> "Parser[A_monoid]":
        """
        Applies `parser`, applies a predicate to the result and fails if this returns false.

        >>> p = option("x", type=int).many().sat(
        ...     lambda out: sum(out.get.values()) > 0,
        ...     lambda out: ArgumentError(f"The values in {list(out.get.values())} must sum to more than 0."),
        ... )
        >>> p.parse_args("-x", "-1", "-x", "1")  # fails
        usage: [-x X ...]
        The values in [-1, 1] must sum to more than 0.

        >>> p.parse_args("-x", "-1", "-x", "2")  # succeeds
        {'x': [-1, 2]}

        Parameters
        ----------
        parser : Parser[A]
            The parser to apply.
        predicate : Callable[[A], bool]
            The predicate to apply to the result of `parser`. `sat` fails if this predicate returns false.
        on_fail : Callable[[A], ArgumentError]
            A function producing an ArgumentError to return if the predicate fails.
            Takes the output of `parser` as an argument.
        """

        def f(x: A_monoid) -> Result[A_monoid]:
            return Result(NonemptyList(x) if predicate(x) else on_fail(x))

        return self.apply(f)

    def nesting(
        self: "Parser[Output[Sequence[KeyValue[Any]]]]",
    ) -> "Parser[Output[Sequence[KeyValue[Any]]]]":
        """
        A wrapper around `apply` that simply applies `f` to the value of the most recently parsed input.
        >>> p1 = option("x") >> option("y")
        >>> p = p1.type(int)
        >>> p.parse_args("-x", "1", "-y", "2")  # converts "1" but not "2"
        {'x': '1', 'y': 2}
        """

        def g(out: Output[Sequence[KeyValue[str]]]) -> Result[Output]:
            d = out.get
            if not d:
                raise RuntimeError("Invoked nested on a parser that returns no output.")
            *tail, head = out.get
            if "." in head.key:
                key, hd, *tl = head.key.split(".")
                parents = NonemptyList.make(hd, *tl)
                path = TreePath(parents, head.value)
                kv = KeyValue(key, path)
                return Result.return_(Output(Sequence([*tail, kv])))
            else:
                return Result.return_(out)

        p = self.apply(g)
        return replace(p, usage=self.usage, helps=self.helps)

    def type(
        self: "Parser[Output[Sequence[KeyValue[str]]]]", f: Callable[[str], Any]
    ) -> "Parser[Output[Sequence[KeyValue[str]]]]":
        """
        A wrapper around `apply` that simply applies `f` to the value of the most recently parsed input.
        >>> p1 = option("x") >> option("y")
        >>> p = p1.type(int)
        >>> p.parse_args("-x", "1", "-y", "2")  # converts "1" but not "2"
        {'x': '1', 'y': 2}
        """

        def g(out: Output[Sequence[KeyValue[str]]]) -> Result[Output]:
            d = out.get
            if not d:
                raise RuntimeError("Invoked type on a parser that returns no output.")
            *tail, head = out.get
            try:
                y = f(head.value)
            except Exception as e:
                usage = f"argument {head.value}: raised exception {e}"
                return Result(ArgumentError(usage))
            return Result.return_(Output(Sequence([*tail, KeyValue(head.key, y)])))

        p = self.apply(g)
        return replace(p, usage=self.usage, helps=self.helps)

    def wrap_error(self, error: ArgumentError) -> "Parser[A_co]":
        return self.map_error(lambda _: error)

    def wrap_help(
        self: "Parser[A_monoid]", a: Optional[Type[A_monoid]] = None
    ) -> "Parser[A_monoid]":
        """
        This checks for the `--help` or `-h` flag before applying `parser`.
        If either of the flags is present, returns the usage message for `parser`.

        >>> p = flag("help", help="Print this help message.").wrap_help()
        >>> p.parse_args("--help")
        usage: --help
        help: Print this help message.
        >>> p.parse_args("-h")
        usage: --help
        help: Print this help message.

        We can use `wrap_help` to print partial usage messages, e.g. for subcommands:
        >>> subcommand1 = matches("subcommand1") >> option("option1").wrap_help()
        >>> subcommand2 = matches("subcommand2") >> option("option2").wrap_help()
        >>> p = subcommand1 | subcommand2
        >>> p.parse_args("subcommand1", "-h")
        usage: --option1 OPTION1
        >>> p.parse_args("subcommand2", "-h")
        usage: --option2 OPTION2
        """
        _help_parser: Parser[Output[A_monoid]] = help_parser(self.usage, Output.zero(a))

        p = _help_parser >= (lambda _: self)
        return replace(p, usage=self.usage, helps=self.helps)

    @classmethod
    def zero(cls, error: Optional[ArgumentError] = None) -> "Parser[A_co]":
        """
        This parser always fails. This method is necessary to make `Parser` a [`Monoid`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monoid.py#L13).

        Parameters
        ----------
        error : Optional[ArgumentError]
            Customize the error returned by `zero`.

        >>> Parser.zero().parse_args()
        zero
        >>> Parser.zero().parse_args("a")
        zero
        >>> Parser.zero(error=ArgumentError("This is a test.")).parse_args("a")
        This is a test.
        """
        return Parser(lambda _: Result.zero(error=error), usage=None, helps={})


def apply(f: Callable[[str], B_monoid], description: str) -> Parser[B_monoid]:
    """
    A shortcut for
    ```python
    item(description).apply(f)
    ```
    and spares `f` the trouble of outputting a `Result` object.
    Here is an example of usage. First we define a simple `argument` parser:

    >>> p1 = argument("foo")
    >>> p1.parse_args("bar")
    {'foo': 'bar'}

    Here we use `f` to directly manipulate the binding generated by `item`:
    >>> p2 = apply(lambda bar: Output.from_dict(**{bar + "e": bar + "f"}), description="baz")
    >>> p2.parse_args("bar")
    {'bare': 'barf'}
    """

    def g(out: Output[Sequence[KeyValue[str]]]) -> Result[B_monoid]:
        *_, (_, v) = map(astuple, out.get)
        assert v is not None  # because item produces output
        try:
            y = f(v)
        except Exception as e:
            usage = f"argument {v} raised exception {e}"
            return Result(ArgumentError(usage))
        return Result.return_(y)

    return item(description).apply(g)


def argument(
    dest: str,
    nesting: bool = True,
    help: Optional[str] = None,
    type: Optional[Callable[[str], Any]] = None,
) -> Parser[Output]:
    """
    Parses a single word and binds it to `dest`.
    Useful for positional arguments.

    Parameters
    ----------
    dest : str
        The name of variable to bind to:

    nesting : bool
        If `True`, then the parser will split the parsed output on `.` yielding nested output.
        See Examples for more details.

    help : Optional[str]
        The help message to display for the option:

    type : Optional[Callable[[str], Any]]
        Use the `type` argument to convert the input to a different type:

    >>> argument("name").parse_args("Dante")
    {'name': 'Dante'}
    >>> argument("name").parse_args()
    usage: NAME
    The following arguments are required: name

    Here are some examples that take advantage of `nesting=True`:
    >>> argument("config.name").parse_args("-h")
    usage: CONFIG.NAME
    >>> argument("config.name").parse_args("Dante")
    {'config': {'name': 'Dante'}}

    Of course, you can disable this by setting `nesting=False`:
    >>> argument("config.name", nesting=False).parse_args("Dante")
    {'config.name': 'Dante'}
    >>> (argument("config.first.name") >> argument("config.last.name")).parse_args("Dante", "Alighieri")
    {'config': {'first': {'name': 'Dante'}, 'last': {'name': 'Alighieri'}}}
    """
    parser = item(dest)
    _type: Callable[[str], Any] = str if type is None else type  # type: ignore[assignment]
    # Mypy doesn't know that types also have type Callable[[str], Any]
    if _type is not str:
        parser = parser.type(_type)
    if nesting:
        parser = parser.nesting()
    helps = {dest: help} if help else {}
    parser = replace(parser, usage=dest.upper(), helps=helps)
    return parser


def defaults(**kwargs: A) -> Parser[Output[Sequence[KeyValue[A]]]]:
    """
    Useful for assigning default values to arguments.
    It ignore the input and always returns `kwargs` converted into `CollisionDict`.
    `defaults` never failsekpoi

    >>> defaults(a=1, b=2).parse_args()
    {'a': 1, 'b': 2}
    >>> (flag("fails") | defaults(fails="succeeds")).parse_args()
    {'fails': 'succeeds'}

    Here's a more complex example derived from the tutorial:
    >>> p = nonpositional(
    ...     (
    ...         flag("verbose") + defaults(quiet=False)  # either --verbose and default "quiet" to False
    ...         | flag("quiet") + defaults(verbose=False)  # or --quiet and default "verbose" to False
    ...     ),
    ...     option("x", type=int, help="the base"),
    ...     option("y", type=int, help="the exponent"),
    ... )

    >>> p.parse_args("-x", "1", "-y", "2", "--verbose")
    {'x': 1, 'y': 2, 'verbose': True, 'quiet': False}
    """
    p = Parser[Output[A_monoid]].return_(
        Output[Sequence[KeyValue[A]]].from_dict(**kwargs)
    )
    return replace(p, usage=None)


def matches(
    s: str, peak: bool = False, regex: bool = True
) -> Parser[Output[Sequence[KeyValue[str]]]]:
    """
    Checks if the next word is `s`.

    >>> matches("hello").parse_args("hello")
    {'hello': 'hello'}
    >>> matches("hello").parse_args("goodbye")
    usage: hello
    Expected 'hello'. Got 'goodbye'

    Parameters
    ----------
    s: str
        The word to that input will be checked against for equality.
    peak : bool
        If `False`, then the parser will consume the word and return the remaining words as `unparsed`.
        If `True`, then the parser leaves the `unparsed` component unchanged.

    regex : bool
        Whether to treat `s` as a regular expression. If `False`, then the parser will only succeed on
        string equality.

    Examples
    --------

    >>> p = matches("hello") >> matches("goodbye")
    >>> p.parse_args("hello", "goodbye")
    {'hello': 'hello', 'goodbye': 'goodbye'}

    Look what happens when `peak=True`:
    >>> p = matches("hello", peak=True) >> matches("goodbye")
    >>> p.parse_args("hello", "goodbye")
    usage: hello goodbye
    Expected 'goodbye'. Got 'hello'

    The first parser didn't consume the word and so "hello" got passed on to `equals("goodbye")`.
    But this would work:
    >>> p = matches("hello", peak=True) >> matches("hello") >> matches("goodbye")
    >>> p.parse_args("hello", "goodbye")
    {'hello': ['hello', 'hello'], 'goodbye': 'goodbye'}
    """

    def predicate(_s: str) -> bool:
        if regex:
            b = bool(re.match(s, _s))
            return b
        else:
            return s == _s

    if peak:
        return sat_peak(
            predicate=predicate,
            on_fail=lambda _s: UnequalError(
                left=s, right=_s, usage=f"Expected '{s}'. Got '{_s}'"
            ),
            name=s,
        )
    else:
        return sat(
            predicate=predicate,
            on_fail=lambda _s: UnequalError(
                left=s, right=_s, usage=f"Expected '{s}'. Got '{_s}'"
            ),
            name=s,
        )


def flag(
    dest: str,
    nesting: bool = True,
    default: Optional[bool] = None,
    help: Optional[str] = None,
    short: bool = True,
    string: Optional[str] = None,
) -> Parser[Output[Sequence[KeyValue[bool]]]]:
    """
    Binds a boolean value to a variable.

    >>> p = flag("verbose")
    >>> p.parse_args("--verbose")
    {'verbose': True}


    Parameters
    ----------
    dest : str
        The variable to which the value will be bound.

    nesting : bool
        If `True`, then the parser will split the parsed output on `.` yielding nested output.
        See Examples for more details.

    default : Optional[bool]
        An optional default value.

    help : Optional[str]
        An optional help string.

    short : bool
        Whether to check for the short form of the flag, which
        uses a single dash and the first character of `dest`, e.g. `-f` for `foo`.

    string : Optional[str]
        A custom string to use for the flag. Defaults to `--{dest}`.

    Examples
    --------

    Here is an example using the `default` parameter:

    >>> p = flag("verbose", default=False)
    >>> p.parse_args("-h")
    usage: --verbose

    >>> p.parse_args()
    {'verbose': False}

    By default `flag` fails when it does not receive expected input:
    >>> p = flag("verbose")
    >>> p.parse_args()
    usage: --verbose
    The following arguments are required: --verbose

    Here is an example using the `help` parameter:

    >>> p = flag("verbose", help="Turn on verbose output.")
    >>> p.parse_args("-h")
    usage: --verbose
    verbose: Turn on verbose output.

    Here is an example using the `short` parameter:

    >>> flag("verbose", short=True).parse_args("-v")  # this is the default
    {'verbose': True}
    >>> flag("verbose", short=False).parse_args("-v")  # fails
    usage: --verbose
    Expected '--verbose'. Got '-v'

    Here is an example using the `string` parameter:

    >>> flag("value", string="v").parse_args("v")  # note that string does not have to start with -
    {'value': True}

    >>> flag("config.value").parse_args("--config.value")
    {'config': {'value': True}}
    """
    if string is None:
        _string = f"--{dest}" if len(dest) > 1 else f"-{dest}"
    else:
        _string = string

    def f(
        cs: Sequence[str],
        s: str,
    ) -> Result[Parse[Output[Sequence[KeyValue[bool]]]]]:
        _defaults = defaults(**{dest: not default})
        if nesting:
            _defaults = _defaults.nesting()
        parser = matches(s) >= (lambda _: _defaults)
        return parser.parse(cs)

    parser = Parser(partial(f, s=_string), usage=None, helps={})
    if short:
        short_string = f"-{dest[0]}"
        parser2 = flag(dest, short=False, string=short_string, default=default)
        parser = parser | parser2
    if default:
        help = f"{help + ' ' if help else ''}(default: {default})"
    helps = {dest: help} if help else {}
    parser = replace(parser, usage=_string, helps=helps)
    return parser if default is None else parser | defaults(**{dest: default})


def help_parser(usage: Optional[str], parsed: A_monoid) -> Parser[A_monoid]:
    def f(
        cs: Sequence[str],
    ) -> Result[Parse[A_monoid]]:
        result = (matches("--help", peak=True) | matches("-h", peak=True)).parse(cs)
        if isinstance(result.get, ArgumentError):
            return Result.return_(Parse(parsed=parsed, unparsed=cs))
        return Result(HelpError(usage=usage or "Usage not provided."))

    return Parser(f, usage=None, helps={})


def item(
    name: str,
    usage_name: Optional[str] = None,
) -> Parser[Output[Sequence[KeyValue[str]]]]:
    """
    Parses a single word and binds it to `dest`.
    One of the lowest level building blocks for parsers.

    Parameters
    ----------
    usage_name : Optional[str]
        Used for generating usage text

    Examples
    --------

    >>> p = item("name", usage_name="Your first name")
    >>> p.parse_args("Alice")
    {'name': 'Alice'}
    >>> p.parse_args()
    usage: name
    The following arguments are required: Your first name
    """

    def f(cs: Sequence[str]) -> Result[Parse[Output[Sequence[KeyValue[str]]]]]:
        if cs:
            head, *tail = cs
            return Result(
                NonemptyList(
                    Parse(
                        parsed=Output[Sequence[KeyValue[str]]].from_dict(
                            **{name: head}
                        ),
                        unparsed=Sequence(tail),
                    )
                )
            )
        return Result(
            MissingError(
                missing=name,
                usage=f"The following arguments are required: {usage_name or name}",
            )
        )

    return Parser(f, usage=name, helps={})


def nonpositional(
    *parsers: "Parser[Output[A_monoid]]",
    repeated: Optional[Parser[Output[A_monoid]]] = None,
) -> "Parser[Output[A_monoid]]":
    """
    `nonpositional` takes a sequence of parsers as arguments and attempts all permutations of them,
    returning the first permutations that is successful:

    >>> p = nonpositional(flag("verbose"), flag("quiet"))
    >>> p.parse_args("--verbose", "--quiet")
    {'verbose': True, 'quiet': True}
    >>> p.parse_args("--quiet", "--verbose")  # reverse order also works
    {'quiet': True, 'verbose': True}

    Parameters
    ----------
    repeated : Optional[Parser[Sequence[A]]]
        If provided, this parser gets applied repeatedly (zero or more times) at all positions.

    Examples
    --------
    >>> p = nonpositional(repeated=flag("x"))
    >>> p.parse_args()
    {}
    >>> p.parse_args("-x")
    {'x': True}
    >>> p.parse_args("-x", "-x")
    {'x': [True, True]}

    >>> p = nonpositional(flag("y"), repeated=flag("x"))
    >>> p.parse_args("-y")
    {'y': True}
    >>> p.parse_args("-y", "-x")
    {'y': True, 'x': True}
    >>> p.parse_args("-x", "-y")
    {'x': True, 'y': True}
    >>> p.parse_args("-y", "-x", "-x")
    {'y': True, 'x': [True, True]}
    >>> p.parse_args("-x", "-y", "-x")
    {'x': [True, True], 'y': True}
    >>> p.parse_args("-x", "-x", "-y")
    {'x': [True, True], 'y': True}

    >>> p = nonpositional(flag("y"), repeated=(flag("x") | flag("z")).ignore())
    >>> p.parse_args("-x", "-y", "-z")
    {'y': True}
    """
    sep = " " if len(parsers) <= 3 else "\n"
    _parsers = [*parsers] if repeated is None else [*parsers, repeated]
    usage = sep.join([p.usage or "" for p in _parsers])
    repeat_parser = None
    if repeated is not None:
        _repeated = repeated  # for mypy's benefit

        def f(cs: Sequence[str]):
            p = _repeated >> nonpositional(*parsers, repeated=repeated)
            return p.parse(cs)

        repeat_parser = Parser(f, usage=None, helps={})

    if not parsers:
        if repeat_parser is None:
            return Parser[Output[A_monoid]].empty()
        else:
            return repeat_parser | Parser[Output[A_monoid]].empty()

    def get_alternatives():
        if repeat_parser is not None:
            yield repeat_parser
        for i, head in enumerate(parsers):
            tail = [p for j, p in enumerate(parsers) if j != i]
            yield head >> nonpositional(*tail, repeated=repeated)

    parser = reduce(operator.or_, get_alternatives())
    helps = parser.helps
    if repeated is not None:
        helps = {**helps, **repeated.helps}
    return replace(parser, usage=usage, helps=helps)


def option(
    dest: str,
    nesting: bool = True,
    flag: Optional[str] = None,
    default: Any = None,
    help: Optional[str] = None,
    short: bool = True,
    type: Callable[[str], Any] = str,
) -> Parser[Output[Sequence[KeyValue[Any]]]]:
    """
    Parses two words, binding the second to the first.

    Parameters
    ----------
    dest : str
        The name of variable to bind to:

    nesting : bool
        If `True`, then the parser will split the parsed output on `.` yielding nested output.
        See Examples for more details.

    flag : Optional[str]
        The flag to use for the option. If not provided, defaults to `--{dest}`.

    default : Optional[Any]
        The default value to bind on failure:

    help : Optional[str]
        The help message to display for the option:

    short : bool
        Whether to check for the short form of the flag, which
        uses a single dash and the first character of `dest`, e.g. `-c` for `count`.

    type : Callable[[str], Any]
        Use the `type` argument to convert the input to a different type:

    Examples
    --------

    >>> option("count").parse_args("--count", "1")
    {'count': '1'}

    In this example, you can see that the `flag` parameter allows the user to
    specify an arbitrary lead string, including one that doesn't start with a dash.

    >>> option("count", flag="ct").parse_args("ct", "1")
    {'count': '1'}

    This example demonstrates the use of the `default` parameter:

    >>> p = option("count", default=2)
    >>> p.parse_args("-h")
    usage: --count COUNT
    count: (default: 2)


    >>> p.parse_args()
    {'count': 2}

    Here we specify a help-string using the `help` parameter:

    >>> option("count", help="The number we should count to").parse_args("-h")
    usage: --count COUNT
    count: The number we should count to

    This example demonstrates the difference between `short=True` and `short=False`:

    >>> option("count", short=True).parse_args("-c", "1")
    {'count': '1'}
    >>> option("count", short=False).parse_args("-c", "1")
    usage: --count COUNT
    Expected '--count'. Got '-c'

    As with [argparse](https://docs.python.org/3/library/argparse.html#argument-parsing),
    the `type` argument allows you to convert the input to a different type using a
    function that takes a single string argument:

    >>> option("x", type=int).parse_args("-x", "1")  # converts "1" to an int
    {'x': 1}
    >>> option("x", type=lambda x: int(x) + 1).parse_args("-x", "1")
    {'x': 2}

    >>> option("config.x").parse_args("--config.x", "a")
    {'config': {'x': 'a'}}
    """

    if flag is None:
        _flag = f"--{dest}" if len(dest) > 1 else f"-{dest}"
    else:
        _flag = flag

    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Output[Sequence[KeyValue[str]]]]]:
        parser = matches(_flag) >= (
            lambda _: argument(dest, nesting=nesting, type=type)
        )
        return parser.parse(cs)

    parser = Parser(f, usage=None, helps={})
    if short and len(dest) > 1:
        parser2 = option(dest=dest, short=False, flag=f"-{dest[0]}", default=None)
        parser = parser | parser2
    if default:
        help = f"{help + ' ' if help else ''}(default: {default})"
    helps = {dest: help} if help else {}
    parser = replace(parser, usage=f"{_flag} {dest.upper()}", helps=helps)
    return parser if default is None else parser | defaults(**{dest: default})


def peak(
    name: str,
    description: Optional[str] = None,
) -> Parser[Output[Sequence[KeyValue[str]]]]:
    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Output[Sequence[KeyValue[str]]]]]:
        if cs:
            head, *_ = cs
            return Result(
                NonemptyList(
                    Parse(
                        parsed=Output[Sequence[KeyValue[str]]].from_dict(
                            **{name: head}
                        ),
                        unparsed=Sequence(cs),
                    )
                )
            )
        return Result(
            MissingError(
                missing=name,
                usage=f"The following arguments are required: {description or name}",
            )
        )

    return Parser(f, usage=name, helps={})


def sat(
    predicate: Callable[[str], bool],
    on_fail: Callable[[str], ArgumentError],
    name: str,
) -> Parser[Output[Sequence[KeyValue[str]]]]:
    """
    A wrapper around `Parser.sat` that uses `item` to parse the argument and just applies `predicate` to the value output by `item`.

    >>> p = sat(lambda x: len(x) == 1, lambda x: ArgumentError(f"'{x}' must have exactly one character."), "x")
    >>> p.parse_args("a")  # succeeds
    {'x': 'a'}
    >>> p.parse_args("aa")  # fails
    usage: x
    'aa' must have exactly one character.

    Parameters
    ----------
    predicate : Callable[[A], bool]
        The predicate to apply to the result of `item`. `sat` fails if this predicate returns false.
    on_fail : Callable[[A], ArgumentError]
        A function producing an ArgumentError to return if the predicate fails.
        Takes the output of `item` as an argument.
    name: str
        The value to bind the result to.
    """

    def _predicate(out: Output[Sequence[KeyValue[str]]]) -> bool:
        *_, (_, v) = map(astuple, out.get)
        return predicate(v)

    def _on_fail(out: Output[Sequence[KeyValue[str]]]) -> ArgumentError:
        *_, (_, v) = map(astuple, out.get)
        return on_fail(v)

    return item(name).sat(_predicate, _on_fail)


def sat_peak(
    predicate: Callable[[str], bool],
    on_fail: Callable[[str], ArgumentError],
    name: str,
) -> Parser[Output[Sequence[KeyValue[str]]]]:
    def _predicate(out: Output[Sequence[KeyValue[str]]]) -> bool:
        *_, (_, v) = map(astuple, out.get)
        return predicate(v)

    def _on_fail(out: Output[Sequence[KeyValue[str]]]) -> ArgumentError:
        *_, (_, v) = map(astuple, out.get)
        return on_fail(v)

    return peak(name).sat(_predicate, _on_fail)
