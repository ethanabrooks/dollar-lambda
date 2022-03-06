"""
Contains all the functions for generating parsers tailored for parsing command line arguments.
"""
from dataclasses import Field, dataclass, fields, replace
from functools import partial, reduce
from typing import Any, Callable, Generator, Optional, TypeVar

from pytypeclass import MonadPlus
from pytypeclass.nonempty_list import NonemptyList

from monad_argparse.error import (
    ArgumentError,
    MissingError,
    UnequalError,
    UnexpectedError,
)
from monad_argparse.key_value import KeyValue
from monad_argparse.parse import Parse
from monad_argparse.parser import Parser
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence

A = TypeVar("A", bound=MonadPlus)
B = TypeVar("B")
C = TypeVar("C", covariant=True, bound=MonadPlus)
D = TypeVar("D", bound=MonadPlus)


def apply(f: Callable[[D], Result[C]], parser: Parser[D]) -> Parser[C]:
    return parser >= (
        lambda d: Parser(
            lambda unparsed: f(d)
            >= (lambda parsed: Result.return_(Parse(parsed, unparsed)))
        )
    )


def apply_item(f: Callable[[str], C], description: str) -> Parser[C]:
    def g(parsed: Sequence[KeyValue[str]]) -> Result[C]:
        [kv] = parsed
        try:
            y = f(kv.value)
        except Exception as e:
            return Result(e)
        return Result.return_(y)

    return apply(g, item(description))


def argument(dest: str) -> Parser[Sequence[KeyValue[str]]]:
    """
    >>> argument("name").parse_args("Alice")
    {'name': 'Alice'}
    >>> argument("name").parse_args()
    MissingError(missing='name')
    """
    return item(dest)


def default(**kwargs: Any) -> Parser[Sequence[KeyValue[Any]]]:
    return Parser.return_(Sequence([KeyValue(k, v) for k, v in kwargs.items()]))


def done() -> Parser[Sequence[B]]:
    """
    >>> done().parse_args()
    {}
    >>> done().parse_args("arg")
    UnexpectedError(unexpected='arg')
    >>> (argument("arg") >> done()).parse_args("a")
    {'arg': 'a'}
    >>> (argument("arg") >> done()).parse_args("a", "b")
    UnexpectedError(unexpected='b')
    >>> (flag("arg").many() >> done()).parse_args("--arg", "--arg", return_dict=False)
    [('arg', True), ('arg', True)]
    >>> (flag("arg").many() >> done()).parse_args("--arg", "--arg", "x")
    UnexpectedError(unexpected='x')
    """

    def f(cs: Sequence[str]) -> Result[Parse[Sequence[B]]]:
        if cs:
            c, *_ = cs
            return Result(UnexpectedError(c))
        return Result(NonemptyList(Parse(parsed=Sequence([]), unparsed=cs)))

    return Parser(f)


def equals(s: str) -> Parser[Sequence[KeyValue[str]]]:
    return sat_item(
        predicate=lambda _s: _s == s,
        on_fail=lambda _s: UnequalError(s, _s),
        description=s,
    )


def flag(
    dest: str,
    short: bool = True,
    string: Optional[str] = None,
    default: Optional[bool] = None,
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
        parser = equals(s) >= (
            lambda _: Parser[Sequence[KeyValue[bool]]].key_values(**{dest: not default})
        )
        return parser.parse(cs)

    parser = Parser(partial(f, s=_string))
    if default is not None:
        parser = parser | parser.key_values(**{dest: default})
    if short:
        parser2 = flag(dest, short=False, string=f"-{dest[0]}", default=default)
        parser = parser | parser2
    return parser


def item(
    name: str,
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
        return Result(MissingError(name))

    return Parser(f)


def nonpositional(*parsers: "Parser[Sequence[B]]") -> "Parser[Sequence[B]]":
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
        return Parser[Sequence[B]].empty()

    def get_alternatives():
        for i, head in enumerate(parsers):
            tail = [p for j, p in enumerate(parsers) if j != i]
            yield head >> nonpositional(*tail)

    return reduce(lambda p1, p2: p1 | p2, get_alternatives())


def option(
    dest: str, flag: Optional[str] = None, default=None, short: bool = True
) -> Parser[Sequence[KeyValue[str]]]:
    """
    >>> option("value").parse_args("--value", "x")
    {'value': 'x'}
    >>> option("value").parse_args("--value")
    MissingError(missing='value')
    >>> option("value").parse_args()
    MissingError(missing='--value')
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

    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[str]]]]:
        if flag is None:
            _flag = f"--{dest}" if len(dest) > 1 else f"-{dest}"
        else:
            _flag = flag

        parser = equals(_flag) >= (lambda _: item(dest))
        return parser.parse(cs)

    parser = Parser(f)
    if default:
        parser = parser | parser.key_values(**{dest: default})
    if short:
        parser2 = option(dest=dest, short=False, flag=f"-{dest[0]}", default=None)
        parser = parser | parser2
    return parser


def sat(
    parser: Parser[A],
    predicate: Callable[[A], bool],
    on_fail: Callable[[A], ArgumentError],
) -> Parser[A]:
    def f(x: A) -> Result[A]:
        return Result(NonemptyList(x) if predicate(x) else on_fail(x))

    return apply(f, parser)


def sat_item(
    predicate: Callable[[str], bool],
    on_fail: Callable[[str], ArgumentError],
    description: str,
) -> Parser[Sequence[KeyValue[str]]]:
    def _predicate(parsed: Sequence[KeyValue[str]]) -> bool:
        [kv] = parsed
        return predicate(kv.value)

    def _on_fail(parsed: Sequence[KeyValue[str]]) -> ArgumentError:
        [kv] = parsed
        return on_fail(kv.value)

    return sat(item(description), _predicate, _on_fail)


def type_(
    f: Callable[[str], Any], parser: Parser[Sequence[KeyValue[str]]]
) -> Parser[Sequence[KeyValue[Any]]]:
    def g(
        kvs: Sequence[KeyValue[str]],
    ) -> Result[Sequence[KeyValue[Any]]]:
        head, *tail = kvs.get
        try:
            head = replace(head, value=f(head.value))
        except Exception as e:
            return Result(e)

        return Result(NonemptyList(Sequence([*tail, head])))

    return apply(g, parser)


@dataclass
class Args:
    """
    >>> @dataclass
    ... class MyArgs(Args):
    ...     t: bool = True
    ...     f: bool = False
    ...     i: int = 1
    ...     s: str = "a"
    >>> p = MyArgs()
    >>> MyArgs().parse_args("--no-t", "-f", "-i", "2", "-s", "b")
    {'t': False, 'f': True, 'i': 2, 's': 'b'}
    >>> MyArgs().parse_args("--no-t")
    {'t': False, 'f': False, 'i': 1, 's': 'a'}
    >>> @dataclass
    ... class MyArgs(Args):
    ...     b: bool = False
    >>> p = MyArgs().parser
    >>> p1 = p >> argument("a")
    >>> p1.parse_args("-b", "hello")
    {'b': True, 'a': 'hello'}
    """

    @property
    def parser(self) -> Parser[Sequence[KeyValue[Any]]]:
        def get_parsers() -> Generator[Parser, None, None]:
            field: Field
            for field in fields(self):
                if field.type == bool:
                    assert isinstance(
                        field.default, bool
                    ), f"If `field.type == bool`, `field.default` must be a bool, not '{field.default}'."
                    if field.default is True:
                        string = f"--no-{field.name}"
                    else:
                        string = None
                    yield flag(dest=field.name, string=string, default=field.default)
                else:
                    opt = option(dest=field.name, default=field.default)
                    try:
                        t = field.metadata["type"]
                    except (TypeError, KeyError):
                        t = field.type

                    yield type_(t, opt)

        return nonpositional(*get_parsers())

    def parse_args(self, *args):
        return (self.parser >> done()).parse_args(*args)
