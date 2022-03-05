from monad_argparse.parser.item import item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.sequence import Sequence


def argument(dest: str) -> Parser[Sequence[KeyValue[str]]]:
    """
    >>> argument("name").parse_args("Alice")
    [('name', 'Alice')]
    >>> argument("name").parse_args()
    MissingError(missing='name')
    """
    return item(dest)
