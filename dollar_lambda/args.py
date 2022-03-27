"""
Defines the `Args` dataclass and associated functions.
"""
import dataclasses
import typing
from dataclasses import Field, dataclass, fields
from typing import Any, Callable, Iterator, Optional

from dollar_lambda.key_value import KeyValue, KeyValueTuple
from dollar_lambda.parser import Parser, done, flag, nonpositional, option, type_
from dollar_lambda.sequence import Sequence


def field(
    help: Optional[str] = None,
    metadata: Optional[dict] = None,
    type: Optional["type | Callable[[str], Any]"] = None,
    **kwargs,
) -> Field:
    """
    This is a thin wrapper around [`dataclasses.field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field).

    Parameters
    ----------
    help : str
        An optional help string for the argument.
    metadata : str
        Identical to the `metadata` argument for [`dataclasses.field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field).
    type : Optional[type | Callable[[str], Any]]
        A function that takes a string and returns a value just like the `type` argument for
        [`ArgumentParser.add_argument`](https://docs.python.org/3/library/argparse.html#type).

    Returns
    -------
    A `dataclasses.Field` object that can be used in place of a default argument as
    described in the [`dataclasses.Field` documentation](https://docs.python.org/3/library/dataclasses.html#dataclasses.field).

    """
    if metadata is None:
        metadata = {}
    if type is not None:
        metadata.update(type=type)
    if help is not None:
        metadata.update(help=help)
    return dataclasses.field(metadata=metadata, **kwargs)


@dataclass
class _ArgsField:
    name: str
    default: Any = None
    help: Optional[str] = None
    string: Optional[str] = None
    type: Callable[[str], Any] = str

    @staticmethod
    def parse(field: Field) -> "_ArgsField":
        if "help" in field.metadata:
            help_ = field.metadata["help"]
        else:
            help_ = None
        if "string" in field.metadata:
            string = field.metadata["string"]
        else:
            string = None
        if "type" in field.metadata:
            type_ = field.metadata["type"]
        else:
            type_ = field.type
        default = field.default
        if field.default is dataclasses.MISSING:
            default = None

        return _ArgsField(
            name=field.name, default=default, help=help_, string=string, type=type_
        )

    @staticmethod
    def nonpositional(
        *fields: "_ArgsField", flip_bools: bool = True
    ) -> Parser[Sequence[KeyValue[Any]]]:
        def get_parsers() -> Iterator[Parser[Sequence[KeyValue[Any]]]]:
            for field in fields:
                if field.type == bool:
                    if field.string is None and field.default is True and flip_bools:
                        string: Optional[str] = f"--no-{field.name}"
                    else:
                        string = field.string
                    yield flag(
                        dest=field.name,
                        string=string,
                        default=field.default,
                        help=field.help,
                    )
                else:
                    opt = option(
                        dest=field.name,
                        default=field.default,
                        flag=field.string,
                        help=field.help,
                    )
                    yield type_(field.type, opt)

        return nonpositional(*get_parsers())


@dataclass
class Args:
    """
    `Args` is sugar for the `nonpositional` function and removes much of the boilerplate
    from defining parsers with many arguments.

    >>> @dataclass
    ... class MyArgs(Args):
    ...     verbose: bool
    ...     count: int
    >>> MyArgs.parse_args("--verbose", "--count", "1")
    {'verbose': True, 'count': 1}

    `MyArgs` will accept these arguments in any order:
    >>> MyArgs.parse_args("--count", "1", "--verbose")
    {'count': 1, 'verbose': True}

    Note that when the default value of an argument is `True`, `Args` will, by default
    add `--no-` to the front of the flag (while still assigning the value to the original key):
    >>> @dataclass
    ... class MyArgs(Args):
    ...     tests: bool = True
    >>> MyArgs.parse_args("--no-tests")
    {'tests': False}
    >>> MyArgs.parse_args()
    {'tests': True}

    To suppress this behavior, set `flip_bools=False`:
    >>> MyArgs.parse_args("--tests", flip_bools=False)
    {'tests': False}

    By using the `Args.parser()` method, `Args` can take advantage of all the same
    combinators as other parsers:

    >>> from dollar_lambda import argument
    >>> p = MyArgs.parser()
    >>> p1 = p >> argument("a")
    >>> p1.parse_args("--no-tests", "hello")
    {'tests': False, 'a': 'hello'}

    To supply other metadata, like `help` text and more complex `type` converters, use `field`:
    >>> @dataclass
    ... class MyArgs(Args):
    ...     n: int = field(default=0, help="a number to increment", type=lambda x: 1 + int(x))
    >>> MyArgs.parse_args("-n", "1")
    {'n': 2}
    >>> MyArgs.parse_args()
    {'n': 1}
    """

    @classmethod
    def parser(cls, flip_bools: bool = True) -> Parser[Sequence[KeyValue[Any]]]:
        """
        Returns a parser for the dataclass.
        Converts each field to a parser (`option` or `flag` depending on its type).
        Combines these parsers using `nonpositional`.

        Parameters
        ----------
        flip_bools: bool
             Whether to add `--no-<argument>` before arguments that default to `True`.

        Examples
        --------
        >>> @dataclass
        ... class MyArgs(Args):
        ...     tests: bool = True

        Note the leading `--no-`:
        >>> MyArgs.parse_args("--no-tests")
        {'tests': False}
        >>> MyArgs.parse_args()
        {'tests': True}

        To suppress this behavior, set `flip_bools=False`:
        >>> MyArgs.parse_args("--tests", flip_bools=False)
        {'tests': False}
        """
        return _ArgsField.nonpositional(
            *[_ArgsField.parse(field) for field in fields(cls)], flip_bools=flip_bools
        )

    @classmethod
    def parse_args(
        cls, *args, flip_bools: bool = True
    ) -> "typing.Sequence[KeyValueTuple] | typing.Dict[str, Any]":
        """
        Parses the arguments and returns a dictionary of the parsed values.
        """
        return (cls.parser(flip_bools=flip_bools) >> done()).parse_args(*args)
