import abc

from typing import Type

from do import Monad


class MonadZero(Monad):
    @classmethod
    @abc.abstractmethod
    def zero(cls):
        raise NotImplementedError


class MonadPlus(MonadZero):
    @classmethod
    @abc.abstractmethod
    def __add__(cls, a, b):
        raise NotImplementedError


class Parser(MonadPlus):
    def __init__(self, f):
        self.f = f

    def parse(self, cs: str):
        y = self.f(cs)
        assert isinstance(y, list)
        for a, b in y:
            assert isinstance(b, list)
            for c in b:
                assert isinstance(c, str)
        return y

    @classmethod
    def bind(cls, p, f):
        """
        :type p: Parser
        :type f: Callable[str, List[Tuple[Any, str]]]
        """

        def g(cs):
            for (a, _cs) in p.parse(cs):
                yield from f(a).parse(_cs)

        def h(cs):
            return list(g(cs))

        return Parser(h)

    @classmethod
    def ret(cls, x):
        return Parser(lambda cs: [(x, cs)])

    @classmethod
    def zero(cls):
        return Parser(lambda cs: [])

    @classmethod
    def __add__(cls, p, q):
        return Parser(lambda cs: p.parse(cs) + q.parse(cs))

    @classmethod
    def choice(cls, p, q):
        """
        :type p: Parser
        :type q: Parser
        """

        def f(cs):
            x = (p + q).parse(cs)
            return [x[0]] if x else []

        return Parser(f)


class Item(Parser):
    def __init__(self):
        def g(cs):
            try:
                c, *cs = cs
                return [(c, cs)]
            except ValueError:
                return []

        super().__init__(g)


class MaybeItem(Parser):
    def __init__(self):
        def g(cs):
            try:
                c, *cs = cs
                return [(c, cs)]
            except ValueError:
                return [(None, cs)]

        super().__init__(g)


class Sat(Parser):
    def __init__(self, p):
        def g():
            c = yield Item()
            if p(c):
                yield self.ret(c)
            else:
                yield self.zero()

        def f(cs):
            return Parser.do(g).parse(cs)

        super().__init__(f)


class Eq(Sat):
    def __init__(self, s):
        super().__init__(lambda s1: s == s1)


class Flag(Parser):
    def __init__(
        self, long: str, short: str = None, dest: str = None, value: bool = True
    ):
        def g():
            c = yield MaybeItem()
            k = dest or long
            yield self.ret({k: value if c in [f"-{short}", f"--{long}"] else not value})

        def f(cs):
            return Parser.do(g).parse(cs)

        super().__init__(f)


class Option(Parser):
    def __init__(self, long, type: Type = str, pre=None, short=None, dest=None):
        def g():
            c1 = yield Item()
            c2 = yield Item()
            if c1 in [f"-{short}", f"--{long}"]:
                key = dest or long
                try:
                    value = type(c2) if pre is None else pre(c2)
                    yield self.ret({key: value})
                except Exception:
                    yield self.zero()
            else:
                yield self.zero()

        def f(cs):
            return Parser.do(g).parse(cs)

        super().__init__(f)


class Argument(Parser):
    def __init__(self, dest):
        def g():
            c = yield Item()
            yield self.ret({dest: c})

        def f(cs):
            return Parser.do(g).parse(cs)

        super().__init__(f)


def parser():
    x1 = yield Argument("hello")
    # x2 = yield Option("world", type=int)
    x3 = yield Flag("verbose")


if __name__ == "__main__":
    p = Parser.do(parser)
    print(p.parse(["hello"]))
    print(p.parse(["hello", "--verbose"]))
    # print.parse(["hello", "--world", "1", "--verbose"]))
