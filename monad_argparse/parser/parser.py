import typing
from dataclasses import asdict, replace
from functools import lru_cache, reduce
from typing import Any, Callable, Generator, Generic, Optional, Sequence, TypeVar, Union

from monad_argparse.monad.monad_plus import MonadPlus
from monad_argparse.monad.nonempty_list import NonemptyList
from monad_argparse.parser.error import ArgumentError
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


class Check(Parser[Sequence[A]]):
    """
    >>> Check(lambda c: c.startswith('c'), "Does not start with c").parse_args("c")
    []
    >>> Check(lambda c: c.startswith('c'), "Does not start with c").parse_args()
    []
    >>> Check(lambda c: c.startswith('c'), "Does not start with c").parse_args("d")
    ArgumentError(token='d', description='Does not start with c: d')
    """

    def __init__(self, predicate: Callable[[str], bool], description: str):
        def f(cs: Sequence[str]) -> Result[NonemptyList[Parse[Sequence[A]]]]:
            if cs:
                c, *_ = cs
                if predicate(c):
                    return Result(
                        Ok(NonemptyList(Parse(parsed=Parsed([]), unparsed=cs)))
                    )
                else:
                    return Result(
                        ArgumentError(token=c, description=f"{description}: {c}")
                    )
            return Result(Ok(NonemptyList(Parse(parsed=Parsed([]), unparsed=cs))))

        super().__init__(f)


class Empty(Parser[Sequence[A]]):
    """
    >>> Empty().parse_args()
    []
    >>> Empty().parse_args("arg")
    ArgumentError(token='arg', description='Unexpected argument: arg')
    >>> (Argument("arg") >> Empty()).parse_args("a")
    [('arg', 'a')]
    >>> (Argument("arg") >> Empty()).parse_args("a", "b")
    ArgumentError(token='b', description='Unexpected argument: b')
    >>> (Flag("arg").many() >> Empty()).parse_args("--arg", "--arg")
    [('arg', True), ('arg', True)]
    >>> (Flag("arg").many() >> Empty()).parse_args("--arg", "--arg", "x")
    ArgumentError(token='x', description='Unexpected argument: x')
    """

    def __init__(self):
        def f(cs: Sequence[str]) -> Result[NonemptyList[Parse[Sequence[A]]]]:
            if cs:
                c, *_ = cs
                return Result(
                    ArgumentError(token=c, description=f"Unexpected argument: {c}")
                )
            return Result(Ok(NonemptyList(Parse(parsed=Parsed([]), unparsed=cs))))

        super().__init__(f)


A = TypeVar("A", covariant=True)  # type: ignore[misc]


class ArgParser(Parser[Sequence[KeyValue[A]]]):

    pass


D = TypeVar("D", covariant=True)
E = TypeVar("E", covariant=True)


class Apply(Parser[E], Generic[D, E]):
    def __init__(
        self,
        f: Callable[[D], Result[E]],
        parser: Parser[D],
    ):
        def h() -> Generator[
            Parser[Union[D, E]],
            Parsed[D],
            None,
        ]:
            # noinspection PyTypeChecker
            parsed: Parsed[D] = yield parser
            y = f(parsed.get)
            if isinstance(y.get, Exception):
                yield self.zero(y.get)
            elif isinstance(y.get, Ok):
                yield Parser[E].return_(Parsed(y.get.get))

        def g(
            cs: Sequence[str],
        ) -> Result[NonemptyList[Parse[E]]]:
            do = Parser[E].do(h)  # type: ignore[arg-type]
            # The suppression of the type-checker is unfortunately unavoidable here because our definition of `do` requires
            # the type to remain the same throughout the do block as a consequence of the way that python types generators.
            return do.parse(cs)

        super().__init__(g)


class Type(Apply[Sequence[KeyValue[str]], Sequence[KeyValue[Any]]]):
    """
    >>> Type(int, Argument("arg")).parse_args("1")
    [('arg', 1)]
    >>> Type(int, Argument("arg")).parse_args("one")
    ValueError("invalid literal for int() with base 10: 'one'")
    """

    def __init__(
        self, f: Callable[[str], Any], parser: Parser[Sequence[KeyValue[str]]]
    ):
        def g(
            kvs: Sequence[KeyValue[str]],
        ) -> Result[Sequence[KeyValue[Any]]]:
            head, *tail = kvs
            try:
                head = replace(head, value=f(head.value))
            except Exception as e:
                return Result(e)

            return Result(Ok([*tail, head]))

        super().__init__(g, parser)


class Item(Parser[Sequence[KeyValue[str]]]):
    def __init__(self, name: str, description: Optional[str] = None):
        def f(
            cs: Sequence[str],
        ) -> Result[NonemptyList[Parse[Sequence[KeyValue[str]]]]]:
            if cs:
                c, *cs = cs
                return Result(
                    Ok(
                        NonemptyList(
                            Parse(parsed=Parsed([KeyValue(name, c)]), unparsed=cs)
                        )
                    )
                )
            return Result(ArgumentError(description=f"Missing: {description or name}"))

        super().__init__(f)


F = TypeVar("F")


class Sat(Apply[F, F]):
    def __init__(
        self,
        parser: Parser[F],
        predicate: Callable[[F], bool],
        on_fail: Callable[[F], ArgumentError],
    ):
        def f(x: F) -> Result[F]:
            return Result(Ok(x) if predicate(x) else on_fail(x))

        super().__init__(f, parser)


class SatItem(Sat[Sequence[KeyValue[str]]]):
    def __init__(
        self,
        predicate: Callable[[str], bool],
        on_fail: Callable[[str], ArgumentError],
        description: str,
    ):
        def _predicate(parsed: Sequence[KeyValue[str]]) -> bool:
            [kv] = parsed
            return predicate(kv.value)

        def _on_fail(parsed: Sequence[KeyValue[str]]) -> ArgumentError:
            [kv] = parsed
            return on_fail(kv.value)

        super().__init__(Item(description), _predicate, _on_fail)


class DoParser(Parser[Sequence[KeyValue[A]]]):
    def __init__(
        self,
        g: Callable[
            [],
            Generator[
                Parser[Sequence[KeyValue[A]]], Parsed[Sequence[KeyValue[A]]], None
            ],
        ],
    ):
        def f(cs: Sequence[str]) -> Result[NonemptyList[Parse[Sequence[KeyValue[A]]]]]:
            return Parser.do(g).parse(cs)

        super().__init__(f)


class Argument(DoParser[str]):
    """
    >>> Argument("name").parse_args("Alice")
    [('name', 'Alice')]
    >>> Argument("name").parse_args()
    ArgumentError(token=None, description='Missing: name')
    """

    def __init__(self, dest: str):
        def g() -> Generator[
            Parser[Sequence[KeyValue[str]]], Parsed[Sequence[KeyValue[str]]], None
        ]:
            yield Item(dest)

        super().__init__(g)


def flags(long: Optional[str] = None, short: Optional[str] = None):
    if short:
        yield f"-{short}"
    if long:
        yield f"--{long}"


class MatchesFlag(SatItem):
    def __init__(
        self,
        long: Optional[str] = None,
        short: Optional[str] = None,
    ):
        assert long or short, "Either long or short must be provided."

        def matches(x: str) -> bool:
            if short is not None and x == f"-{short}":
                return True
            if long is not None and x == f"--{long}":
                return True
            return False

        flags_string = f"{' or '.join(list(flags(short=short, long=long)))}"

        super().__init__(
            matches,
            on_fail=lambda a: ArgumentError(
                a, description=f"Input '{a}' does not match '{flags_string}"
            ),
            description=flags_string,
        )


class Flag(DoParser[bool]):
    """
    >>> Flag("verbose").parse_args("--verbose")
    [('verbose', True)]
    >>> Flag("verbose").parse_args()
    ArgumentError(token=None, description='Missing: --verbose')
    >>> Flag("verbose").parse_args("--verbose", "--verbose", "--verbose")
    [('verbose', True)]
    """

    def __init__(
        self,
        long: str,
        short: Optional[str] = None,
        dest: Optional[str] = None,
        value: bool = True,
    ):
        assert short or long, "Either short or long must be specified."

        def g() -> Generator[Parser, Parsed, None]:
            yield MatchesFlag(long=long, short=short)
            yield self.return_(Parsed([KeyValue((dest or long), value)]))

        super().__init__(g)


class Option(DoParser[str]):
    """
    >>> Option("value").parse_args("--value", "x")
    [('value', 'x')]
    >>> Option("value").parse_args("--value")
    ArgumentError(token=None, description='Missing: argument for --value')
    """

    def __init__(
        self,
        long: str,
        short: Optional[str] = None,
        dest: Optional[str] = None,
    ):
        def g() -> Generator[Parser, Parsed[Sequence[KeyValue[str]]], None]:
            yield MatchesFlag(long=long, short=short)
            parsed = yield Item(f"argument for {next(flags(short=short, long=long))}")
            [kv] = parsed.get
            key = dest or long
            yield self.return_(Parsed([KeyValue(key, kv.value)]))

        super().__init__(g)
