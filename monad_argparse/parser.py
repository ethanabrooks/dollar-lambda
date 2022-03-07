"""
`Parser` is the class that powers `monad_argparse`.
"""
# pyright: reportGeneralTypeIssues=false
from __future__ import annotations

import operator
import os
import typing
from dataclasses import asdict, dataclass, replace
from functools import lru_cache, partial, reduce
from typing import Any, Callable, Dict, Generator, Optional, Type, TypeVar

from pytypeclass import MonadPlus, Monoid
from pytypeclass.nonempty_list import NonemptyList

from monad_argparse.error import (
    ArgumentError,
    HelpError,
    MissingError,
    UnequalError,
    UnexpectedError,
)
from monad_argparse.key_value import KeyValue, KeyValueTuple
from monad_argparse.parse import Parse
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence

A = TypeVar("A", bound=Monoid, covariant=True)
B = TypeVar("B", bound=Monoid)
C = TypeVar("C")
D = TypeVar("D", bound=Monoid)

global TESTING
TESTING = os.environ.get("TESTING", False)


def const(b: B) -> Parser[Sequence[B]]:
    return Parser.return_(Sequence([b]))


def empty() -> Parser[Sequence[B]]:
    return Parser.return_(Sequence([]))


def binary_usage(a: Optional[str], op: str, b: Optional[str], add_brackets=True):
    no_nones = [x for x in (a, b) if x is not None]
    usage = op.join(no_nones)
    if len(no_nones) > 1 and add_brackets:
        usage = f"[{usage}]"
    return usage or None


@dataclass
class Parser(MonadPlus[A]):
    f: Callable[[Sequence[str]], Result[Parse[A]]]
    usage: Optional[str]
    helps: Dict[str, str]

    def __add__(
        self: Parser[Sequence[D]], other: Parser[Sequence[B]]
    ) -> Parser[Sequence[D | B]]:
        p = (self >> other) | (other >> self)
        usage = binary_usage(self.usage, " ", other.usage, add_brackets=False)
        return replace(p, usage=usage)

    def __or__(
        self: Parser[A],
        other: Parser[B],
    ) -> Parser[A | B]:
        """
        >>> from monad_argparse import argument, option, done, flag
        >>> p = option("option") | flag("verbose")
        >>> p.parse_args("--verbose")
        {'verbose': True}
        >>> p.parse_args("--verbose", "--option", "x")
        {'verbose': True}
        >>> (p >> done()).parse_args("--verbose", "--option", "x")
        usage: [--option OPTION | --verbose]
        Unrecognized argument: --option
        >>> p.parse_args("--option", "x")
        {'option': 'x'}
        """

        def f(cs: Sequence[str]) -> Result[Parse[A | B]]:
            return self.parse(cs) | other.parse(cs)

        return Parser(
            f,
            usage=binary_usage(self.usage, " | ", other.usage),
            helps={**self.helps, **other.helps},
        )

    def __rshift__(
        self: Parser[Sequence[D]], p: Parser[Sequence[B]]
    ) -> Parser[Sequence[D | B]]:
        """
        >>> from monad_argparse import argument, flag
        >>> p = argument("first") >> argument("second")
        >>> p.parse_args("a", "b")
        {'first': 'a', 'second': 'b'}
        >>> p.parse_args("a")
        usage: first second
        The following arguments are required: second
        >>> p.parse_args("b")
        usage: first second
        The following arguments are required: second
        >>> p1 = flag("verbose", default=False) | flag("quiet", default=False) | flag("yes", default=False)
        >>> p = p1 >> argument("a")
        >>> p.parse_args("--verbose", "value")
        {'verbose': True, 'a': 'value'}
        >>> p.parse_args("value")
        {'verbose': False, 'a': 'value'}
        >>> p.parse_args("--verbose")
        {'verbose': False, 'a': '--verbose'}
        >>> p1 = flag("verbose") | flag("quiet") | flag("yes")
        >>> p = p1 >> argument("a")
        >>> p.parse_args("--verbose")
        usage: [[--verbose | --quiet] | --yes] a
        The following arguments are required: a
        >>> p.parse_args("a")
        usage: [[--verbose | --quiet] | --yes] a
        Expected '--verbose'. Got 'a'
        """
        # def f(p1: Sequence[D]) -> Parser[Parse[Sequence[D | B]]]:
        #     def g(p2: Sequence[B]) -> Parser[Sequence[D | B]]:
        #         return Parser.return_(p1 + p2)

        #     return p >= g

        # return self >= f
        parser = self >= (lambda p1: (p >= (lambda p2: Parser.return_(p1 + p2))))
        return replace(
            parser, usage=binary_usage(self.usage, " ", p.usage, add_brackets=False)
        )

    def bind(self, f: Callable[[A], Parser[B]]) -> Parser[B]:
        def h(parse: Parse[A]) -> Result[Parse[B]]:
            return f(parse.parsed).parse(parse.unparsed)

        def g(cs: Sequence[str]) -> Result[Parse[B]]:
            return self.parse(cs) >= h

        return Parser(g, usage=None, helps=self.helps)

    def many(self: "Parser[Sequence[B]]") -> "Parser[Sequence[B]]":
        """
        >>> from monad_argparse import argument, flag
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args(return_dict=False)
        []
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a", return_dict=False)
        [('as-many-as-you-like', 'a')]
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a", "b", return_dict=False)
        [('as-many-as-you-like', 'a'), ('as-many-as-you-like', 'b')]
        >>> p = flag("verbose") | flag("quiet")
        >>> p = p.many()  # parse zero or more copies
        >>> p.parse_args("--quiet", "--quiet", "--quiet", return_dict=False)
        [('quiet', True), ('quiet', True), ('quiet', True)]
        >>> p.parse_args("--verbose", "--quiet", "--quiet", return_dict=False)
        [('verbose', True), ('quiet', True), ('quiet', True)]
        """
        p = self.many1() | empty()
        return replace(p, usage=f"[{self.usage} ...]")

    def many1(self: "Parser[Sequence[B]]") -> "Parser[Sequence[B]]":
        def g() -> Generator["Parser[Sequence[B]]", Sequence[B], None]:
            # noinspection PyTypeChecker
            r1: Sequence[B] = yield self
            # noinspection PyTypeChecker
            r2: Sequence[B] = yield self.many()
            yield Parser[Sequence[B]].return_(r1 + r2)

        @lru_cache()
        def f(cs: tuple):
            return Parser.do(g).parse(Sequence(list(cs)))

        return Parser(
            lambda cs: f(tuple(cs)),
            usage=f"{self.usage} [{self.usage} ...]",
            helps=self.helps,
        )

    def parse(self, cs: Sequence[str]) -> Result[Parse[A]]:
        return self.f(cs)

    def parse_args(
        self: "Parser[Sequence[KeyValue]]",
        *args: str,
        return_dict: bool = True,
        check_help: bool = True,
    ) -> typing.Sequence[KeyValueTuple] | Dict[str, Any]:
        if check_help:
            return wrap_help(self).parse_args(
                *args, return_dict=return_dict, check_help=False
            )
        result = self.parse(Sequence(list(args))).get
        if isinstance(result, ArgumentError):
            if self.usage and not isinstance(result, HelpError):
                print("usage:", end="\n" if "\n" in self.usage else " ")
                if "\n" in self.usage:
                    usage = "\n".join(["    " + u for u in self.usage.split("\n")])
                else:
                    usage = self.usage
                print(usage)
            if self.helps:
                for k, v in self.helps.items():
                    print(f"{k}: {v}")
            if result.usage:
                print(result.usage)
            if TESTING:
                return  # type: ignore[return-value]
            else:
                exit()

        nel: NonemptyList[Parse[Sequence[KeyValue]]] = result
        parse: Parse[Sequence[KeyValue]] = nel.head
        kvs: Sequence[KeyValue] = parse.parsed
        if return_dict:
            return {kv.key: kv.value for kv in kvs}
        return [KeyValueTuple(**asdict(kv)) for kv in kvs]

    @classmethod
    def return_(cls, a: A) -> Parser[A]:  # type: ignore[misc]
        # see https://github.com/python/mypy/issues/6178#issuecomment-1057111790
        """
        >>> from monad_argparse.key_value import KeyValue
        >>> Parser.return_(([KeyValue("some-key", "some-value")])).parse_args()
        {'some-key': 'some-value'}
        """

        def f(cs: Sequence[str]) -> Result[Parse[A]]:
            return Result.return_(Parse(a, cs))

        return Parser(f, usage=None, helps={})

    @classmethod
    def zero(cls: Type[Parser[A]], error: Optional[ArgumentError] = None) -> Parser[A]:
        """
        >>> Parser.zero().parse_args()
        zero
        >>> Parser.zero().parse_args("a")
        zero
        >>> Parser.zero(error=ArgumentError("This is a test.")).parse_args("a")
        This is a test.
        """
        return Parser(lambda _: Result.zero(error=error), usage=None, helps={})


E = TypeVar("E", bound=MonadPlus)
F = TypeVar("F")
G = TypeVar("G", covariant=True, bound=MonadPlus)


def apply(f: Callable[[E], Result[G]], parser: Parser[E]) -> Parser[G]:
    def g(a: E) -> Parser[G]:
        usage = f"invalid value for {f.__name__}: {a}"
        usage = f"argument {parser.usage}: {usage}"
        return Parser(
            lambda unparsed: f(a)
            >= (lambda parsed: Result.return_(Parse(parsed, unparsed))),
            usage=usage,
            helps=parser.helps,
        )

    return parser >= g


def apply_item(f: Callable[[str], G], description: str) -> Parser[G]:
    def g(parsed: Sequence[KeyValue[str]]) -> Result[G]:
        [kv] = parsed
        try:
            y = f(kv.value)
        except ArgumentError as e:
            return Result(e)
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


def done() -> Parser[Sequence[F]]:
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

    def f(cs: Sequence[str]) -> Result[Parse[Sequence[F]]]:
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


def help_parser(usage: str, parsed: B) -> Parser[B]:
    def f(
        cs: Sequence[str],
    ) -> Result[Parse[B]]:
        result = (equals("--help", peak=True) | equals("-h", peak=True)).parse(cs)
        if isinstance(result.get, ArgumentError):
            return Result.return_(Parse(parsed=parsed, unparsed=cs))
        return Result(HelpError(usage=usage))

    return Parser(f, usage=None, helps={})


def wrap_help(parser: Parser[Sequence[C]]) -> Parser[Sequence[C]]:
    _help_parser: Parser[Sequence[C]] = help_parser(
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


def nonpositional(*parsers: "Parser[Sequence[F]]") -> "Parser[Sequence[F]]":
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
    """
    if not parsers:
        return empty()

    def get_alternatives():
        for i, head in enumerate(parsers):
            tail = [p for j, p in enumerate(parsers) if j != i]
            yield head >> nonpositional(*tail)

    parser = reduce(operator.or_, get_alternatives())
    return replace(parser, usage="\n".join([p.usage or "" for p in parsers]))


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
    parser: Parser[E],
    predicate: Callable[[E], bool],
    on_fail: Callable[[E], ArgumentError],
) -> Parser[E]:
    def f(x: E) -> Result[E]:
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
            head = replace(head, value=f(head.value))
        except ArgumentError as e:
            return Result(e)

        return Result(NonemptyList(Sequence([*tail, head])))

    return apply(g, parser)
