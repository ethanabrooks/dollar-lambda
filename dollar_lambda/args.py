"""
`Args` is sugar for the `nonpositional` function and removes much of the boilerplate
from defining parsers with many arguments.
"""
import dataclasses
from dataclasses import Field, dataclass, fields
from typing import Any, Callable, Generator, Optional, Union

from dollar_lambda.key_value import KeyValue
from dollar_lambda.parser import Parser, done, flag, nonpositional, option, type_
from dollar_lambda.sequence import Sequence


def field(
    metadata: Optional[dict] = None,
    type: Optional[Union[type, Callable[[str], Any]]] = None,
    help: Optional[str] = None,
    **kwargs,
) -> Field:
    """
    This is a thin wrapper around [`dataclasses.field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field).

    Parameters
    ----------
    metadata : str
        Identical to the `metadata` argument for [`dataclasses.field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.field).
    type : Optional[Union[type, Callable[[str], Any]]]
        A function that takes a string and returns a value just like the `type` argument for
        [`ArgumentParser.add_argument`](https://docs.python.org/3/library/argparse.html#type).
    help : str
        An optional help string for the argument.

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
class ArgsField:
    name: str
    default: Any = None
    help: Optional[str] = None
    type: Callable[[str], Any] = str

    @staticmethod
    def parse(field: Field) -> "ArgsField":
        if "type" in field.metadata:
            type_ = field.metadata["type"]
        else:
            type_ = field.type
        if "help" in field.metadata:
            help_ = field.metadata["help"]
        else:
            help_ = None
        default = field.default
        if field.default is dataclasses.MISSING:
            default = None

        return ArgsField(name=field.name, default=default, help=help_, type=type_)


@dataclass
class Args:
    """
    `Args` is sugar for the `nonpositional` function and removes much of the boilerplate
    from defining parsers with many arguments.

    >>> @dataclass
    ... class MyArgs(Args):
    ...     t: bool = False
    ...     f: bool = True
    ...     i: int = 1
    ...     s: str = "a"
    >>> p = MyArgs()

    By using the `Args.parser()` method, `Args` can take advantage of all the same
    combinators as other parsers:

    >>> from dollar_lambda import argument
    >>> p = MyArgs.parser()
    >>> p1 = p >> argument("a")
    >>> p1.parse_args("-t", "hello")
    {'t': True, 'f': True, 'i': 1, 's': 'a', 'a': 'hello'}

    Note that when the default value of an argument is `True`, `Args` will, by default
    add `--no-` to the front of the flag (while still assigning the value to the original key):
    >>> MyArgs.parse_args("--no-f")
    {'t': False, 'f': False, 'i': 1, 's': 'a'}

    To suppress this behavior, set `flip_bools=False`:
    >>> MyArgs.parser(flip_bools=False).parse_args("--no-t", "-f", "-i", "2", "-s", "b")
    {'t': False, 'f': True, 'i': 1, 's': 'a'}

    To supply other metadata, like `help` text and more complex `type` converters, use `field`:
    >>> @dataclass
    ... class MyArgs(Args):
    ...     n: int = field(default=0, help="a number to increment", type=lambda x: 1 + int(x))
    >>> MyArgs.parse_args("-n", "1")
    {'n': 2}
    >>> MyArgs.parse_args()
    usage: -n N
    n: a number to increment
    The following arguments are required: -n
    """

    @classmethod
    def parser(cls, flip_bools: bool = True) -> Parser[Sequence[KeyValue[Any]]]:
        def get_parsers() -> Generator[Parser, None, None]:
            field: Field
            for field in fields(cls):
                args_field = ArgsField.parse(field)
                if args_field.type == bool:
                    if args_field.default is True and flip_bools:
                        string = f"--no-{field.name}"
                    else:
                        string = None
                    yield flag(
                        dest=args_field.name,
                        string=string,
                        default=args_field.default,
                        help=args_field.help,
                    )
                else:
                    opt = option(
                        dest=args_field.name,
                        default=args_field.default,
                        help=args_field.help,
                    )
                    yield type_(args_field.type, opt)

        return nonpositional(*get_parsers())

    @classmethod
    def parse_args(cls, *args):
        return (cls.parser() >> done()).parse_args(*args)
