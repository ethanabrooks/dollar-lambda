import abc
from dataclasses import asdict, dataclass
from typing import (
    Any,
    Callable,
    Generator,
    Generic,
    List,
    NamedTuple,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from monad_argparse.monad import BaseMonad, M, Monad
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
class Ok(Generic[A]):
    parsed: List[A]
    remainder: List[str]


@dataclass
class ArgumentError(Exception):
    token: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Result(BaseMonad[A, "Result", "Result"]):
    get: Union[Ok[A], Exception]

    @classmethod
    def bind(  # type: ignore[override]
        cls,
        x: "Result[A]",
        f: Callable[[Ok[A]], "Result[B]"],
    ) -> "Result[B]":
        y = x.get
        if isinstance(y, Exception):
            return cast(Result[B], x)
        return f(y)

    def is_error(self):
        return isinstance(self.get, Exception)

    def is_ok(self):
        return not self.is_error()

    @staticmethod
    def ok(parsed: List[A], remainder: List[str]):
        assert isinstance(parsed, list)
        return Result(Ok(parsed, remainder))

    @classmethod
    def return_(cls, a: Union[Ok[A], Exception]) -> "Result[A]":  # type: ignore[override]
        return Result(a)

    def __rshift__(self, other: "Result"):
        def result():
            o1 = yield self
            o2 = yield other
            yield Ok(parsed=o1.parsed + o2.parsed, remainder=o2.remainder)

        return Result.do(result)


class Parser(MonadPlus[A, "Parser", "Parser"]):
    """
    >>> def f():
    ...     x1 = yield Argument("first")
    ...     x2 = yield Argument("second")
    ...     yield Parser.return_(x1 + x2)
    ...
    >>> Parser.do(f).parse_args("a", "b")
    [('first', 'a'), ('second', 'b')]
    """

    # >>>
    # >>> p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
    # >>> p2 = p1.many()
    # >>> def f():
    # ...     xs1 = yield p2
    # ...     x1 = yield Argument("first")
    # ...     xs2 = yield p2
    # ...     x2 = yield Argument("second")
    # ...     xs3 = yield p2
    # ...     yield Parser.return_(xs1 + x1 + xs2 + x2 + xs3)
    # ...
    # >>> Parser.do(f).parse_args("a", "--verbose", "b", "--quiet")
    # [('first', 'a'), ('verbose', True), ('second', 'b'), ('quiet', True)]

    def __init__(self, f: Callable[[List[str]], Result[A]]):
        self.f = f

    def __add__(
        self,
        other: "Parser",
    ) -> "Parser":
        def f(cs: List[str]) -> Result[A]:
            results = first, _ = [self.parse(cs), other.parse(cs)]
            for result in results:
                if result.is_ok():
                    return result
            return first

        return Parser(f)

    def __or__(self, p: "Parser") -> "Parser":
        """
        >>> p = Flag("verbose") | Option("option")
        >>> p.parse_args("--verbose")
        [('verbose', True)]
        >>> p.parse_args("--verbose", "--option", "x")  # TODO: shouldn't this throw an error?
        [('verbose', True)]
        >>> p.parse_args("--option", "x")
        [('option', 'x')]
        """

        def f(cs: List[str]) -> Result[A]:
            def results():
                yield (self + p).parse(cs)

            return Result.do(results)

        return Parser(f)

    def __rshift__(self, p: "Parser") -> "Parser":
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
        >>> p.parse_args("--verbose")
        ArgumentError(token=None, description='Missing: a')
        >>> p.parse_args("value")
        ArgumentError(token='value', description='matches --verbose')
        """

        def g() -> Generator[Any, List[KeyValue[A]], None]:
            r1 = yield self
            r2 = yield p
            yield self.return_(r1 + r2)

        return Parser.do(g)

    @classmethod
    def bind(cls, x: "Parser", f: Callable[[List[B]], "Parser"]) -> "Parser":  # type: ignore[override]
        def g(cs: List[str]) -> Result[B]:
            def results() -> Generator[Result[B], Ok[B], None]:
                parse = x.parse(cs)
                out: Ok[B] = yield parse
                parser = f(out.parsed)
                yield parser.parse(out.remainder)

            return Result.do(results)

        return Parser(g)

    def many(self) -> "Parser":
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
        return self.many1() | self.return_([])

    def many1(self):
        def g() -> Generator["Parser", List[KeyValue[A]], None]:
            r1 = yield self
            r2 = yield self.many()
            yield self.return_(r1 + r2)

        def f(cs):
            return Parser.do(g).parse(cs)

        return Parser(f)

    def parse(self, cs: List[str]) -> Result:
        return self.f(cs)

    def parse_args(self, *args: str) -> Union[List[KeyValueTuple], Exception]:
        result = self.parse(list(args)).get
        if isinstance(result, Ok):
            return [KeyValueTuple(**asdict(kv)) for kv in result.parsed]
        return result

    @classmethod
    def return_(cls, a: List[B]) -> "Parser":  # type: ignore[override]
        def f(cs: List[str]) -> Result[B]:
            return Result.ok(parsed=a, remainder=cs)

        return Parser(f)

    @classmethod
    def zero(cls, error: Exception = None) -> "Parser":
        if error is None:
            error = RuntimeError("zero")
        result: Result[A] = Result(error)
        return Parser(lambda cs: result)


class P(M, Generic[A]):
    def __ge__(self, f: Callable[[List[A]], Parser]):  # type: ignore[override]
        return Parser.bind(self.a, f)

    @classmethod
    def return_(cls, a: List[A]) -> "P[Parser]":
        return P(Parser.return_(a))


class Item(Parser):
    def __init__(self, description: str):
        def f(cs: List[str]) -> Result[str]:
            try:
                c, *cs = cs
                return Result.ok(parsed=[c], remainder=cs)
            except ValueError:
                return Result(ArgumentError(description=f"Missing{description}"))

        super().__init__(f)


class Sat(Parser, Generic[A]):
    def __init__(self, predicate: Callable[[List[str]], bool], description: str):
        def g() -> Generator[Parser, List[str], None]:
            cs = [c] = yield Item(description)
            if predicate(cs):
                yield self.return_(cs)
            else:
                yield self.zero(ArgumentError(token=c, description=description))

        def f(cs: List[str]) -> Result:
            return Parser.do(g).parse(cs)

        super().__init__(f)


class Eq(Sat):
    def __init__(self, s):
        super().__init__(lambda s1: s == s1, description=f"equals {s}")


class DoParser(Parser):
    def __init__(self, g):
        def f(cs):
            return Parser.do(g).parse(cs)

        super().__init__(f)


class Argument(DoParser):
    """
    >>> Argument("name").parse_args("Alice")
    [('name', 'Alice')]
    >>> Argument("name").parse_args()
    ArgumentError(token=None, description='Missing: name')
    """

    def __init__(self, dest: str):
        def g() -> Generator[Parser, List[str], None]:
            [c] = yield Item(f": {dest}")
            yield self.return_([KeyValue(dest, c)])

        super().__init__(g)


class Flag(DoParser):
    """
    >>> Flag("verbose").parse_args("--verbose")
    [('verbose', True)]
    >>> Flag("verbose").parse_args() # TODO: fix this
    ArgumentError(token=None, description='Missingmatches --verbose')
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

        def predicate(xs: List[str]) -> bool:
            [x] = xs
            if short is not None and x == f"-{short}":
                return True
            if long is not None and x == f"--{long}":
                return True
            return False

        def g() -> Generator[Parser, Tuple[Any, StatelessIterator], None]:
            def flags():
                if short:
                    yield f"-{short}"
                if long:
                    yield f"--{long}"

            description = f"matches {' or '.join(list(flags()))}"
            yield Sat[List[str]](predicate, description=description)
            yield self.return_([KeyValue((dest or long), value)])

        super().__init__(g)


class Option(DoParser):
    """
    >>> Option("value").parse_args("--value", "x")
    [('value', 'x')]
    >>> Option("value").parse_args("--value")
    ArgumentError(token=None, description='Missing argument for --value')
    """

    def __init__(
        self,
        long: str,
        short: Optional[str] = None,
        convert: Optional[Callable[[str], Any]] = None,
        dest: Optional[str] = None,
    ):
        def predicate(xs: List[str]) -> bool:
            [x] = xs
            if short is not None and x == f"-{short}":
                return True
            if long is not None and x == f"--{long}":
                return True
            return False

        def g() -> Generator[Parser, List[str], None]:
            def flags():
                if short:
                    yield f"-{short}"
                if long:
                    yield f"--{long}"

            description = f"matches {' or '.join(list(flags()))}"
            yield Sat[List[str]](predicate, description=description)
            [c2] = yield Item(f" argument for {next(flags())}")
            key = dest or long
            value = c2 if convert is None else convert(c2)
            yield self.return_([KeyValue(key, value)])

        super().__init__(g)
