"""
`Parser` is the class that powers `monad_argparse`.
"""
# pyright: reportGeneralTypeIssues=false
from __future__ import annotations

import typing
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Callable, Dict, Generator, Optional, Type, TypeVar

from pytypeclass import MonadPlus, Monoid
from pytypeclass.nonempty_list import NonemptyList

from monad_argparse.key_value import KeyValue, KeyValueTuple
from monad_argparse.parse import Parse
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence

A = TypeVar("A", bound=Monoid, covariant=True)
B = TypeVar("B", bound=Monoid)
C = TypeVar("C")
D = TypeVar("D", bound=Monoid)


def const(b: B) -> Parser[Sequence[B]]:
    return Parser.return_(Sequence([b]))


def empty() -> Parser[Sequence[B]]:
    return Parser.return_(Sequence([]))


@dataclass
class Parser(MonadPlus[A]):
    f: Callable[[Sequence[str]], Result[Parse[A]]]

    def __add__(
        self: Parser[Sequence[D]], other: Parser[Sequence[B]]
    ) -> Parser[Sequence[D | B]]:
        return (self >> other) | (other >> self)

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
        UnexpectedError(unexpected='--option')
        >>> p.parse_args("--option", "x")
        {'option': 'x'}
        """

        def f(cs: Sequence[str]) -> Result[Parse[A | B]]:
            return self.parse(cs) | other.parse(cs)

        return Parser(f)

    def __rshift__(
        self: Parser[Sequence[D]], p: Parser[Sequence[B]]
    ) -> Parser[Sequence[D | B]]:
        """
        >>> from monad_argparse import argument, flag
        >>> p = argument("first") >> argument("second")
        >>> p.parse_args("a", "b")
        {'first': 'a', 'second': 'b'}
        >>> p.parse_args("a")
        MissingError(missing='second')
        >>> p.parse_args("b")
        MissingError(missing='second')
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
        MissingError(missing='a')
        >>> p.parse_args("a")
        UnequalError(left='--verbose', right='a')
        """
        # def f(p1: Sequence[D]) -> Parser[Parse[Sequence[D | B]]]:
        #     def g(p2: Sequence[B]) -> Parser[Sequence[D | B]]:
        #         return Parser.return_(p1 + p2)

        #     return p >= g

        # return self >= f
        return self >= (lambda p1: (p >= (lambda p2: Parser.return_(p1 + p2))))

    def bind(self, f: Callable[[A], Parser[B]]) -> Parser[B]:
        def h(parse: Parse[A]) -> Result[Parse[B]]:
            return f(parse.parsed).parse(parse.unparsed)

        def g(cs: Sequence[str]) -> Result[Parse[B]]:
            return self.parse(cs) >= h

        return Parser(g)

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
        return self.many1() | empty()

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
        self: "Parser[Sequence[KeyValue]]", *args: str, return_dict: bool = True
    ) -> typing.Sequence[KeyValueTuple] | Exception | Dict[str, Any]:
        result = self.parse(Sequence(list(args))).get
        if isinstance(result, Exception):
            return result
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

        return Parser(f)

    @classmethod
    def zero(cls: Type[Parser[A]], error: Optional[Exception] = None) -> Parser[A]:
        """
        >>> Parser.zero().parse_args()
        ZeroError()
        >>> Parser.zero().parse_args("a")
        ZeroError()
        >>> Parser.zero(error=RuntimeError("This is a test.")).parse_args("a")
        RuntimeError('This is a test.')
        """
        return Parser(lambda _: Result.zero(error=error))
