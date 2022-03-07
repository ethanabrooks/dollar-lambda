"""
Contains all the functions for generating parsers tailored for parsing command line arguments.
"""
# pyright: reportGeneralTypeIssues=false
import operator
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
from monad_argparse.parser import Parser, empty
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence

A = TypeVar("A", bound=MonadPlus)
B = TypeVar("B")
C = TypeVar("C", covariant=True, bound=MonadPlus)
D = TypeVar("D", bound=MonadPlus)


def apply(f: Callable[[D], Result[C]], parser: Parser[D]) -> Parser[C]:
    def g(d: D) -> Parser[C]:
        usage = f"invalid value for {f.__name__}: {d}"
        usage = f"argument {parser.usage}: {usage}"
        return Parser(
            lambda unparsed: f(d)
            >= (lambda parsed: Result.return_(Parse(parsed, unparsed))),
            usage=usage,
        )

    return parser >= g


def apply_item(f: Callable[[str], C], description: str) -> Parser[C]:
    def g(parsed: Sequence[KeyValue[str]]) -> Result[C]:
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


def done() -> Parser[Sequence[B]]:
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

    def f(cs: Sequence[str]) -> Result[Parse[Sequence[B]]]:
        if cs:
            c, *_ = cs
            return Result(
                UnexpectedError(unexpected=c, usage=f"Unrecognized argument: {c}")
            )
        return Result(NonemptyList(Parse(parsed=Sequence([]), unparsed=cs)))

    return Parser(f, usage=None)


def equals(s: str) -> Parser[Sequence[KeyValue[str]]]:
    return sat_item(
        predicate=lambda _s: _s == s,
        on_fail=lambda _s: UnequalError(
            left=s, right=_s, usage=f"Expected '{s}'. Got '{_s}'"
        ),
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
        parser = equals(s) >= (lambda _: defaults(**{dest: not default}))
        return parser.parse(cs)

    parser = Parser(partial(f, s=_string), usage=None)
    if default is not None:
        parser = parser | defaults(**{dest: default})
    if short:
        short_string = f"-{dest[0]}"
        parser2 = flag(dest, short=False, string=short_string, default=default)
        parser = parser | parser2
    return replace(parser, usage=_string)


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

    return Parser(f, usage=name)


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
    short: bool = True,
    type: Callable[[str], Any] = str,
) -> Parser[Sequence[KeyValue[str]]]:
    """
    >>> option("value").parse_args("--value", "x")
    {'value': 'x'}
    >>> Parser._exit = lambda _: None  # Need to mock _exit for doctests
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

    parser = Parser(f, usage=None)
    if default:
        parser = parser | defaults(**{dest: default})
    if short and len(dest) > 1:
        parser2 = option(dest=dest, short=False, flag=f"-{dest[0]}", default=None)
        parser = parser | parser2
    if type is not str:
        parser = type_(type, parser)
    return replace(parser, usage=f"{_flag} {dest.upper()}")


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
        except ArgumentError as e:
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
