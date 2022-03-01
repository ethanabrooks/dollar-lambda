from typing import Callable, Generic, Sequence, TypeVar

from monad_argparse.parser.item import Item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse, Parsed
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Ok, Result

D = TypeVar("D", covariant=True)
E = TypeVar("E", covariant=True)


class Apply(Parser[E], Generic[D, E]):
    def __init__(
        self,
        f: Callable[[D], Result[E]],
        parser: Parser[D],
    ):
        def h(parsed: Parsed[D]) -> Parser[E]:
            y = f(parsed.get)
            if isinstance(y.get, Exception):
                return self.zero(y.get)
            return Parser[E].return_(Parsed(y.get.get))

        def g(
            cs: Sequence[str],
        ) -> Result[Parse[E]]:
            return (parser >= h).parse(cs)

        super().__init__(g)


class ApplyItem(Apply[Sequence[KeyValue[str]], E]):
    def __init__(
        self,
        f: Callable[[str], E],
        description: str,
    ):
        def g(parsed: Sequence[KeyValue[str]]) -> Result[E]:
            [kv] = parsed
            try:
                y = f(kv.value)
            except Exception as e:
                return Result(e)
            return Result(Ok(y))

        super().__init__(g, Item(description))
