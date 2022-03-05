from typing import Optional

from monad_argparse.parser.error import MissingError
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence


class Item(Parser[Sequence[KeyValue[str]]]):
    def __init__(self, name: str, description: Optional[str] = None):
        def f(
            cs: Sequence[str],
        ) -> Result[Parse[Sequence[KeyValue[str]]]]:
            if cs:
                head, *tail = cs
                return Result(
                    Parse(
                        parsed=Sequence([KeyValue(name, head)]),
                        unparsed=Sequence(tail),
                    )
                )
            return Result(MissingError(name))

        super().__init__(f)
