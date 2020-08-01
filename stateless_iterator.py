class StatelessIterator:
    def __init__(self, generator, inputs=None):
        self.generator = generator
        self.inputs = inputs or []

    def send(self, x):
        it = self.generator()
        inputs = self.inputs
        for inp in inputs:
            it.send(inp)
        y = it.send(x)
        it2 = StatelessIterator(self.generator, inputs + [x])
        return y, it2

    def __next__(self):
        return self.send(None)
