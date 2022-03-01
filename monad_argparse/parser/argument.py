from monad_argparse.parser.item import Item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.sequence import Sequence


class Argument(Parser[Sequence[KeyValue[str]]]):
    """
    >>> Argument("name").parse_args("Alice")
    [('name', 'Alice')]
    >>> Argument("name").parse_args()
    ArgumentError(token=None, description='Missing: name')
    """

    def __init__(self, dest: str):
        super().__init__(lambda cs: Item(dest).parse(cs))
