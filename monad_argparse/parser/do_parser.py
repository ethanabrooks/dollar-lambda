from typing import Callable, Generator, Sequence

from monad_argparse.monad.nonempty_list import NonemptyList
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse, Parsed
from monad_argparse.parser.parser import A, Parser
from monad_argparse.parser.result import Result


class DoParser(Parser[Sequence[KeyValue[A]]]):
    def __init__(
        self,
        g: Callable[
            [],
            Generator[
                Parser[Sequence[KeyValue[A]]], Parsed[Sequence[KeyValue[A]]], None
            ],
        ],
    ):
        def f(cs: Sequence[str]) -> Result[NonemptyList[Parse[Sequence[KeyValue[A]]]]]:
            return Parser.do(g).parse(cs)

        super().__init__(f)
