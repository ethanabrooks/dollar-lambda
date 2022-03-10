"""
Contains the `Parser` class and functions for building more specialized builder functions.
"""
# pyright: reportGeneralTypeIssues=false
from __future__ import annotations

import operator
import os
import sys
import typing
from dataclasses import asdict, dataclass, replace
from functools import lru_cache, partial, reduce
from typing import Any, Callable, Dict, Generator, Generic, Optional, Type, TypeVar

from pytypeclass import MonadPlus, Monoid
from pytypeclass.nonempty_list import NonemptyList

from dollar_lambda.error import (
    ArgumentError,
    HelpError,
    MissingError,
    UnequalError,
    UnexpectedError,
)
from dollar_lambda.key_value import KeyValue, KeyValueTuple
from dollar_lambda.result import Result
from dollar_lambda.sequence import Sequence

Monoid_co = TypeVar("Monoid_co", bound=Monoid, covariant=True)
Monoid1 = TypeVar("Monoid1", bound=Monoid)
Monoid2 = TypeVar("Monoid2", bound=Monoid)
A_co = TypeVar("A_co", covariant=True)
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


def empty() -> Parser[Sequence]:
    """
    Always returns {}, no matter the input. Mostly useful for use in `nonpositional`.
    >>> empty().parse_args("any", "arguments")
    {}
    """
    return Parser[Sequence[A]].empty()


def binary_usage(a: Optional[str], op: str, b: Optional[str], add_brackets=True):
    """
    Utility for generating usage strings for binary operators.
    """
    no_nones = [x for x in (a, b) if x is not None]
    usage = op.join(no_nones)
    if len(no_nones) > 1 and add_brackets:
        usage = f"[{usage}]"
    return usage or None


__pdoc__ = {}


@dataclass
class Parser(MonadPlus[A_co]):
    """
    Main class powering the argument parser.
    """

    __pdoc__["Parser.__add__"] = True
    __pdoc__["Parser.__or__"] = True
    __pdoc__["Parser.__rshift__"] = True
    __pdoc__["Parser.__ge__"] = True

    f: Callable[[Sequence[str]], Result[Parse[A_co]]]
    usage: Optional[str]
    helps: Dict[str, str]

    def __add__(
        self: Parser[Sequence[A]], other: Parser[Sequence[B]]
    ) -> Parser[Sequence[A | B]]:
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
        p = (self >> other) | (other >> self)
        usage = binary_usage(self.usage, " ", other.usage, add_brackets=False)
        return replace(p, usage=usage)

    def __or__(
        self: Parser[A_co],
        other: Parser[B],
    ) -> Parser[A_co | B]:
        """
        Tries apply the first parser. If it fails, tries the second. If that fails, the parser fails.

        >>> from dollar_lambda import argument, option, done, flag
        >>> p = option("option") | flag("verbose")
        >>> p.parse_args("--option", "x")
        {'option': 'x'}
        >>> p.parse_args("--verbose")
        {'verbose': True}

        Note that when both arguments are supplied, this will only parse the first:
        >>> p.parse_args("--verbose", "--option", "x")
        {'verbose': True}

        If you want this to fail, use `>>` (`Parser.__rshift__`) with `done()` or another parser:
        >>> (p >> done()).parse_args("--verbose", "--option", "x")
        usage: [--option OPTION | --verbose]
        Unrecognized argument: --option
        >>> p.parse_args("--option", "x")
        {'option': 'x'}
        """

        def f(cs: Sequence[str]) -> Result[Parse[A_co | B]]:
            return self.parse(cs) | other.parse(cs)

        return Parser(
            f,
            usage=binary_usage(self.usage, " | ", other.usage),
            helps={**self.helps, **other.helps},
        )

    def __rshift__(
        self: Parser[Sequence[A]], p: Parser[Sequence[B]]
    ) -> Parser[Sequence[A | B]]:
        """
        This applies parsers in sequence. If the first parser succeeds, the unparsed remainder
        gets handed off to the second parser. If either parser fails, the whole thing fails.

        >>> from dollar_lambda import argument, flag
        >>> p = argument("first") >> argument("second")
        >>> p.parse_args("a", "b")
        {'first': 'a', 'second': 'b'}
        >>> p.parse_args("a")
        usage: first second
        The following arguments are required: second
        >>> p.parse_args("b")
        usage: first second
        The following arguments are required: second
        """
        # def f(p1: Sequence[D]) -> Parser[Parse[Sequence[D | B]]]:
        #     def g(p2: Sequence[B]) -> Parser[Sequence[D | B]]:
        #         return Parser.return_(p1 + p2)

        #     return p >= g

        # return self >= f
        parser = self >= (lambda p1: (p >= (lambda p2: Parser.return_(p1 + p2))))
        return replace(
            parser,
            usage=binary_usage(self.usage, " ", p.usage, add_brackets=False),
            helps={**self.helps, **p.helps},
        )

    def bind(self, f: Callable[[A_co], Parser[B]]) -> Parser[B]:
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

        Now let's use the `equals` parser to write a function that takes the output of `p1` and fails unless
        the next argument is the same as the first:
        >>> def f(kvs: Sequence(KeyValue[str])) -> Sequence(KeyValue[str]):
        ...     [kv] = kvs
        ...     return equals(kv.value)

        >>> p = p1 >= f
        >>> p.parse_args("a", "a")
        {'a': 'a'}
        >>> p.parse_args("a", "b")
        Expected 'a'. Got 'b'
        """

        def h(parse: Parse[A_co]) -> Result[Parse[B]]:
            return f(parse.parsed).parse(parse.unparsed)

        def g(cs: Sequence[str]) -> Result[Parse[B]]:
            return self.parse(cs) >= h

        return Parser(g, usage=None, helps=self.helps)

    @classmethod
    def empty(cls: Type[Parser[Sequence[A]]]) -> Parser[Sequence[A]]:
        """
        Always returns {}, no matter the input. Mostly useful for use in `nonpositional`.
        >>> empty().parse_args("any", "arguments")
        {}
        """
        return cls.return_(Sequence([]))

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

    def many(self: Parser[Sequence[Monoid1]]) -> Parser[Sequence[Monoid1]]:
        """
        Applies `self` zero or more times (like `*` in regexes).

        >>> from dollar_lambda import argument, flag
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args(return_dict=False)
        []
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a", return_dict=False)
        [('as-many-as-you-like', 'a')]
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a", "b", return_dict=False)  # return_dict=False allows duplicate keys
        [('as-many-as-you-like', 'a'), ('as-many-as-you-like', 'b')]

        Note that if `self` contains `Parser.__or__`, the arguments can be
        heterogenous:
        >>> p = flag("verbose") | flag("quiet")
        >>> p = p.many()
        >>> p.parse_args("--verbose", "--quiet", return_dict=False) # mix --verbose and --quiet
        [('verbose', True), ('quiet', True)]
        """
        p = self.many1() | self.empty()
        return replace(p, usage=f"[{self.usage} ...]")

    def many1(self: Parser[Sequence[Monoid1]]) -> Parser[Sequence[Monoid1]]:
        """
        Applies `self` one or more times (like `+` in regexes).

        >>> from dollar_lambda import argument, flag
        >>> p = argument("1-or-more").many1()
        >>> p.parse_args("1")
        {'1-or-more': '1'}
        >>> p.parse_args("1", "2", return_dict=False)  # return_dict=False allows duplicate keys
        [('1-or-more', '1'), ('1-or-more', '2')]
        >>> p.parse_args()
        usage: 1-or-more [1-or-more ...]
        The following arguments are required: 1-or-more
        """

        def g() -> Generator["Parser[Sequence[Monoid1]]", Sequence[Monoid1], None]:
            # noinspection PyTypeChecker
            r1: Sequence[Monoid1] = yield self
            # noinspection PyTypeChecker
            r2: Sequence[Monoid1] = yield self.many()
            yield Parser[Sequence[Monoid1]].return_(r1 + r2)

        @lru_cache()
        def f(cs: tuple):
            return Parser.do(g).parse(Sequence(list(cs)))

        return Parser(
            lambda cs: f(tuple(cs)),
            usage=f"{self.usage} [{self.usage} ...]",
            helps=self.helps,
        )

    def optional(self: Parser[Sequence[A]]) -> Parser[Sequence[A]]:
        return self | self.empty()

    def parse(self, cs: Sequence[str]) -> Result[Parse[A_co]]:
        """
        Applies the parser to the input sequence `cs`.
        """
        return self.f(cs)

    def parse_args(
        self: "Parser[Sequence[KeyValue]]",
        *args: str,
        return_dict: bool = True,
        check_help: bool = True,
    ) -> typing.Sequence[KeyValueTuple] | Dict[str, Any]:
        """
        The main way the user extracts parsed results from the parser.

        Parameters
        ----------
        args : str
            A sequence of strings to parse (e.g. `sys.argv[1:]`).
        return_dict : bool
            Returns a sequence of tuples instead of dictionary, thereby allowing duplicate keys.
            The tuples are `KeyValueTuple` namedtuples, with fields `key` and `value`.
        check_help : bool
            Before running the parser, checks if the input string is `--help` or `-h`.
            If it is, returns the usage message.

        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a", "b", return_dict=False)
        [('as-many-as-you-like', 'a'), ('as-many-as-you-like', 'b')]

        >>> argument("a").parse_args("-h")
        usage: a
        >>> argument("a").parse_args("--help")
        usage: a
        """
        _args = args if args or TESTING else sys.argv[1:]
        if check_help:
            return wrap_help(self).parse_args(
                *_args, return_dict=return_dict, check_help=False
            )
        result = self.parse(Sequence(list(_args))).get
        if isinstance(result, ArgumentError):
            self.handle_error(result)
            if TESTING:
                return  # type: ignore[return-value]
            else:
                exit()

        kvs = result.head.parsed
        if return_dict:
            return {kv.key: kv.value for kv in kvs}
        return [KeyValueTuple(**asdict(kv)) for kv in kvs]

    @classmethod
    def return_(cls, a: A_co) -> Parser[A_co]:  # type: ignore[misc]
        # see https://github.com/python/mypy/issues/6178#issuecomment-1057111790
        """
        This method is required to make `Parser` a [`Monad`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monad.py#L16). It consumes none of the input
        and always returns `a` as the result. For the most part, the user will not use
        this method unless building custom parsers.

        >>> from dollar_lambda.key_value import KeyValue
        >>> Parser.return_(([KeyValue("some-key", "some-value")])).parse_args()
        {'some-key': 'some-value'}
        """

        def f(cs: Sequence[str]) -> Result[Parse[A_co]]:
            return Result.return_(Parse(a, cs))

        return Parser(f, usage=None, helps={})

    @classmethod
    def zero(cls, error: Optional[ArgumentError] = None) -> Parser[A_co]:
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


def apply(
    f: Callable[[Monoid1], Result[Monoid_co]], parser: Parser[Monoid1]
) -> Parser[Monoid_co]:
    """
    Take the output of `parser` and apply `f` to it. Convert any errors that arise into `ArgumentError`.
    """

    def g(a: Monoid1) -> Parser[Monoid_co]:
        try:
            y = f(a)
        except Exception as e:
            usage = f"An argument {a}: raised exception {e}"
            y = Result(ArgumentError(usage))
        return Parser(
            lambda unparsed: y
            >= (lambda parsed: Result.return_(Parse(parsed, unparsed))),
            usage=parser.usage,
            helps=parser.helps,
        )

    p = parser >= g
    return replace(p, usage=parser.usage, helps=parser.helps)


def apply_item(f: Callable[[str], Monoid_co], description: str) -> Parser[Monoid_co]:
    def g(parsed: Sequence[KeyValue[str]]) -> Result[Monoid_co]:
        [kv] = parsed
        try:
            y = f(kv.value)
        except Exception as e:
            usage = f"argument {kv.value}: raised exception {e}"
            return Result(ArgumentError(usage))
        return Result.return_(y)

    return apply(g, item(description))


def argument(dest: str) -> Parser[Sequence[KeyValue[str]]]:
    """
    >>> argument("name").parse_args("Alice")
    {'name': 'Alice'}
    >>> argument("name").parse_args()
    usage: name
    The following arguments are required: name
    """
    return item(dest)


def defaults(**kwargs: Any) -> Parser[Sequence[KeyValue[Any]]]:
    p = Parser.return_(Sequence([KeyValue(k, v) for k, v in kwargs.items()]))
    return replace(p, usage=None)


def done() -> Parser[Sequence[A]]:
    """
    >>> done().parse_args()
    {}
    >>> done().parse_args("arg")
    Unrecognized argument: arg
    >>> (argument("arg") >> done()).parse_args("a")
    {'arg': 'a'}
    >>> (argument("arg") >> done()).parse_args("a", "b")
    usage: arg
    Unrecognized argument: b
    >>> (flag("arg").many() >> done()).parse_args("--arg", "--arg", return_dict=False)
    [('arg', True), ('arg', True)]
    >>> (flag("arg").many() >> done()).parse_args("--arg", "--arg", "x")
    usage: [--arg ...]
    Unrecognized argument: x
    """

    def f(cs: Sequence[str]) -> Result[Parse[Sequence[A]]]:
        if cs:
            c, *_ = cs
            return Result(
                UnexpectedError(unexpected=c, usage=f"Unrecognized argument: {c}")
            )
        return Result(NonemptyList(Parse(parsed=Sequence([]), unparsed=cs)))

    return Parser(f, usage=None, helps={})


def equals(s: str, peak=False) -> Parser[Sequence[KeyValue[str]]]:
    if peak:
        return sat_peak(
            predicate=lambda _s: _s == s,
            on_fail=lambda _s: UnequalError(
                left=s, right=_s, usage=f"Expected '{s}'. Got '{_s}'"
            ),
            name=s,
        )
    else:
        return sat_item(
            predicate=lambda _s: _s == s,
            on_fail=lambda _s: UnequalError(
                left=s, right=_s, usage=f"Expected '{s}'. Got '{_s}'"
            ),
            name=s,
        )


def flag(
    dest: str,
    default: Optional[bool] = None,
    help: Optional[str] = None,
    short: bool = True,
    string: Optional[str] = None,
) -> Parser[Sequence[KeyValue[bool]]]:
    """
    >>> p = flag("verbose", default=False)
    >>> p.parse_args("--verbose")
    {'verbose': True}
    >>> p.parse_args()
    {'verbose': False}
    >>> p.parse_args("--verbose", "--verbose", "--verbose")
    {'verbose': True}
    >>> flag("v", string="--value").parse_args("--value")
    {'v': True}

    >>> p1 = flag("verbose", default=False) | flag("quiet", default=False) | flag("yes", default=False)
    >>> p = p1 >> done()
    >>> p.parse_args("--verbose", "value")
    usage: [[--verbose | --quiet] | --yes]
    Unrecognized argument: value
    >>> p.parse_args("value")
    usage: [[--verbose | --quiet] | --yes]
    Unrecognized argument: value
    >>> p.parse_args("--verbose")
    {'verbose': True}
    >>> p1 = flag("verbose") | flag("quiet") | flag("yes")
    >>> p = p1 >> argument("a")
    >>> p.parse_args("--verbose")
    usage: [[--verbose | --quiet] | --yes] a
    The following arguments are required: a
    >>> p.parse_args("a")
    usage: [[--verbose | --quiet] | --yes] a
    Expected '--verbose'. Got 'a'
    """
    if string is None:
        _string = f"--{dest}" if len(dest) > 1 else f"-{dest}"
    else:
        _string = string

    def f(
        cs: Sequence[str],
        s: str,
    ) -> Result[Parse[Sequence[KeyValue[bool]]]]:
        parser = equals(s) >= (lambda _: defaults(**{dest: not default}))
        return parser.parse(cs)

    parser = Parser(partial(f, s=_string), usage=None, helps={})
    if default is not None:
        parser = parser | defaults(**{dest: default})
    if short:
        short_string = f"-{dest[0]}"
        parser2 = flag(dest, short=False, string=short_string, default=default)
        parser = parser | parser2
    if default:
        help = f"{help + ' ' if help else ''}(default: {default})"
    helps = {dest: help} if help else {}
    return replace(parser, usage=_string, helps=helps)


def help_parser(usage: str, parsed: Monoid1) -> Parser[Monoid1]:
    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Monoid1]]:
        result = (equals("--help", peak=True) | equals("-h", peak=True)).parse(cs)
        if isinstance(result.get, ArgumentError):
            return Result.return_(Parse(parsed=parsed, unparsed=cs))
        return Result(HelpError(usage=usage))

    return Parser(f, usage=None, helps={})


def wrap_help(parser: Parser[A]) -> Parser[A]:
    _help_parser: Parser[Sequence[A]] = help_parser(
        parser.usage or "No usage provided.", Sequence([])
    )

    p = _help_parser >= (lambda _: parser)
    return replace(p, usage=parser.usage, helps=parser.helps)


def item(
    name: str,
    description: Optional[str] = None,
) -> Parser[Sequence[KeyValue[str]]]:
    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[str]]]]:
        if cs:
            head, *tail = cs
            return Result(
                NonemptyList(
                    Parse(
                        parsed=Sequence([KeyValue(name, head)]),
                        unparsed=Sequence(tail),
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


def nonpositional(*parsers: "Parser[Sequence[A]]") -> "Parser[Sequence[A]]":
    """
    >>> p = nonpositional(flag("verbose", default=False), flag("debug", default=False)) >> done()
    >>> p.parse_args("--verbose", "--debug")
    {'verbose': True, 'debug': True}
    >>> p.parse_args("--debug", "--verbose")
    {'debug': True, 'verbose': True}
    >>> p.parse_args()
    {'verbose': False, 'debug': False}
    >>> p.parse_args("--debug")
    {'verbose': False, 'debug': True}
    >>> p.parse_args("--verbose")
    {'verbose': True, 'debug': False}
    >>> p = nonpositional(flag("verbose", default=False), flag("debug", default=False)) >> done()
    >>> p.parse_args("--verbose", "--debug")
    {'verbose': True, 'debug': True}
    >>> p.parse_args("--verbose")
    {'verbose': True, 'debug': False}
    >>> p.parse_args("--debug")
    {'verbose': False, 'debug': True}
    >>> p.parse_args()
    {'verbose': False, 'debug': False}
    >>> p = nonpositional(flag("verbose", default=False), flag("debug", default=False), argument("a")) >> done()
    >>> p.parse_args("--debug", "hello", "--verbose")
    {'debug': True, 'a': 'hello', 'verbose': True}
    >>> p = nonpositional(flag("verbose"))
    >>> p.parse_args("-h")
    usage: --verbose
    >>> p.parse_args("--verbose")
    {'verbose': True}
    """
    if not parsers:
        return empty()

    def get_alternatives():
        for i, head in enumerate(parsers):
            tail = [p for j, p in enumerate(parsers) if j != i]
            yield head >> nonpositional(*tail)

    parser = reduce(operator.or_, get_alternatives())
    sep = " " if len(parsers) <= 3 else "\n"
    return replace(parser, usage=sep.join([p.usage or "" for p in parsers]))


def option(
    dest: str,
    flag: Optional[str] = None,
    default=None,
    help: Optional[str] = None,
    short: bool = True,
    type: Callable[[str], Any] = str,
) -> Parser[Sequence[KeyValue[str]]]:
    """
    >>> option("value").parse_args("--value", "x")
    {'value': 'x'}
    >>> option("value").parse_args("--value")
    usage: --value VALUE
    The following arguments are required: VALUE
    >>> option("value").parse_args()
    usage: --value VALUE
    The following arguments are required: --value
    >>> option("value", default=1).parse_args()
    {'value': 1}
    >>> option("value", default=1).parse_args("--value")
    {'value': 1}
    >>> option("value", default=1).parse_args("--value", "x")
    {'value': 'x'}
    >>> option("v").parse_args("-v", "x")
    {'v': 'x'}
    >>> option("v", flag="--value").parse_args("--value", "x")
    {'v': 'x'}
    """

    if flag is None:
        _flag = f"--{dest}" if len(dest) > 1 else f"-{dest}"
    else:
        _flag = flag

    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[str]]]]:
        parser = equals(_flag) >= (lambda _: item(dest, description=dest.upper()))
        return parser.parse(cs)

    parser = Parser(f, usage=None, helps={})
    if default:
        parser = parser | defaults(**{dest: default})
    if short and len(dest) > 1:
        parser2 = option(dest=dest, short=False, flag=f"-{dest[0]}", default=None)
        parser = parser | parser2
    if type is not str:
        parser = type_(type, parser)
    helps = {dest: help} if help else {}
    return replace(parser, usage=f"{_flag} {dest.upper()}", helps=helps)


def peak(
    name: str,
    description: Optional[str] = None,
) -> Parser[Sequence[KeyValue[str]]]:
    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[str]]]]:
        if cs:
            head, *_ = cs
            return Result(
                NonemptyList(
                    Parse(
                        parsed=Sequence([KeyValue(name, head)]),
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
    parser: Parser[Monoid1],
    predicate: Callable[[Monoid1], bool],
    on_fail: Callable[[Monoid1], ArgumentError],
) -> Parser[Monoid1]:
    def f(x: Monoid1) -> Result[Monoid1]:
        return Result(NonemptyList(x) if predicate(x) else on_fail(x))

    return apply(f, parser)


def sat_item(
    predicate: Callable[[str], bool],
    on_fail: Callable[[str], ArgumentError],
    name: str,
) -> Parser[Sequence[KeyValue[str]]]:
    def _predicate(parsed: Sequence[KeyValue[str]]) -> bool:
        [kv] = parsed
        return predicate(kv.value)

    def _on_fail(parsed: Sequence[KeyValue[str]]) -> ArgumentError:
        [kv] = parsed
        return on_fail(kv.value)

    return sat(item(name), _predicate, _on_fail)


def sat_peak(
    predicate: Callable[[str], bool],
    on_fail: Callable[[str], ArgumentError],
    name: str,
) -> Parser[Sequence[KeyValue[str]]]:
    def _predicate(parsed: Sequence[KeyValue[str]]) -> bool:
        [kv] = parsed
        return predicate(kv.value)

    def _on_fail(parsed: Sequence[KeyValue[str]]) -> ArgumentError:
        [kv] = parsed
        return on_fail(kv.value)

    return sat(peak(name), _predicate, _on_fail)


def type_(
    f: Callable[[str], Any], parser: Parser[Sequence[KeyValue[str]]]
) -> Parser[Sequence[KeyValue[Any]]]:
    def g(
        kvs: Sequence[KeyValue[str]],
    ) -> Result[Sequence[KeyValue[Any]]]:
        head, *tail = kvs.get
        try:
            y = f(head.value)
        except Exception as e:
            usage = f"argument {head.value}: raised exception {e}"
            return Result(ArgumentError(usage))
        head = replace(head, value=y)
        return Result.return_(Sequence([*tail, head]))

    p = apply(g, parser)
    return replace(p, usage=parser.usage, helps=parser.helps)
