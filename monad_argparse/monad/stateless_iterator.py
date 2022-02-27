from typing import Callable, Generator, Generic, List, Optional, Tuple, TypeVar

Yields = TypeVar("Yields", contravariant=True)
Sends = TypeVar("Sends", contravariant=True)


class StatelessIterator(Generic[Yields, Sends]):
    def __init__(
        self,
        generator: Callable[[], Generator[Yields, Sends, None]],
        inputs: Optional[List[Sends]] = None,
    ):
        self.generator = generator
        self.inputs = inputs or []

    def send(self, x: Sends) -> Tuple[Yields, "StatelessIterator[Yields, Sends]"]:
        it = self.generator()
        inputs = self.inputs
        next(it)
        for inp in inputs:
            it.send(inp)
        y: Yields = it.send(x)
        it2 = StatelessIterator(self.generator, inputs + [x])
        return y, it2

    def __next__(self) -> Tuple[Yields, "StatelessIterator[Yields, Sends]"]:
        it = self.generator()
        assert not self.inputs
        y: Yields = next(it)
        it2: StatelessIterator[Yields, Sends] = StatelessIterator(self.generator, [])
        return y, it2
