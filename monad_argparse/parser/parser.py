from __future__ import annotations

import typing
from dataclasses import asdict
from functools import lru_cache
from typing import Callable, Generator, Optional, Type, TypeVar

from monad_argparse.monad.monoid import MonadPlus, Monoid
from monad_argparse.parser.key_value import KeyValue, KeyValueTuple
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence

A = TypeVar("A", bound=Monoid, covariant=True)
B = TypeVar("B", bound=Monoid)
C = TypeVar("C", bound=Monoid)


class Parser(MonadPlus[A]):
    D = TypeVar("D", bound="Parser")

    def __init__(self, f: Callable[[Sequence[str]], Result[Parse[A]]]):
        self.f = f

    def __add__(
        self: Parser[A],
        other: Parser[B],
    ) -> Parser[A | B]:
        """
        >>> from monad_argparse import Argument, Option, Done, Flag
        >>> p = Flag("verbose") | Option("option")
        >>> p.parse_args("--verbose")
        [('verbose', True)]
        >>> p.parse_args("--verbose", "--option", "x")
        [('verbose', True)]
        >>> (p >> Done()).parse_args("--verbose", "--option", "x")
        ArgumentError(token='--option', description='Unexpected argument: --option')
        >>> p.parse_args("--option", "x")
        [('option', 'x')]
        """

        def f(cs: Sequence[str]) -> Result[Parse[A | B]]:
            r1: Result[Parse[A]] = self.parse(cs)
            r2: Result[Parse[B]] = other.parse(cs)
            choices: Result[Parse[A | B]] = r1 | r2
            if not isinstance(choices.get, Exception):
                return choices
            else:
                return r2

        return Parser(f)

    def __rshift__(
        self: Parser[Sequence[A]], p: Parser[Sequence[B]]
    ) -> Parser[Sequence[A | B]]:
        """
        >>> from monad_argparse import Argument, Flag
        >>> p = Argument("first") >> Argument("second")
        >>> p.parse_args("a", "b")
        [('first', 'a'), ('second', 'b')]
        >>> p.parse_args("a")
        ArgumentError(token=None, description='Missing: second')
        >>> p.parse_args("b")
        ArgumentError(token=None, description='Missing: second')
        >>> p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
        >>> p = p1 >> Argument("a")
        >>> p.parse_args("--verbose", "value")
        [('verbose', True), ('a', 'value')]
        >>> p.parse_args("value")
        ArgumentError(token='value', description="Input 'value' does not match '--yes")
        >>> p.parse_args("--verbose")
        ArgumentError(token=None, description='Missing: a')
        """
        return self >= (lambda p1: (p >= (lambda p2: Parser.return_(p1 + p2))))

    def bind(self, f: Callable[[A], Parser[B]]) -> Parser[B]:
        def h(parse: Parse[A]) -> Result[Parse[B]]:
            return f(parse.parsed).parse(parse.unparsed)

        def g(cs: Sequence[str]) -> Result[Parse[B]]:
            return self.parse(cs).bind(h)

        return Parser(g)

    @classmethod
    def const(cls: Type[Parser[Sequence[B]]], b: B) -> Parser[Sequence[B]]:
        return cls.return_(Sequence([b]))

    @classmethod
    def key_values(
        cls: Type[Parser[Sequence[KeyValue[B]]]], **kwargs: B
    ) -> Parser[Sequence[KeyValue[B]]]:
        return cls.return_(Sequence([KeyValue(k, v) for k, v in kwargs.items()]))

    @classmethod
    def empty(cls: Type[Parser[Sequence[B]]]) -> Parser[Sequence[B]]:
        return cls.return_(Sequence([]))

    def many(self: "Parser[Sequence[B]]") -> "Parser[Sequence[B]]":
        """
        >>> from monad_argparse import Argument, Flag
        >>> p = Argument("as-many-as-you-like").many()
        >>> p.parse_args()
        []
        >>> p = Argument("as-many-as-you-like").many()
        >>> p.parse_args("a")
        [('as-many-as-you-like', 'a')]
        >>> p = Argument("as-many-as-you-like").many()
        >>> p.parse_args("a", "b")
        [('as-many-as-you-like', 'a'), ('as-many-as-you-like', 'b')]
        >>> p = Flag("verbose") | Flag("quiet")
        >>> p = p.many()  # parse zero or more copies
        >>> p.parse_args("--quiet", "--quiet", "--quiet")
        [('quiet', True), ('quiet', True), ('quiet', True)]
        >>> p.parse_args("--verbose", "--quiet", "--quiet")
        [('verbose', True), ('quiet', True), ('quiet', True)]
        """
        return self.many1() | Parser[Sequence[B]].empty()

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

        return Parser(lambda cs: f(tuple(cs)))

    def parse(self, cs: Sequence[str]) -> Result[Parse[A]]:
        return self.f(cs)

    def parse_args(
        self: "Parser[Sequence[KeyValue]]", *args: str
    ) -> typing.Sequence[KeyValueTuple] | Exception:
        result = self.parse(Sequence(list(args))).get
        if isinstance(result, Exception):
            return result
        parse: Parse[Sequence[KeyValue]] = result
        kvs: Sequence[KeyValue] = parse.parsed
        return [KeyValueTuple(**asdict(kv)) for kv in kvs]

    @classmethod
    def return_(cls, a: A) -> Parser[A]:  # type: ignore[misc]
        # see https://github.com/python/mypy/issues/6178#issuecomment-1057111790
        """
        >>> from monad_argparse.parser.key_value import KeyValue
        >>> Parser.return_(([KeyValue("some-key", "some-value")])).parse_args()
        [('some-key', 'some-value')]
        """

        def f(cs: Sequence[str]) -> Result[Parse[A]]:
            return Result(Parse(a, cs))

        return Parser(f)

    @classmethod
    def zero(cls: Type[Parser[A]], error: Optional[Exception] = None) -> Parser[A]:
        """
        >>> Parser.zero().parse_args()
        RuntimeError('zero')
        >>> Parser.zero().parse_args("a")
        RuntimeError('zero')
        >>> Parser.zero(error=RuntimeError("This is a test.")).parse_args("a")
        RuntimeError('This is a test.')
        """
        if error is None:
            error = RuntimeError("zero")
        result: Result[Parse[A]] = Result(error)
        return Parser(lambda _: result)
