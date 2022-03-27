"""
Defines parsing functions and the `Parser` class that they instantiate.
"""
# pyright: reportGeneralTypeIssues=false
import operator
import os
import sys
import typing
from dataclasses import asdict, dataclass, replace
from functools import lru_cache, partial, reduce
from typing import Any, Callable, Dict, Generator, Generic, Optional, Type, TypeVar

from pytypeclass import Monad, MonadPlus
from pytypeclass.nonempty_list import NonemptyList

from dollar_lambda.error import (
    ArgumentError,
    HelpError,
    MissingError,
    UnequalError,
    UnexpectedError,
)
from dollar_lambda.key_value import KeyValue, KeyValueTuple
from dollar_lambda.result import Result
from dollar_lambda.sequence import Sequence

A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")
B = TypeVar("B")

global TESTING
TESTING = os.environ.get("DOLLAR_LAMBDA_TESTING", False)


@dataclass
class Parse(Generic[A_co]):
    """
    A `Parse` is the output of parsing.

    Parameters
    ----------
    parsed : A
        Component parsed by the parsed
    unparsed : Sequence[str]
        Component yet to be parsed
    """

    parsed: A_co
    unparsed: Sequence[str]


def empty() -> "Parser[Sequence]":
    """
    Always returns {}, no matter the input. Mostly useful for use in `nonpositional`.
    >>> empty().parse_args("any", "arguments")
    {}
    """
    return Parser[Sequence[A]].empty()


def binary_usage(a: Optional[str], op: str, b: Optional[str], add_brackets=True):
    """
    Utility for generating usage strings for binary operators.
    """
    no_nones = [x for x in (a, b) if x is not None]
    usage = op.join(no_nones)
    if len(no_nones) > 1 and add_brackets:
        usage = f"[{usage}]"
    return usage or None


__pdoc__ = {}


@dataclass
class Parser(MonadPlus[A_co]):
    """
    Main class powering the argument parser.
    """

    __pdoc__["Parser.__add__"] = True
    __pdoc__["Parser.__or__"] = True
    __pdoc__["Parser.__rshift__"] = True
    __pdoc__["Parser.__ge__"] = True

    f: Callable[[Sequence[str]], Result[Parse[A_co]]]
    usage: Optional[str]
    helps: Dict[str, str]

    def __add__(
        self: "Parser[Sequence[A]]", other: "Parser[Sequence[B]]"
    ) -> "Parser[Sequence[A | B]]":
        """
        Parse two arguments in either order.
        >>> p = flag("verbose") + flag("debug")
        >>> p.parse_args("--verbose", "--debug")
        {'verbose': True, 'debug': True}
        >>> p.parse_args("--debug", "--verbose")
        {'debug': True, 'verbose': True}
        >>> p.parse_args("--debug")
        usage: --verbose --debug
        Expected '--verbose'. Got '--debug'

        Note that if more than two arguments are chained together with `+`, some combinations will not parse:
        >>> p = flag("a") + flag("b") + flag("c")
        >>> p.parse_args("-c", "-a", "-b")   # this works
        {'c': True, 'a': True, 'b': True}
        >>> p.parse_args("-a", "-c", "-b")   # this doesn't
        usage: -a -b -c
        Expected '-b'. Got '-c'

        This makes more sense when one supplies the implicit parentheses:
        >>> p = (flag("a") + flag("b")) + flag("c")

        In order to chain together more than two arguments, use `nonpositional`:
        >>> p = nonpositional(flag("a"), flag("b"), flag("c"))
        >>> p.parse_args("-a", "-c", "-b")
        {'a': True, 'c': True, 'b': True}
        """
        p = (self >> other) | (other >> self)
        usage = binary_usage(self.usage, " ", other.usage, add_brackets=False)
        return replace(p, usage=usage)

    def __or__(  # type: ignore[override]
        self: "Parser[A_co]",
        other: "Parser[B]",
    ) -> "Parser[A_co | B]":
        """
        Tries apply the first parser. If it fails, tries the second. If that fails, the parser fails.

        >>> from dollar_lambda import argument, option, done, flag
        >>> p = option("option") | flag("verbose")
        >>> p.parse_args("--option", "x")
        {'option': 'x'}
        >>> p.parse_args("--verbose")
        {'verbose': True}

        Note that when both arguments are supplied, this will only parse the first:
        >>> p.parse_args("--verbose", "--option", "x")
        {'verbose': True}

        If you want this to fail, use `>>` (`Parser.__rshift__`) with `done()` or another parser:
        >>> (p >> done()).parse_args("--verbose", "--option", "x")
        usage: [--option OPTION | --verbose]
        Unrecognized argument: --option
        >>> p.parse_args("--option", "x")
        {'option': 'x'}
        """

        def f(cs: Sequence[str]) -> Result[Parse["A_co | B"]]:
            return self.parse(cs) | other.parse(cs)

        return Parser(
            f,
            usage=binary_usage(self.usage, " | ", other.usage),
            helps={**self.helps, **other.helps},
        )

    def __rshift__(
        self: "Parser[Sequence[A]]", p: "Parser[Sequence[B]]"
    ) -> "Parser[Sequence[A | B]]":
        """
        This applies parsers in sequence. If the first parser succeeds, the unparsed remainder
        gets handed off to the second parser. If either parser fails, the whole thing fails.

        >>> from dollar_lambda import argument, flag
        >>> p = argument("first") >> argument("second")
        >>> p.parse_args("a", "b")
        {'first': 'a', 'second': 'b'}
        >>> p.parse_args("a")
        usage: first second
        The following arguments are required: second
        >>> p.parse_args("b")
        usage: first second
        The following arguments are required: second
        """
        # def f(p1: Sequence[D]) -> Parser[Parse[Sequence[D | B]]]:
        #     def g(p2: Sequence[B]) -> Parser[Sequence[D | B]]:
        #         return Parser.return_(p1 + p2)

        #     return p >= g

        # return self >= f
        parser = self >= (lambda p1: (p >= (lambda p2: Parser.return_(p1 + p2))))
        return replace(
            parser,
            usage=binary_usage(self.usage, " ", p.usage, add_brackets=False),
            helps={**self.helps, **p.helps},
        )

    def __ge__(self, f: Callable[[A_co], Monad[B]]) -> "Parser[B]":
        return self.bind(f)

    def bind(self, f: Callable[[A_co], Monad[B]]) -> "Parser[B]":
        """
        Returns a new parser that

        1. applies `self`;
        2. if this succeeds, applies `f` to the parsed component of the result.

        `bind` is one of the functions that makes `Parser` a [`Monad`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monad.py#L16). But most users will
        avoid using it directly, preferring higher level combinators like `>>` (`Parser.__rshift__`),
        `|` (`Parser.__or__`) and `+` (`Parser.__add__`).

        Note that `>=` as a synonym for `bind` (as defined in [`pytypeclass`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monad.py#L26))
        and we typically prefer using the infix operator to the spelled out method.

        Let's start with our simplest parser, `argument`:
        >>> p1 = argument("some_dest")

        Now let's use the `equals` parser to write a function that takes the output of `p1` and fails unless
        the next argument is the same as the first:
        >>> def f(kvs: Sequence(KeyValue[str])) -> Parser[Sequence[KeyValue[str]]]:
        ...     [kv] = kvs
        ...     return equals(kv.value)

        >>> p = p1 >= f
        >>> p.parse_args("a", "a")
        {'a': 'a'}
        >>> p.parse_args("a", "b")
        Expected 'a'. Got 'b'
        """

        def h(parse: Parse[A_co]) -> Result[Parse[B]]:
            y = f(parse.parsed)
            assert isinstance(y, Parser), y
            return y.parse(parse.unparsed)

        def g(cs: Sequence[str]) -> Result[Parse[B]]:
            return self.parse(cs) >= h

        return Parser(g, usage=None, helps=self.helps)

    @classmethod
    def empty(cls: Type["Parser[Sequence[A]]"]) -> "Parser[Sequence[A]]":
        """
        Always returns {}, no matter the input. Mostly useful for use in `nonpositional`.
        >>> empty().parse_args("any", "arguments")
        {}
        """
        return cls.return_(Sequence([]))

    def handle_error(self, error: ArgumentError) -> None:
        def print_usage(usage: str):
            print("usage:", end="\n" if "\n" in usage else " ")
            if "\n" in usage:
                usage = "\n".join(["    " + u for u in usage.split("\n")])
            print(usage)
            if self.helps:
                for k, v in self.helps.items():
                    print(f"{k}: {v}")

        if isinstance(error, HelpError):
            print_usage(error.usage)
        else:
            if self.usage:
                print_usage(self.usage)
            if error.usage:
                print(error.usage)

    def many(self: "Parser[Sequence[A]]") -> "Parser[Sequence[A]]":
        """
        Applies `self` zero or more times (like `*` in regexes).

        >>> from dollar_lambda import argument, flag
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args(return_dict=False)
        []
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a", return_dict=False)
        [('as-many-as-you-like', 'a')]
        >>> p = argument("as-many-as-you-like").many()
        >>> p.parse_args("a", "b", return_dict=False)  # return_dict=False allows duplicate keys
        [('as-many-as-you-like', 'a'), ('as-many-as-you-like', 'b')]

        Note that if `self` contains `Parser.__or__`, the arguments can be
        heterogenous:
        >>> p = flag("verbose") | flag("quiet")
        >>> p = p.many()
        >>> p.parse_args("--verbose", "--quiet", return_dict=False) # mix --verbose and --quiet
        [('verbose', True), ('quiet', True)]
        """
        p = self.many1() | self.empty()
        return replace(p, usage=f"[{self.usage} ...]")

    def many1(self: "Parser[Sequence[A]]") -> "Parser[Sequence[A]]":
        """
        Applies `self` one or more times (like `+` in regexes).

        >>> from dollar_lambda import argument, flag
        >>> p = argument("1-or-more").many1()
        >>> p.parse_args("1")
        {'1-or-more': '1'}
        >>> p.parse_args("1", "2", return_dict=False)  # return_dict=False allows duplicate keys
        [('1-or-more', '1'), ('1-or-more', '2')]
        >>> p.parse_args()
        usage: 1-or-more [1-or-more ...]
        The following arguments are required: 1-or-more
        """

        def g() -> Generator["Parser[Sequence[A]]", Sequence[A], None]:
            # noinspection PyTypeChecker
            r1: Sequence[A] = yield self
            # noinspection PyTypeChecker
            r2: Sequence[A] = yield self.many()
            yield Parser[Sequence[A]].return_(r1 + r2)

        @lru_cache()
        def f(cs: tuple):
            y = Parser.do(g)
            assert isinstance(y, Parser), y
            return y.parse(Sequence(list(cs)))

        return Parser(
            lambda cs: f(tuple(cs)),
            usage=f"{self.usage} [{self.usage} ...]",
            helps=self.helps,
        )

    def optional(self: "Parser[Sequence[A]]") -> "Parser[Sequence[A]]":
        """
        Allows arguments to be optional:
        >>> p1 = flag("optional") >> done()
        >>> p = p1.optional()
        >>> p.parse_args("--optional")
        {'optional': True}
        >>> p.parse_args("--misspelled")  # succeeds with no output
        {}
        >>> p1.parse_args("--misspelled")
        usage: --optional
        Expected '--optional'. Got '--misspelled'
        """
        return self | self.empty()

    def parse(self, cs: Sequence[str]) -> Result[Parse[A_co]]:
        """
        Applies the parser to the input sequence `cs`.
        """
        return self.f(cs)

    def parse_args(
        self: "Parser[Sequence[KeyValue]]",
        *args: str,
        return_dict: bool = True,
        check_help: bool = True,
    ) -> "typing.Sequence[KeyValueTuple] | Dict[str, Any]":
        """
        The main way the user extracts parsed results from the parser.

        Parameters
        ----------
        args : str
            A sequence of strings to parse. If empty, defaults to `sys.argv[1:]`.
        return_dict : bool
            Returns a sequence of tuples instead of dictionary, thereby allowing duplicate keys.
            The tuples are `KeyValueTuple` namedtuples, with fields `key` and `value`.
        check_help : bool
            Before running the parser, checks if the input string is `--help` or `-h`.
            If it is, returns the usage message.

        Examples
        --------

        >>> argument("a").parse_args("-h")
        usage: a
        >>> argument("a").parse_args("--help")
        usage: a
        """
        _args = args if args or TESTING else sys.argv[1:]
        if check_help:
            return wrap_help(self).parse_args(
                *_args, return_dict=return_dict, check_help=False
            )
        result = self.parse(Sequence(list(_args))).get
        if isinstance(result, ArgumentError):
            self.handle_error(result)
            if TESTING:
                return  # type: ignore[return-value]
            else:
                exit()

        kvs = result.head.parsed
        if return_dict:
            return {kv.key: kv.value for kv in kvs}
        return [KeyValueTuple(**asdict(kv)) for kv in kvs]

    @classmethod
    def return_(cls, a: A_co) -> "Parser[A_co]":  # type: ignore[misc]
        # see https://github.com/python/mypy/issues/6178#issuecomment-1057111790
        """
        This method is required to make `Parser` a [`Monad`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monad.py#L16). It consumes none of the input
        and always returns `a` as the result. For the most part, the user will not use
        this method unless building custom parsers.

        >>> from dollar_lambda.key_value import KeyValue
        >>> Parser.return_(([KeyValue("some-key", "some-value")])).parse_args()
        {'some-key': 'some-value'}
        """

        def f(cs: Sequence[str]) -> Result[Parse[A_co]]:
            return Result.return_(Parse(a, cs))

        return Parser(f, usage=None, helps={})

    @classmethod
    def zero(cls, error: Optional[ArgumentError] = None) -> "Parser[A_co]":
        """
        This parser always fails. This method is necessary to make `Parser` a [`Monoid`](https://github.com/ethanabrooks/pytypeclass/blob/fe6813e69c1def160c77dea1752f4235820793df/pytypeclass/monoid.py#L13).

        Parameters
        ----------
        error : Optional[ArgumentError]
            Customize the error returned by `zero`.

        >>> Parser.zero().parse_args()
        zero
        >>> Parser.zero().parse_args("a")
        zero
        >>> Parser.zero(error=ArgumentError("This is a test.")).parse_args("a")
        This is a test.
        """
        return Parser(lambda _: Result.zero(error=error), usage=None, helps={})


def apply(
    f: Callable[[A], Result[B]], parser: Parser[A]  # type: ignore[misc]
) -> Parser[B]:
    """
    Takes the output of `parser` and applies `f` to it. Convert any errors that arise into `ArgumentError`.

    >>> p1 = flag("hello")
    >>> p1.parse_args("--hello", return_dict=False)
    [('hello', True)]

    This will double `p1`'s output:
    >>> p2 = apply(lambda kv: Result.return_(kv + kv), p1)
    >>> p2.parse_args("--hello", return_dict=False)
    [('hello', True), ('hello', True)]
    """

    def g(a: A) -> Parser[B]:
        try:
            y = f(a)
        except Exception as e:
            usage = f"An argument {a}: raised exception {e}"
            y = Result(ArgumentError(usage))
        return Parser(
            lambda cs: y >= (lambda parsed: Result.return_(Parse(parsed, cs))),
            usage=parser.usage,
            helps=parser.helps,
        )

    p = parser >= g
    return replace(p, usage=parser.usage, helps=parser.helps)


def apply_item(f: Callable[[str], B], description: str) -> Parser[B]:
    """
    A shortcut for `apply(f, item(description))`
    and spares `f` the trouble of outputting a `Result` object.

    >>> p1 = argument("foo")
    >>> p1.parse_args("bar", return_dict=False)
    [('foo', 'bar')]

    Here we use `f` to directly manipulate the binding generated by `item`:
    >>> p2 = apply_item(lambda bar: [KeyValue(bar + "e", bar + "f")], description="baz")
    >>> p2.parse_args("bar", return_dict=False)
    [('bare', 'barf')]
    """

    def g(parsed: Sequence[KeyValue[str]]) -> Result[B]:
        [kv] = parsed
        try:
            y = f(kv.value)
        except Exception as e:
            usage = f"argument {kv.value}: raised exception {e}"
            return Result(ArgumentError(usage))
        return Result.return_(y)

    return apply(g, item(description))


def argument(dest: str) -> Parser[Sequence[KeyValue[str]]]:
    """
    Parses a single word and binds it to `dest`.
    Useful for positional arguments.

    >>> argument("name").parse_args("Alice")
    {'name': 'Alice'}
    >>> argument("name").parse_args()
    usage: name
    The following arguments are required: name
    """
    return item(dest)


def defaults(**kwargs: Any) -> Parser[Sequence[KeyValue[Any]]]:
    """
    Useful for assigning default values to arguments.
    It ignore the input and always returns `kwargs` converted into `Sequence[KeyValue]`.
    `defaults` never fails.

    >>> defaults(a=1, b=2).parse_args()
    {'a': 1, 'b': 2}
    >>> (flag("fails") | defaults(fails="succeeds")).parse_args()
    {'fails': 'succeeds'}

    Here's a more complex example derived from the tutorial:
    >>> p = nonpositional(
    ...     (
    ...         flag("verbose") + defaults(quiet=False)  # either --verbose and default "quiet" to False
    ...         | flag("quiet") + defaults(verbose=False)  # or --quiet and default "verbose" to False
    ...     ),
    ...     option("x", type=int, help="the base"),
    ...     option("y", type=int, help="the exponent"),
    ... ) >> done()

    >>> p.parse_args("-x", "1", "-y", "2", "--verbose")
    {'x': 1, 'y': 2, 'verbose': True, 'quiet': False}
    """
    p = Parser.return_(Sequence([KeyValue(k, v) for k, v in kwargs.items()]))
    return replace(p, usage=None)


def done() -> Parser[Sequence[A]]:
    """
    `done` succeds on the end of input and fails on everything else.
    >>> done().parse_args()
    {}
    >>> done().parse_args("arg")
    Unrecognized argument: arg

    Without `done` the parser will not complain about leftover (unparsed) input:

    >>> flag("verbose").parse_args("--verbose", "--quiet")
    {'verbose': True}

    `--quiet` is not parsed here but this does not cause the parser to fail.
    If we want to prevent leftover inputs, we can use `done`:

    >>> (flag("verbose") >> done()).parse_args("--verbose", "--quiet")
    usage: --verbose
    Unrecognized argument: --quiet

    `done` is usually necessary to get `nonpositional` to behave in the way that you expect.
    See `nonpositional` API docs for details.
    """

    def f(cs: Sequence[str]) -> Result[Parse[Sequence[A]]]:
        if cs:
            c, *_ = cs
            return Result(
                UnexpectedError(unexpected=c, usage=f"Unrecognized argument: {c}")
            )
        return Result(NonemptyList(Parse(parsed=Sequence([]), unparsed=cs)))

    return Parser(f, usage=None, helps={})


def equals(s: str, peak=False) -> Parser[Sequence[KeyValue[str]]]:
    """
    Checks if the next word is `s`.

    >>> equals("hello").parse_args("hello")
    {'hello': 'hello'}
    >>> equals("hello").parse_args("goodbye")
    usage: hello
    Expected 'hello'. Got 'goodbye'

    Parameters
    ----------
    s: str
        The word to that input will be checked against for equality.
    peak : bool
        If `False`, then the parser will consume the word and return the remaining words as `unparsed`.
        If `True`, then the parser leaves the `unparsed` component unchanged.

    Examples
    --------

    >>> p = equals("hello") >> equals("goodbye")
    >>> p.parse_args("hello", "goodbye")
    {'hello': 'hello', 'goodbye': 'goodbye'}

    Look what happens when `peak=True`:
    >>> p = equals("hello", peak=True) >> equals("goodbye")
    >>> p.parse_args("hello", "goodbye")
    usage: hello goodbye
    Expected 'goodbye'. Got 'hello'

    The first parser didn't consume the word and so "hello" got passed on to `equals("goodbye")`.
    But this would work:
    >>> p = equals("hello", peak=True) >> equals("hello") >>equals("goodbye")
    >>> p.parse_args("hello", "goodbye")
    {'hello': 'hello', 'goodbye': 'goodbye'}
    """
    if peak:
        return sat_peak(
            predicate=lambda _s: _s == s,
            on_fail=lambda _s: UnequalError(
                left=s, right=_s, usage=f"Expected '{s}'. Got '{_s}'"
            ),
            name=s,
        )
    else:
        return sat_item(
            predicate=lambda _s: _s == s,
            on_fail=lambda _s: UnequalError(
                left=s, right=_s, usage=f"Expected '{s}'. Got '{_s}'"
            ),
            name=s,
        )


def flag(
    dest: str,
    default: Optional[bool] = None,
    help: Optional[str] = None,
    short: bool = True,
    string: Optional[str] = None,
) -> Parser[Sequence[KeyValue[bool]]]:
    """
    Binds a boolean value to a variable.

    >>> p = flag("verbose")
    >>> p.parse_args("--verbose")
    {'verbose': True}


    Parameters
    ----------
    dest : str
        The variable to which the value will be bound.

    default : Optional[bool]
        An optional default value.

    help : Optional[str]
        An optional help string.

    short : bool
        Whether to check for the short form of the flag, which
        uses a single dash and the first character of `dest`, e.g. `-f` for `foo`.

    string : Optional[str]
        A custom string to use for the flag. Defaults to `--{dest}`.

    Examples
    --------

    Here is an example using the `default` parameter:

    >>> p = flag("verbose", default=False)
    >>> p.parse_args()
    {'verbose': False}

    By default `flag` fails when it does not receive expected input:
    >>> p = flag("verbose")
    >>> p.parse_args()
    usage: --verbose
    The following arguments are required: --verbose

    Here is an example using the `help` parameter:

    >>> p = flag("verbose", help="Turn on verbose output.")
    >>> p.parse_args("-h")
    usage: --verbose
    verbose: Turn on verbose output.

    Here is an example using the `short` parameter:

    >>> flag("verbose", short=True).parse_args("-v")  # this is the default
    {'verbose': True}
    >>> flag("verbose", short=False).parse_args("-v")  # fails
    usage: --verbose
    Expected '--verbose'. Got '-v'

    Here is an example using the `string` parameter:

    >>> flag("value", string="v").parse_args("v")  # note that string does not have to start with -
    {'value': True}
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

    parser = Parser(partial(f, s=_string), usage=None, helps={})
    if short:
        short_string = f"-{dest[0]}"
        parser2 = flag(dest, short=False, string=short_string, default=default)
        parser = parser | parser2
    if default:
        help = f"{help + ' ' if help else ''}(default: {default})"
    helps = {dest: help} if help else {}
    parser = replace(parser, usage=_string, helps=helps)
    return parser if default is None else parser | defaults(**{dest: default})


def help_parser(usage: Optional[str], parsed: A) -> Parser[A]:
    def f(
        cs: Sequence[str],
    ) -> Result[Parse[A]]:
        result = (equals("--help", peak=True) | equals("-h", peak=True)).parse(cs)
        if isinstance(result.get, ArgumentError):
            return Result.return_(Parse(parsed=parsed, unparsed=cs))
        return Result(HelpError(usage=usage or "Usage not provided."))

    return Parser(f, usage=None, helps={})


def wrap_help(parser: Parser[A]) -> Parser[A]:
    """
    This checks for the `--help` or `-h` flag before applying `parser`.
    If either of the flags is present, returns the usage message for `parser`.

    >>> p = wrap_help(flag("help", help="Print this help message."))
    >>> p.parse_args("--help")
    usage: --help
    help: Print this help message.
    >>> p.parse_args("-h")
    usage: --help
    help: Print this help message.

    We can use `wrap_help` to print partial usage messages, e.g. for subcommands:
    >>> subcommand1 = equals("subcommand1") >> wrap_help(option("option1"))
    >>> subcommand2 = equals("subcommand2") >> wrap_help(option("option2"))
    >>> p = subcommand1 | subcommand2
    >>> p.parse_args("subcommand1", "-h")
    usage: --option1 OPTION1
    >>> p.parse_args("subcommand2", "-h")
    usage: --option2 OPTION2
    """
    _help_parser: Parser[Sequence[A]] = help_parser(parser.usage, Sequence([]))

    p = _help_parser >= (lambda _: parser)
    return replace(p, usage=parser.usage, helps=parser.helps)


def item(
    name: str,
    help_name: Optional[str] = None,
) -> Parser[Sequence[KeyValue[str]]]:
    """
    Parses a single word and binds it to `dest`.
    One of the lowest level building blocks for parsers.

    Parameters
    ----------
    help_name : Optional[str]
        Used for generating help text

    Examples
    --------

    >>> p = item("name", help_name="Your first name")
    >>> p.parse_args("Alice")
    {'name': 'Alice'}
    >>> p.parse_args()
    usage: name
    The following arguments are required: Your first name
    """

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
                usage=f"The following arguments are required: {help_name or name}",
            )
        )

    return Parser(f, usage=name, helps={})


def nonpositional(*parsers: "Parser[Sequence[A]]") -> "Parser[Sequence[A]]":
    """
    `nonpositional` takes a sequence of parsers as arguments and attempts all permutations of them,
    returning the first permutations that is successful:

    >>> p = nonpositional(flag("verbose"), flag("quiet"))
    >>> p.parse_args("--verbose", "--quiet")
    {'verbose': True, 'quiet': True}
    >>> p.parse_args("--quiet", "--verbose")  # reverse order also works
    {'quiet': True, 'verbose': True}

    If alternatives or defaults appear among the arguments to `nonpositional`, you will probably want
    to add `>>` followed by `done` (or another parser) after `nonpositional`. Otherwise,
    the parser will not behave as expected:

    >>> p = nonpositional(flag("verbose", default=False), flag("quiet"))
    >>> p.parse_args("--quiet", "--verbose")  # you expect this to set verbose to True, but it doesn't
    {'verbose': False, 'quiet': True}

    Why is happening? There are two permutions:

    - `flag("verbose", default=False) >> flag("quiet")` and
    - `flag("quiet") >> flag("verbose", default=False)`

    In our example, both permutations are actually succeeding. This first succeeds by falling
    back to the default, and leaving the last word of the input, `--verbose`, unparsed.
    Either interpretation is valid, and `nonpositional` returns one arbitrarily -- just not the one we expected.

    Now let's add `>> done()` to the end:
    >>> p = nonpositional(flag("verbose", default=False), flag("quiet")) >> done()

    This ensures that the first permutation will fail because the leftover `--verbose` input will
    cause the `done` parser to fail:
    >>> p.parse_args("--quiet", "--verbose")
    {'quiet': True, 'verbose': True}
    """
    if not parsers:
        return empty()

    def get_alternatives():
        for i, head in enumerate(parsers):
            tail = [p for j, p in enumerate(parsers) if j != i]
            yield head >> nonpositional(*tail)

    parser = reduce(operator.or_, get_alternatives())
    sep = " " if len(parsers) <= 3 else "\n"
    return replace(parser, usage=sep.join([p.usage or "" for p in parsers]))


def option(
    dest: str,
    flag: Optional[str] = None,
    default: Any = None,
    help: Optional[str] = None,
    short: bool = True,
    type: Callable[[str], Any] = str,
) -> Parser[Sequence[KeyValue[str]]]:
    """
    Parses two words, binding the second to the first.

    Parameters
    ----------
    dest : str
        The name of variable to bind to:

    flag : Optional[str]
        The flag to use for the option. If not provided, defaults to `--{dest}`.

    default : Optional[Any]
        The default value to bind on failure:

    help : Optional[str]
        The help message to display for the option:

    short : bool
        Whether to check for the short form of the flag, which
        uses a single dash and the first character of `dest`, e.g. `-c` for `count`.

    type : Callable[[str], Any]
        Use the `type` argument to convert the input to a different type:

    Examples
    --------

    >>> option("count").parse_args("--count", "1")
    {'count': '1'}

    In this example, you can see that the `flag` parameter allows the user to
    specify an arbitrary lead string, including one that doesn't start with a dash.

    >>> option("count", flag="ct").parse_args("ct", "1")
    {'count': '1'}

    This example demonstrates the use of the `default` parameter:

    >>> option("count", default=2).parse_args()
    {'count': 2}

    Here we specify a help-string using the `help` parameter:

    >>> option("count", help="The number we should count to").parse_args("-h")
    usage: --count COUNT
    count: The number we should count to

    This example demonstrates the difference between `short=True` and `short=False`:

    >>> option("count", short=True).parse_args("-c", "1")
    {'count': '1'}
    >>> option("count", short=False).parse_args("-c", "1")
    usage: --count COUNT
    Expected '--count'. Got '-c'

    As with [argparse](https://docs.python.org/3/library/argparse.html#argument-parsing),
    the `type` argument allows you to convert the input to a different type using a
    function that takes a single string argument:

    >>> option("x", type=int).parse_args("-x", "1")  # converts "1" to an int
    {'x': 1}
    >>> option("x", type=lambda x: int(x) + 1).parse_args("-x", "1")
    {'x': 2}
    """

    if flag is None:
        _flag = f"--{dest}" if len(dest) > 1 else f"-{dest}"
    else:
        _flag = flag

    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[str]]]]:
        parser = equals(_flag) >= (lambda _: item(dest, help_name=dest.upper()))
        return parser.parse(cs)

    parser = Parser(f, usage=None, helps={})
    if type is not str:
        parser = type_(type, parser)
    if short and len(dest) > 1:
        parser2 = option(dest=dest, short=False, flag=f"-{dest[0]}", default=None)
        parser = parser | parser2
    helps = {dest: help} if help else {}
    parser = replace(parser, usage=f"{_flag} {dest.upper()}", helps=helps)
    return parser if default is None else parser | defaults(**{dest: default})


def peak(
    name: str,
    description: Optional[str] = None,
) -> Parser[Sequence[KeyValue[str]]]:
    def f(
        cs: Sequence[str],
    ) -> Result[Parse[Sequence[KeyValue[str]]]]:
        if cs:
            head, *_ = cs
            return Result(
                NonemptyList(
                    Parse(
                        parsed=Sequence([KeyValue(name, head)]),
                        unparsed=Sequence(cs),
                    )
                )
            )
        return Result(
            MissingError(
                missing=name,
                usage=f"The following arguments are required: {description or name}",
            )
        )

    return Parser(f, usage=name, helps={})


def sat(
    parser: Parser[A],
    predicate: Callable[[A], bool],
    on_fail: Callable[[A], ArgumentError],
) -> Parser[A]:
    """
    Applies `parser`, applies a predicate to the result and fails if this returns false.

    >>> p = sat(
    ...     option("x", type=int).many(),
    ...     lambda kvs: sum([kv.value for kv in kvs]) > 0,
    ...     lambda x: ArgumentError(f"The values in {list(x)} must sum to more than 0."),
    ... )
    >>> p.parse_args("-x", "-1", "-x", "1")  # fails
    usage: [-x X ...]
    The values in [KeyValue(key='x', value=-1), KeyValue(key='x', value=1)] must sum to more than 0.

    >>> p.parse_args("-x", "-1", "-x", "2")  # succeeds
    {'x': 2}

    Parameters
    ----------
    parser : Parser[A]
        The parser to apply.
    predicate : Callable[[A], bool]
        The predicate to apply to the result of `parser`. `sat` fails if this predicate returns false.
    on_fail : Callable[[A], ArgumentError]
        A function producing an ArgumentError to return if the predicate fails.
        Takes the output of `parser` as an argument.
    """

    def f(x: A) -> Result[A]:
        return Result(NonemptyList(x) if predicate(x) else on_fail(x))

    return apply(f, parser)


def sat_item(
    predicate: Callable[[str], bool],
    on_fail: Callable[[str], ArgumentError],
    name: str,
) -> Parser[Sequence[KeyValue[str]]]:
    """
    A wrapper around `sat` that uses `item` to parse the argument and just applies `predicate` to the value output by `item`.

    >>> p = sat_item(lambda x: len(x) == 1, lambda x: ArgumentError(f"'{x}' must have exactly one character."), "x")
    >>> p.parse_args("a")  # succeeds
    {'x': 'a'}
    >>> p.parse_args("aa")  # fails
    usage: x
    'aa' must have exactly one character.

    Parameters
    ----------
    predicate : Callable[[A], bool]
        The predicate to apply to the result of `item`. `sat` fails if this predicate returns false.
    on_fail : Callable[[A], ArgumentError]
        A function producing an ArgumentError to return if the predicate fails.
        Takes the output of `item` as an argument.
    name: str
        The value to bind the result to.
    """

    def _predicate(parsed: Sequence[KeyValue[str]]) -> bool:
        [kv] = parsed
        return predicate(kv.value)

    def _on_fail(parsed: Sequence[KeyValue[str]]) -> ArgumentError:
        [kv] = parsed
        return on_fail(kv.value)

    return sat(item(name), _predicate, _on_fail)


def sat_peak(
    predicate: Callable[[str], bool],
    on_fail: Callable[[str], ArgumentError],
    name: str,
) -> Parser[Sequence[KeyValue[str]]]:
    def _predicate(parsed: Sequence[KeyValue[str]]) -> bool:
        [kv] = parsed
        return predicate(kv.value)

    def _on_fail(parsed: Sequence[KeyValue[str]]) -> ArgumentError:
        [kv] = parsed
        return on_fail(kv.value)

    return sat(peak(name), _predicate, _on_fail)


def type_(
    f: Callable[[str], Any], parser: Parser[Sequence[KeyValue[str]]]
) -> Parser[Sequence[KeyValue[Any]]]:
    """
    A wrapper around `apply` that simply applies `f` to the value of the most recently parsed input.
    >>> p1 = option("x") >> option("y")
    >>> p = type_(int, p1)
    >>> p.parse_args("-x", "1", "-y", "2")  # converts "1" but not "2"
    {'y': '2', 'x': 1}
    """

    def g(
        kvs: Sequence[KeyValue[str]],
    ) -> Result[Sequence[KeyValue[Any]]]:
        head, *tail = kvs.get
        try:
            y = f(head.value)
        except Exception as e:
            usage = f"argument {head.value}: raised exception {e}"
            return Result(ArgumentError(usage))
        head = replace(head, value=y)
        return Result.return_(Sequence([*tail, head]))

    p = apply(g, parser)
    return replace(p, usage=parser.usage, helps=parser.helps)
