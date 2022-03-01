from typing import Optional, Sequence

from monad_argparse.parser.error import ArgumentError
from monad_argparse.parser.key_value import KeyValue, KeyValues
from monad_argparse.parser.parse import Parse, Parsed
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result


class Item(Parser[KeyValues[str]]):
    def __init__(self, name: str, description: Optional[str] = None):
        def f(
            cs: Sequence[str],
        ) -> Result[Parse[KeyValues[str]]]:
            if cs:
                c, *cs = cs
                return Result(
                    Parse(parsed=Parsed(KeyValues([KeyValue(name, c)])), unparsed=cs)
                )
            return Result(ArgumentError(description=f"Missing: {description or name}"))

        super().__init__(f)
