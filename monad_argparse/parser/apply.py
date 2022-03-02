from typing import Callable, Generic, TypeVar

from monad_argparse.monad.monoid import MonadPlus
from monad_argparse.parser.item import Item
from monad_argparse.parser.key_value import KeyValue
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence

D = TypeVar("D", covariant=True, bound=MonadPlus)
E = TypeVar("E", covariant=True, bound=MonadPlus)
F = TypeVar("F", bound=MonadPlus)


class Apply(Parser[E], Generic[F, E]):
    def __init__(
        self,
        f: Callable[[F], Result[E]],
        parser: Parser[F],
    ):
        def h(parsed: F) -> Parser[E]:
            y = f(parsed)
            if isinstance(y.get, Exception):
                return self.zero(y.get)
            return Parser[E].return_(y.get)

        def g(
            cs: Sequence[str],
        ) -> Result[Parse[E]]:
            p: Parser[E] = parser >= h
            return p.parse(cs)

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
                y = f(kv.get_value())
            except Exception as e:
                return Result(e)
            return Result(y)

        super().__init__(g, Item(description))
