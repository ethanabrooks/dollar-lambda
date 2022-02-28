from typing import Callable, Generator, Generic, Sequence, TypeVar, Union

from monad_argparse.monad.nonempty_list import NonemptyList
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
        def h() -> Generator[
            Parser[Union[D, E]],
            Parsed[D],
            None,
        ]:
            # noinspection PyTypeChecker
            parsed: Parsed[D] = yield parser
            y = f(parsed.get)
            if isinstance(y.get, Exception):
                yield self.zero(y.get)
            elif isinstance(y.get, Ok):
                yield Parser[E].return_(Parsed(y.get.get))

        def g(
            cs: Sequence[str],
        ) -> Result[NonemptyList[Parse[E]]]:
            do = Parser[E].do(h)  # type: ignore[arg-type]
            # The suppression of the type-checker is unfortunately unavoidable here because our definition of `do` requires
            # the type to remain the same throughout the do block as a consequence of the way that python types generators.
            return do.parse(cs)

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
