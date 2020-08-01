import abc
import sys

from typepy import List

from do import Monad


class MonadZero(Monad):
    @classmethod
    @abc.abstractmethod
    def zero(cls):
        raise NotImplementedError


class MonadPlus(MonadZero):
    @abc.abstractmethod
    def __add__(self, other):
        raise NotImplementedError


class Parser(MonadPlus):
    def __init__(self, f):
        self.f = f

    def parse(self, cs: str):
        return self.f(cs)

    @classmethod
    def bind(cls, p, f):
        """
        :type p: Parser
        :type f: Callable[str, List[Tuple[Any, str]]]
        """

        def g(cs):
            for (a, _cs) in p.parse(cs):
                f1 = f(a)
                yield from f1.parse(_cs)

        def h(cs):
            return list(g(cs))

        return Parser(h)

    @classmethod
    def ret(cls, x):
        return Parser(lambda cs: [(x, cs)])

    @classmethod
    def zero(cls):
        return Parser(lambda cs: [])

    def many(self):
        return self.many1() | (self.ret([]))

    def many1(self):
        def g():
            x1 = yield self
            xs = yield self.many()
            yield self.ret([x1] + xs)

        def f(cs):
            return Parser.do(g).parse(cs)

        return Parser(f)

    def __add__(self, p):
        return Parser(lambda cs: self.parse(cs) + p.parse(cs))

    def __or__(self, p):
        """
        :type p: Parser
        """

        def f(cs):
            x = (self + p).parse(cs)
            return [x[0]] if x else []

        return Parser(f)

    def __rshift__(self, p):
        def g():
            x1 = yield self
            x2 = yield p
            yield self.ret([x1] + [x2])

        return Parser.do(g)


class Item(Parser):
    def __init__(self):
        def g(cs):
            try:
                c, *cs = cs
                return [(c, cs)]
            except ValueError:
                return []

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


class DoParser(Parser):
    def __init__(self, g):
        def f(cs):
            return Parser.do(g).parse(cs)

        super().__init__(f)


class Flag(DoParser):
    def __init__(
        self, long: str, short: str = None, dest: str = None, value: bool = True
    ):
        def pred(x):
            return x in [f"-{short}", f"--{long}"]

        def g():
            yield Sat(pred)
            yield self.ret(((dest or long), value))

        super().__init__(g)


class Option(DoParser):
    def __init__(self, long, short=None, pre: callable = None, dest=None):
        def pred(x):
            return x in [f"-{short}", f"--{long}"]

        def g():
            yield Item()
            c2 = yield Sat(pred)
            key = dest or long
            try:
                value = c2 if pre is None else pre(c2)
                yield self.ret((key, value))
            except Exception:
                yield self.zero()

        super().__init__(g)


class Argument(DoParser):
    def __init__(self, dest):
        def g():
            c = yield Item()
            yield self.ret((dest, c))

        super().__init__(g)


def build_parser(non_positional: Parser, *positional: Parser):
    xs = yield non_positional.many()
    try:
        head, *tail = positional
        x = yield head
        l1 = xs + [x]
        l2 = yield Parser.do(lambda: build_parser(non_positional, *tail))
    except ValueError:
        l2 = yield non_positional.many()
        l1 = xs
    yield Parser.ret(l1 + l2)


def finite_parser():
    p = Flag("verbose", "v") | Flag("quiet", "q") | Option("num", "n", pre=int)
    x0 = yield p.many()
    x1 = yield Argument("a")
    x2 = yield p.many()
    x3 = yield Argument("b")
    x4 = yield p.many()
    yield Parser.ret(x0 + [x1] + x2 + [x3] + x4)


if __name__ == "__main__":
    p = Flag("verbose", "v") | Flag("quiet", "q") | Option("num", "n", pre=int)
    p = Parser.do(lambda: build_parser(p, Argument("a"), Argument("b")))
    print(p.parse(sys.argv[1:]))
