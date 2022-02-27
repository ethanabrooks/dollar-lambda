from dataclasses import asdict
from functools import lru_cache
from typing import Callable, Generator, Optional, Sequence, Type, TypeVar, Union

from monad_argparse.monad.monad_plus import MonadPlus
from monad_argparse.monad.nonempty_list import NonemptyList
from monad_argparse.parser.error import ArgumentError
from monad_argparse.parser.key_value import KeyValue, KeyValueTuple
from monad_argparse.parser.parse import Parse, Parsed
from monad_argparse.parser.result import Ok, Result

A = TypeVar("A", covariant=True)
B = TypeVar("B", covariant=True)
C = TypeVar("C", covariant=True)


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
        ArgumentError(token='--yes', description='--yes')
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
        return self.many1() | Parser[Sequence[B]].return_(Parsed([]))

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
    def return_(cls: "Type[Parser[A]]", a: Parsed[A]) -> "Parser[A]":
        def f(cs: Sequence[str]) -> Result[NonemptyList[Parse[A]]]:
            return Result(Ok(NonemptyList(Parse(a, cs))))

        return Parser(f)

    @classmethod
    def zero(cls, error: Optional[Exception] = None) -> "Parser[A]":
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


class Sat(Parser[Sequence[KeyValue[str]]]):
    def __init__(self, predicate: Callable[[str], bool], description: str):
        def g() -> Generator[
            Union[ArgParser[str], Parser[Sequence[KeyValue[str]]]],
            Parsed[Sequence[KeyValue[str]]],
            None,
        ]:
            # noinspection PyTypeChecker
            parsed = yield Item(description)
            [kv] = parsed.get
            if predicate(kv.value):
                yield self.return_(parsed)
            else:
                yield self.zero(ArgumentError(token=kv.key, description=description))

        def f(
            cs: Sequence[str],
        ) -> Result[NonemptyList[Parse[Sequence[KeyValue[str]]]]]:
            return Parser[Sequence[KeyValue[str]]].do(g).parse(cs)

        super().__init__(f)


class Eq(Sat):
    def __init__(self, s):
        super().__init__(lambda s1: s == s1, description=f"equals {s}")


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


def matches_short_or_long(
    x: str,
    short: Optional[str] = None,
    long: Optional[str] = None,
) -> bool:
    if short is not None and x == f"-{short}":
        return True
    if long is not None and x == f"--{long}":
        return True
    return False


def flags(short: Optional[str] = None, long: Optional[str] = None):
    if short:
        yield f"-{short}"
    if long:
        yield f"--{long}"


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
        assert short or long

        def g() -> Generator[Parser, Parsed, None]:
            description = f"{' or '.join(list(flags(short, long)))}"
            yield Sat(
                lambda x: matches_short_or_long(x, short=short, long=long),
                description=description,
            )
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
            description = f"matches {' or '.join(list(flags(short, long)))}"
            yield Sat(
                lambda x: matches_short_or_long(x, short=short, long=long),
                description=description,
            )
            parsed = yield Item(f"argument for {next(flags(short, long))}")
            [kv] = parsed.get
            key = dest or long
            yield self.return_(Parsed([KeyValue(key, kv.value)]))

        super().__init__(g)
