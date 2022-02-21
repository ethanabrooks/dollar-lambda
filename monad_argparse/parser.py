import abc
from dataclasses import asdict, dataclass
from functools import lru_cache, partial
from typing import (
    Any,
    Callable,
    Generator,
    Generic,
    List,
    NamedTuple,
    Optional,
    TypeVar,
    Union,
    cast,
)

from monad_argparse.monad import Monad
from monad_argparse.nonempty_list import NonemptyList
from monad_argparse.stateless_iterator import StatelessIterator

A = TypeVar("A", contravariant=True)
B = TypeVar("B", contravariant=True)
MA = TypeVar("MA")
MB = TypeVar("MB", covariant=True)


class MonadZero(Monad[A, MA, MB]):
    @classmethod
    @abc.abstractmethod
    def zero(cls) -> MA:
        raise NotImplementedError


class MonadPlus(MonadZero[A, MA, MB]):
    @abc.abstractmethod
    def __add__(self, other: MA) -> MA:
        raise NotImplementedError


@dataclass
class KeyValue(Generic[A]):
    key: str
    value: A


class KeyValueTuple(NamedTuple):
    key: str
    value: Any

    def __repr__(self):
        return repr(tuple(self))


@dataclass
class Parsed(Generic[A]):
    get: A

    def __repr__(self):
        return f"Parsed({self.get})"

    def __rshift__(self, other: "Parsed[List[A]]"):
        assert isinstance(self.get, list)
        return Parsed(self.get + other.get)


@dataclass
class Parse(Generic[A]):
    parsed: Parsed[A]
    unparsed: List[str]


@dataclass
class ArgumentError(Exception):
    token: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Ok(Generic[A]):
    get: A

    def __repr__(self):
        return f"Ok({self.get})"


@dataclass
class Result(MonadPlus[A, "Result", "Result"], Generic[A]):
    get: Union[Ok[A], Exception]

    def __add__(self, other: "Result[B]") -> "Result":
        if isinstance(self.get, Ok):
            return self
        if isinstance(other.get, Ok):
            return other
        return Result(RuntimeError("__add__"))

    def __ge__(self, other: Callable[[A], "Result"]) -> "Result":
        return Result.bind(self, other)

    def __repr__(self):
        return f"Result({self.get})"

    def __rshift__(self, other: "Result[B]") -> "Result[Any]":
        def result():
            # noinspection PyTypeChecker
            o1: List[Ok[A]] = yield self
            # noinspection PyTypeChecker
            o2: List[Ok[B]] = yield other
            yield o1 + o2

        return Result.do(result)

    @classmethod
    def bind(
        cls,
        x: "Result[A]",
        f: Callable[[A], "Result[B]"],
    ) -> "Result[B]":
        y = x.get
        if isinstance(y, Exception):
            return cast(Result[B], x)
        return f(y.get)

    @classmethod
    def return_(cls, a: A) -> "Result[A]":
        return Result(Ok(a))

    @classmethod
    def zero(cls) -> "Result[A]":
        return Result(ArgumentError(description="zero"))


class Parser(MonadPlus[Parsed[A], "Parser", "Parser"], Generic[A]):
    """
    >>> def f():
    ...     x1 = yield Argument("first")
    ...     x2 = yield Argument("second")
    ...     yield Parser.return_(x1 >> x2)
    ...
    >>> Parser.do(f).parse_args("a", "b")
    [('first', 'a'), ('second', 'b')]
    >>> p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
    >>> p2 = p1.many()
    >>> def f():
    ...     xs1 = yield p2
    ...     x1 = yield Argument("first")
    ...     xs2 = yield p2
    ...     x2 = yield Argument("second")
    ...     xs3 = yield p2
    ...     yield Parser.return_(xs1 >> x1 >> xs2 >> x2 >> xs3)
    ...
    >>> Parser.do(f).parse_args("a", "--verbose", "b", "--quiet")
    [('first', 'a'), ('verbose', True), ('second', 'b'), ('quiet', True)]
    """

    def __init__(self, f: Callable[[List[str]], Result[NonemptyList[Parse[A]]]]):
        self.f = f

    def __add__(
        self,
        other: "Parser[A]",
    ) -> "Parser[A]":
        def f(cs: List[str]) -> Result[NonemptyList[Parse[A]]]:
            result = self.parse(cs)
            choices: Result[NonemptyList[Parse[A]]] = result + other.parse(cs)
            if isinstance(choices.get, Ok):
                return Result(Ok(NonemptyList(choices.get.get.head)))
            else:
                return result

        return Parser(f)

    def __or__(self, p: "Parser[A]") -> "Parser[A]":
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

        def f(cs: List[str]) -> Result[NonemptyList[Parse[A]]]:
            return (self + p).parse(cs)

        return Parser(f)

    def __rshift__(self, p: "Parser[List[B]]") -> "Parser[List[B]]":
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
        ArgumentError(token='--verbose', description='--verbose')
        >>> p.parse_args("--verbose")
        ArgumentError(token=None, description='Missing: a')
        """

        def g() -> Generator[Any, Parsed[List[B]], None]:
            # noinspection PyTypeChecker
            p1: Parsed[List[B]] = yield self
            # noinspection PyTypeChecker
            p2: Parsed[List[B]] = yield p
            yield p.return_(Parsed(p1.get + p2.get))

        return Parser.do(g)

    @classmethod
    def bind(cls, x: "Parser", f: Callable[[Parsed[A]], "Parser[A]"]) -> "Parser[A]":
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

        def g(cs: List[str]) -> Result[NonemptyList[Parse[A]]]:
            return x.parse(cs) >= h

        return Parser(g)

    @classmethod
    def do(cls, generator: Callable[[], Generator["Parser", Parsed[A], None]]):
        def f(
            a: Optional[Parsed[A]], it: StatelessIterator["Parser", Parsed[A]]
        ) -> "Parser":
            try:
                ma: Parser
                it2: StatelessIterator["Parser", Parsed[A]]
                if a is None:
                    ma, it2 = it.__next__()
                else:
                    ma, it2 = it.send(a)
            except StopIteration:
                if a is None:
                    raise RuntimeError("Cannot use an empty iterator with do.")
                return cls.return_(a)
            return cls.bind(ma, partial(f, it=it2))

        return f(None, StatelessIterator(generator))

    def many(self) -> "Parser[List[A]]":
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
        return self.many1() | Parser[List[A]].return_(Parsed([]))

    def many1(self):
        def g() -> Generator["Parser", Parsed, None]:
            # noinspection PyTypeChecker
            r1: Parsed[List[A]] = yield self
            # noinspection PyTypeChecker
            r2: Parsed[List[A]] = yield self.many()
            yield Parser[List[A]].return_(Parsed(r1.get + r2.get))

        @lru_cache()
        def f(cs: tuple):
            return Parser.do(g).parse(list(cs))

        return Parser(lambda cs: f(tuple(cs)))

    def parse(self, cs: List[str]) -> Result:
        return self.f(cs)

    def parse_args(self, *args: str) -> Union[List[KeyValueTuple], Exception]:
        result = self.parse(list(args)).get
        if isinstance(result, Exception):
            return result
        parse: NonemptyList[Parse[List[KeyValue]]] = result.get
        head: Parse[List[KeyValue]] = parse.head
        parsed: Parsed[List[KeyValue]] = head.parsed
        pairs: List[KeyValue] = parsed.get
        return [KeyValueTuple(**asdict(kv)) for kv in pairs]

    @classmethod
    def return_(cls, a: Parsed[A]) -> "Parser":
        def f(cs: List[str]) -> Result[NonemptyList[Parse[A]]]:
            return Result(Ok(NonemptyList(Parse(a, cs))))

        return Parser(f)

    @classmethod
    def zero(cls, error: Optional[Exception] = None) -> "Parser[A]":
        if error is None:
            error = RuntimeError("zero")
        result: Result[NonemptyList[Parse[A]]] = Result(error)
        return Parser(lambda cs: result)


class Check(Parser[List[A]]):
    """
    >>> Check(lambda c: c.startswith('c'), "Does not start with c").parse_args("c")
    []
    >>> Check(lambda c: c.startswith('c'), "Does not start with c").parse_args()
    []
    >>> Check(lambda c: c.startswith('c'), "Does not start with c").parse_args("d")
    ArgumentError(token='d', description='Does not start with c: d')
    """

    def __init__(self, predicate: Callable[[str], bool], description: str):
        def f(cs: List[str]) -> Result[NonemptyList[Parse[List[A]]]]:
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


class Empty(Parser[List[A]]):
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
        def f(cs: List[str]) -> Result[NonemptyList[Parse[List[A]]]]:
            if cs:
                c, *_ = cs
                return Result(
                    ArgumentError(token=c, description=f"Unexpected argument: {c}")
                )
            return Result(Ok(NonemptyList(Parse(parsed=Parsed([]), unparsed=cs))))

        super().__init__(f)


class Item(Parser[List[KeyValue[str]]]):
    def __init__(self, name: str, description: Optional[str] = None):
        def f(cs: List[str]) -> Result[NonemptyList[Parse[List[KeyValue[str]]]]]:
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


class Sat(Parser[List[KeyValue[str]]]):
    def __init__(self, predicate: Callable[[str], bool], description: str):
        def g() -> Generator[Parser, Parsed[List[KeyValue[str]]], None]:
            # noinspection PyTypeChecker
            parsed = yield Item(description)
            [kv] = parsed.get
            if predicate(kv.value):
                yield self.return_(parsed)
            else:
                yield self.zero(ArgumentError(token=kv.key, description=description))

        def f(cs: List[str]) -> Result[NonemptyList[Parse[List[KeyValue[str]]]]]:
            return Parser[List[KeyValue[str]]].do(g).parse(cs)

        super().__init__(f)


class Eq(Sat):
    def __init__(self, s):
        super().__init__(lambda s1: s == s1, description=f"equals {s}")


class DoParser(Parser[A]):
    def __init__(self, g: Callable[[], Generator[Parser, Parsed[A], None]]):
        def f(cs: List[str]) -> Result[NonemptyList[Parse[A]]]:
            return Parser.do(g).parse(cs)

        super().__init__(f)


class Argument(DoParser[A]):
    """
    >>> Argument("name").parse_args("Alice")
    [('name', 'Alice')]
    >>> Argument("name").parse_args()
    ArgumentError(token=None, description='Missing: name')
    """

    def __init__(self, dest: str):
        def g() -> Generator[Parser, Parsed, None]:
            yield Item(dest)

        super().__init__(g)


def matches_short_or_long(
    x: str,
    short: Optional[str] = None,
    long: Optional[str] = None,
) -> bool:
    x
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


class Flag(DoParser):
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


class Option(DoParser):
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
        convert: Optional[Callable[[A], Any]] = None,
        dest: Optional[str] = None,
    ):
        def g() -> Generator[Parser, Parsed[List[KeyValue]], None]:
            description = f"matches {' or '.join(list(flags(short, long)))}"
            yield Sat(
                lambda x: matches_short_or_long(x, short=short, long=long),
                description=description,
            )
            parsed = yield Item(f"argument for {next(flags(short, long))}")
            [kv] = parsed.get
            key = dest or long
            value = kv.value if convert is None else convert(kv.value)
            yield self.return_(Parsed([KeyValue(key, value)]))

        super().__init__(g)
