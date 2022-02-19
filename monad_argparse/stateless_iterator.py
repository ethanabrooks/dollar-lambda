from typing import Callable, Generator, Generic, List, Optional, TypeVar

A = TypeVar("A", contravariant=True)
B = TypeVar("B", covariant=True)


class StatelessIterator(Generic[A, B]):
    def __init__(
        self,
        generator: Callable[[], Generator[A, B, None]],
        inputs: Optional[List[B]] = None,
    ):
        self.generator = generator
        self.inputs = inputs or []

    def send(self, x):  # TODO: caching?
        it = self.generator()
        inputs = self.inputs
        for inp in inputs:
            it.send(inp)
        y = it.send(x)
        it2 = StatelessIterator(self.generator, inputs + [x])
        return y, it2

    def __next__(self):
        return self.send(None)
