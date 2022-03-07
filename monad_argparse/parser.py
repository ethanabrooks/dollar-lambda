"""
`Parser` is the class that powers `monad_argparse`.
"""
# pyright: reportGeneralTypeIssues=false
from __future__ import annotations

import typing
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from typing import Any, Callable, Dict, Generator, NoReturn, Optional, Type, TypeVar

from pytypeclass import MonadPlus, Monoid
from pytypeclass.nonempty_list import NonemptyList

from monad_argparse.error import ArgumentError
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
        >>> Parser._exit = lambda _: None  # Need to mock _exit for doctests
        >>> (p >> done()).parse_args("--verbose", "--option", "x")
        usage: [--option OPTION | --verbose]
        Unrecognized argument: --option
        >>> p.parse_args("--option", "x")
        {'option': 'x'}
        """

        def f(cs: Sequence[str]) -> Result[Parse[A | B]]:
            return self.parse(cs) | other.parse(cs)

        return Parser(f, usage=binary_usage(self.usage, " | ", other.usage))

    def __rshift__(
        self: Parser[Sequence[D]], p: Parser[Sequence[B]]
    ) -> Parser[Sequence[D | B]]:
        """
        >>> from monad_argparse import argument, flag
        >>> p = argument("first") >> argument("second")
        >>> p.parse_args("a", "b")
        {'first': 'a', 'second': 'b'}
        >>> Parser._exit = lambda _: None  # Need to mock _exit for doctests
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
        >>> Parser._exit = lambda _: ()
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

        return Parser(g, usage=None)

    @staticmethod
    def _exit() -> NoReturn:
        exit()

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

        return Parser(lambda cs: f(tuple(cs)), usage=f"{self.usage} [{self.usage} ...]")

    def parse(self, cs: Sequence[str]) -> Result[Parse[A]]:
        return self.f(cs)

    def parse_args(
        self: "Parser[Sequence[KeyValue]]", *args: str, return_dict: bool = True
    ) -> typing.Sequence[KeyValueTuple] | Dict[str, Any]:
        result = self.parse(Sequence(list(args))).get
        if isinstance(result, ArgumentError):
            if self.usage:
                print("usage:", end="\n" if "\n" in self.usage else " ")
                if "\n" in self.usage:
                    usage = "\n".join(["    " + u for u in self.usage.split("\n")])
                else:
                    usage = self.usage
                print(usage)
            if result.usage:
                print(result.usage)
            self._exit()
            return

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

        return Parser(f, usage=None)

    @classmethod
    def zero(cls: Type[Parser[A]], error: Optional[ArgumentError] = None) -> Parser[A]:
        """
        >>> Parser._exit = lambda _: None  # Need to mock _exit for doctests
        >>> Parser.zero().parse_args()
        zero
        >>> Parser.zero().parse_args("a")
        zero
        >>> Parser.zero(error=ArgumentError("This is a test.")).parse_args("a")
        This is a test.
        """
        return Parser(lambda _: Result.zero(error=error), usage=None)
