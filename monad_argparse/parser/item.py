from typing import Optional, Sequence

from monad_argparse.parser.error import ArgumentError
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse, Parsed
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Ok, Result


class Item(Parser[Sequence[KeyValue[str]]]):
    def __init__(self, name: str, description: Optional[str] = None):
        def f(
            cs: Sequence[str],
        ) -> Result[Parse[Sequence[KeyValue[str]]]]:
            if cs:
                c, *cs = cs
                return Result(
                    Ok(Parse(parsed=Parsed([KeyValue(name, c)]), unparsed=cs))
                )
            return Result(ArgumentError(description=f"Missing: {description or name}"))

        super().__init__(f)
