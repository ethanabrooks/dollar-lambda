from typing import Callable, Generator, Generic, List, Optional, Tuple, TypeVar

A = TypeVar("A", contravariant=True)
B = TypeVar("B", contravariant=True)


class StatelessIterator(Generic[A, B]):
    def __init__(
        self,
        generator: Callable[[], Generator[A, B, None]],
        inputs: Optional[List[B]] = None,
    ):
        self.generator = generator
        self.inputs = inputs or []

    def send(self, x: B) -> Tuple[A, "StatelessIterator[A, B]"]:
        it = self.generator()
        inputs = self.inputs
        next(it)
        for inp in inputs:
            it.send(inp)
        y: A = it.send(x)
        it2 = StatelessIterator(self.generator, inputs + [x])
        return y, it2

    def __next__(self) -> Tuple[A, "StatelessIterator[A, B]"]:
        it = self.generator()
        assert not self.inputs
        y: A = next(it)
        it2: StatelessIterator[A, B] = StatelessIterator(self.generator, [])
        return y, it2
