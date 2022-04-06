"""
Defines the :py:class:`Args <dollar_lambda.args.Args>` dataclass and associated functions.
"""
from __future__ import annotations

import dataclasses
import typing
from dataclasses import Field, dataclass, fields
from typing import Any, Callable, Iterator, Optional, Union

from dollar_lambda.data_structures import KeyValue, Output, Sequence
from dollar_lambda.parsers import Parser, defaults, flag, nonpositional, option


def field(
    help: Optional[str] = None,
    metadata: Optional[dict] = None,
    parser: Optional[Parser[Output]] = None,
    **kwargs,
) -> Field:
    """
    This is a thin wrapper around :external:py:func:`dataclasses.field`.

    Parameters
    ----------

    help : str
        An optional help string for the argument.

    metadata : str
        Identical to the `metadata` argument for :external:py:func:`dataclasses.field`.

    type : Optional[type | Callable[[str], Any]]
        A function that takes a string and returns a value just like the ``type`` argument for
        :external:py:meth:`argparse.ArgumentParser.add_argument`.

    Returns
    -------

    A :external:py:class:`dataclasses.Field` object that can be used in place of a default argument as described in the :external:py:class:`dataclasses.Field` documentation.

    """
    if metadata is None:
        metadata = {}
    if parser is not None:
        metadata.update(parser=parser)
    if help is not None:
        metadata.update(help=help)
    return dataclasses.field(metadata=metadata, **kwargs)


@dataclass
class _ArgsField:
    name: str
    default: Any = None
    help: Optional[str] = None
    type: Callable[[str], Any] = str

    @staticmethod
    def parse(field: Field) -> Union["_ArgsField", Parser[Output]]:
        if "help" in field.metadata:
            help_ = field.metadata["help"]
        else:
            help_ = None
        default = field.default
        if field.default is dataclasses.MISSING:
            default = None
        if "parser" in field.metadata:
            parser = field.metadata["parser"]
            assert isinstance(parser, Parser), parser
            if default is None:
                return parser
            else:
                return parser | defaults(**{field.name: default})

        return _ArgsField(name=field.name, default=default, help=help_, type=field.type)

    @staticmethod
    def parser(
        *fields: Union["_ArgsField", Parser[Output]],
        flip_bools: bool,
        repeated: Optional[Parser[Output]],
    ) -> Parser[Output]:
        def get_parsers() -> Iterator[Parser[Output]]:
            for field in fields:
                if isinstance(field, Parser):
                    yield field
                    continue
                string: Optional[str] = None
                if field.type == bool:
                    if field.default is True and flip_bools:
                        string = f"--no-{field.name}"
                    yield flag(
                        dest=field.name,
                        string=string,
                        default=field.default,
                        help=field.help,
                    )
                else:
                    yield option(
                        dest=field.name,
                        default=field.default,
                        flag=string,
                        help=field.help,
                        type=field.type,
                    )

        return nonpositional(*get_parsers(), repeated=repeated)


@dataclass
class Args:
    """
    :py:class:`Args` is sugar for the :py:func:`nonpositional <dollar_lambda.parsers.nonpositional>` function and
    removes much of the boilerplate from defining parsers with many arguments.

    >>> from dataclasses import dataclass
    >>> from dollar_lambda import Args
    >>> @dataclass
    ... class MyArgs(Args):
    ...     verbose: bool
    ...     count: int
    >>> MyArgs.parse_args("--verbose", "--count", "1")
    {'verbose': True, 'count': 1}

    ``MyArgs`` will accept these arguments in any order:

    >>> MyArgs.parse_args("--count", "1", "--verbose")
    {'count': 1, 'verbose': True}

    Note that when the default value of an argument is ``True``, :py:class:`Args` will, by default
    add ``--no-`` to the front of the flag (while still assigning the value to the original key):

    >>> @dataclass
    ... class MyArgs(Args):
    ...     tests: bool = True
    >>> MyArgs.parse_args("--no-tests")
    {'tests': False}
    >>> MyArgs.parse_args()
    {'tests': True}

    To suppress this behavior, set ``flip_bools=False``:

    >>> MyArgs.parse_args("--tests", flip_bools=False)
    {'tests': False}

    By using the :py:meth:`Args.parser` method, :py:class:`Args` can take advantage of all the same
    combinators as other parsers:

    >>> from dollar_lambda import argument
    >>> p = MyArgs.parser()
    >>> p1 = p >> argument("a")
    >>> p1.parse_args("--no-tests", "hello")
    {'tests': False, 'a': 'hello'}

    To supply other metadata, like ``help`` text or custom parsers, use :py:func:`field`:

    >>> from dollar_lambda import field, option
    >>> @dataclass
    ... class MyArgs(Args):
    ...     x: int = field(default=0, help="a number")
    ...     y: int = field(
    ...         default=1,
    ...         parser=option("y", type=lambda s: int(s) + 1, help="a number to increment"),
    ...     )
    >>> MyArgs.parse_args("-h")
    usage: -x X -y Y
    x: a number
    y: a number to increment

    This supplies defaults for ``y`` when omitted:

    >>> MyArgs.parse_args("-x", "10")
    {'x': 10, 'y': 1}

    It also applies the custom type to ``y`` when ``"-y"`` is given

    >>> MyArgs.parse_args()
    {'x': 0, 'y': 1}
    """

    @classmethod
    def parser(
        cls,
        flip_bools: bool = True,
        repeated: Optional[Parser[Output]] = None,
    ) -> Parser[Output]:
        """
        Returns a parser for the dataclass.
        Converts each field to a parser (:py:func:`option <dollar_lambda.parsers.option>` or
        :py:func:`flag <dollar_lambda.parsers.flag>` depending on its type). Combines these parsers using
        :py:func:`nonpositional <dollar_lambda.parsers.nonpositional>`.

        Parameters
        ----------

        flip_bools: bool
             Whether to add ``--no-<argument>`` before arguments that default to ``True``.

        Examples
        --------

        >>> @dataclass
        ... class MyArgs(Args):
        ...     tests: bool = True

        Note the leading ``--no-``:

        >>> MyArgs.parse_args("--no-tests")
        {'tests': False}
        >>> MyArgs.parse_args()
        {'tests': True}

        To suppress this behavior, set ``flip_bools=False``:

        >>> MyArgs.parse_args("--tests", flip_bools=False)
        {'tests': False}
        """

        def get_fields():
            types = typing.get_type_hints(cls)  # see https://peps.python.org/pep-0563/
            for field in fields(cls):
                field.type = types.get(field.name, str)
                yield _ArgsField.parse(field)

        return _ArgsField.parser(
            *get_fields(), flip_bools=flip_bools, repeated=repeated
        )

    @classmethod
    def parse_args(
        cls,
        *args,
        flip_bools: bool = True,
        repeated: Optional[Parser[Output]] = None,
    ) -> Optional[typing.Dict[str, Any]]:
        """
        Parses the arguments and returns a dictionary of the parsed values.
        """
        return (
            cls.parser(flip_bools=flip_bools, repeated=repeated)
            >> Parser[Output[Sequence[KeyValue[Any]]]].done()
        ).parse_args(*args)
