import typing
from dataclasses import asdict
from functools import lru_cache, reduce
from typing import Callable, Generator, Optional, Sequence, TypeVar, Union

from monad_argparse.monad.monad_plus import MonadPlus
from monad_argparse.monad.nonempty_list import NonemptyList
from monad_argparse.parser.key_value import KeyValue, KeyValueTuple
from monad_argparse.parser.parse import Parse, Parsed
from monad_argparse.parser.result import Ok, Result

A = TypeVar("A", covariant=True)
B = TypeVar("B")
C = TypeVar("C")


class Parser(MonadPlus[Parsed[A], "Parser[A]"]):
    def __init__(self, f: Callable[[Sequence[str]], Result[NonemptyList[Parse[A]]]]):
        self.f = f

    def __or__(
        self: "Parser[B]",
        other: "Parser[C]",
    ) -> "Parser[Union[B, C]]":
        """
        >>> from monad_argparse import Argument, Option, Empty, Flag
        >>> p = Flag("verbose") | Option("option")
        >>> p.parse_args("--verbose")
        [('verbose', True)]
        >>> p.parse_args("--verbose", "--option", "x")
        [('verbose', True)]
        >>> (p >> Empty()).parse_args("--verbose", "--option", "x")
        ArgumentError(token='--option', description='Unexpected argument: --option')
        >>> p.parse_args("--option", "x")
        [('option', 'x')]
        """

        def f(cs: Sequence[str]) -> Result[NonemptyList[Parse[Union[B, C]]]]:
            r1: Result[NonemptyList[Parse[B]]] = self.parse(cs)
            r2: Result[NonemptyList[Parse[C]]] = other.parse(cs)
            choices: Result[
                Union[NonemptyList[Parse[B]], NonemptyList[Parse[C]]]
            ] = r1.__or__(r2)
            if isinstance(choices.get, Ok):
                return Result(Ok(NonemptyList(choices.get.get.head)))
            else:
                return r2

        return Parser(f)

    def __rshift__(
        self: "Parser[Sequence[B]]", p: "Parser[Sequence[C]]"
    ) -> "Parser[Sequence[Union[B, C]]]":
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

        def g() -> Generator[
            Parser[Sequence[Union[B, C]]],
            Parsed[Sequence[Union[B, C]]],
            None,
        ]:
            # noinspection PyTypeChecker
            p1: Parsed[Sequence[Union[B, C]]] = yield self
            # noinspection PyTypeChecker
            p2: Parsed[Sequence[Union[B, C]]] = yield p
            p3: Parsed[Sequence[Union[B, C]]] = p1 >> p2
            yield Parser[Sequence[Union[B, C]]].return_(p3)

        return Parser.do(g)

    @staticmethod
    def bind(x: "Parser[A]", f: Callable[[Parsed[A]], "Parser[A]"]) -> "Parser[A]":  # type: ignore[override]
        def apply_parser(parse: Parse[A]) -> Result[NonemptyList[Parse[A]]]:
            return f(parse.parsed).parse(parse.unparsed)

        def get_successful(
            parses: NonemptyList[Parse[A]],
        ) -> Generator[Parse[A], None, None]:
            for parse in parses:
                result: Result[NonemptyList[Parse[A]]] = apply_parser(parse)
                if isinstance(result.get, Ok):  # Exclude failed parses
                    yield from result.get.get

        def h(parses: NonemptyList[Parse[A]]) -> Result[NonemptyList[Parse[A]]]:
            successful_parses = NonemptyList.make(*get_successful(parses))
            if successful_parses:
                return Result(Ok(successful_parses))
            return apply_parser(parses.head)

        def g(cs: Sequence[str]) -> Result[NonemptyList[Parse[A]]]:
            return x.parse(cs) >= h

        return Parser(g)

    @classmethod
    def empty(cls: "typing.Type[Parser[Sequence[B]]]") -> "Parser[Sequence[B]]":
        return cls.return_(Parsed([]))

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
        def g() -> Generator["Parser[Sequence[B]]", Parsed[Sequence[B]], None]:
            # noinspection PyTypeChecker
            r1: Parsed[Sequence[B]] = yield self
            # noinspection PyTypeChecker
            r2: Parsed[Sequence[B]] = yield self.many()
            yield Parser[Sequence[B]].return_(r1 >> r2)

        @lru_cache()
        def f(cs: tuple):
            return Parser.do(g).parse(list(cs))

        return Parser(lambda cs: f(tuple(cs)))

    @classmethod
    def nonpositional(cls, *parsers: "Parser[Sequence[B]]") -> "Parser[Sequence[B]]":
        """
        >>> from monad_argparse import Argument, Flag
        >>> p = Parser.nonpositional(Flag("verbose"), Flag("debug"))
        >>> p.parse_args("--verbose", "--debug")
        [('verbose', True), ('debug', True)]
        >>> p.parse_args("--debug", "--verbose")
        [('debug', True), ('verbose', True)]
        >>> p.parse_args()
        ArgumentError(token=None, description='Missing: --debug')
        >>> p.parse_args("--debug")
        ArgumentError(token=None, description='Missing: --verbose')
        >>> p.parse_args("--verbose")
        ArgumentError(token='--verbose', description="Input '--verbose' does not match '--debug")
        >>> p = Parser.nonpositional(Flag("verbose"), Flag("debug"), Argument("a"))
        >>> p.parse_args("--debug", "hello", "--verbose")
        [('debug', True), ('a', 'hello'), ('verbose', True)]
        """
        if not parsers:
            return Parser[Sequence[B]].empty()

        def get_alternatives():
            for i, head in enumerate(parsers):
                tail = [p for j, p in enumerate(parsers) if j != i]
                yield head >> cls.nonpositional(*tail)

        def _or(
            p1: Parser[Sequence[B]], p2: Parser[Sequence[B]]
        ) -> Parser[Sequence[B]]:
            return p1 | p2

        return reduce(_or, get_alternatives())

    def parse(self, cs: Sequence[str]) -> Result[NonemptyList[Parse[A]]]:
        return self.f(cs)

    def parse_args(
        self: "Parser[Sequence[KeyValue]]", *args: str
    ) -> Union[Sequence[KeyValueTuple], Exception]:
        result = self.parse(list(args)).get
        if isinstance(result, Exception):
            return result
        parse: NonemptyList[Parse[Sequence[KeyValue]]] = result.get
        head: Parse[Sequence[KeyValue]] = parse.head
        parsed: Parsed[Sequence[KeyValue]] = head.parsed
        pairs: Sequence[KeyValue] = parsed.get
        return [KeyValueTuple(**asdict(kv)) for kv in pairs]

    @classmethod
    def return_(cls: "typing.Type[Parser[A]]", a: Parsed[A]) -> "Parser[A]":
        """
        >>> Parser.return_(Parsed([KeyValue("some-key", "some-value")])).parse_args()
        [('some-key', 'some-value')]
        """

        def f(cs: Sequence[str]) -> Result[NonemptyList[Parse[A]]]:
            return Result(Ok(NonemptyList(Parse(a, cs))))

        return Parser(f)

    @classmethod
    def zero(cls, error: Optional[Exception] = None) -> "Parser[A]":
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
        result: Result[NonemptyList[Parse[A]]] = Result(error)
        return Parser(lambda cs: result)
