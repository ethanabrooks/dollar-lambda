from monad_argparse.error import MissingError
from monad_argparse.key_value import KeyValue
from monad_argparse.parse import Parse
from monad_argparse.parser import Parser
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence


def item(
    name: str,
) -> Parser[Sequence[KeyValue[str]]]:
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

    return Parser(f)
