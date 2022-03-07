import dataclasses
from dataclasses import Field, dataclass, fields
from typing import Any, Callable, Generator, Optional, Union

from monad_argparse.key_value import KeyValue
from monad_argparse.parser import Parser, done, flag, nonpositional, option, type_
from monad_argparse.sequence import Sequence


def field(
    metadata: Optional[dict] = None,
    type: Optional[Union[type, Callable[[str], Any]]] = None,
    help: Optional[str] = None,
    **kwargs,
) -> Field:
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

        return ArgsField(name=field.name, default=field.default, help=help_, type=type_)


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
    >>> MyArgs.parse_args("--no-t", "-f", "-i", "2", "-s", "b")
    {'t': False, 'f': True, 'i': 2, 's': 'b'}
    >>> MyArgs.parse_args("--no-t")
    {'t': False, 'f': False, 'i': 1, 's': 'a'}
    >>> @dataclass
    ... class MyArgs(Args):
    ...     b: bool = False
    >>> p = MyArgs.parser()
    >>> p1 = p >> argument("a")
    >>> p1.parse_args("-b", "hello")
    {'b': True, 'a': 'hello'}
    >>> @dataclass
    ... class MyArgs(Args):
    ...     n: int = field(default=0, help="a number to increment", type=lambda x: 1 + int(x))
    >>> MyArgs.parse_args("-n", "1")
    {'n': 2}
    >>> Parser._exit = lambda _: None  # Need to mock _exit for doctests
    >>> MyArgs.parse_args()
    n: a number to increment
    The following arguments are required: -n
    """

    @classmethod
    def parser(cls) -> Parser[Sequence[KeyValue[Any]]]:
        def get_parsers() -> Generator[Parser, None, None]:
            field: Field
            for field in fields(cls):
                args_field = ArgsField.parse(field)
                if args_field.type == bool:
                    assert isinstance(
                        args_field.default, bool
                    ), f"If `field.type == bool`, `field.default` must be a bool, not '{field.default}'."
                    if args_field.default is True:
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
