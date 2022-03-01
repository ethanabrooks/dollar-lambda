from typing import Optional

from monad_argparse.parser.error import ArgumentError
from monad_argparse.parser.key_value import KeyValue, KeyValues
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence


class Item(Parser[KeyValues[str]]):
    def __init__(self, name: str, description: Optional[str] = None):
        def f(
            cs: Sequence[str],
        ) -> Result[Parse[KeyValues[str]]]:
            if cs:
                head, *tail = cs
                return Result(
                    Parse(
                        parsed=KeyValues(Sequence([KeyValue(name, head)])),
                        unparsed=Sequence(tail),
                    )
                )
            return Result(
                ArgumentError(token=None, description=f"Missing: {name}")
                # MissingError(
                #     Parse(
                #         default=KeyValues(Sequence([KeyValue(name, None)])),
                #         parsed=KeyValues(Sequence([])),
                #         unparsed=cs,
                #     )
                # )
            )

        super().__init__(f)
