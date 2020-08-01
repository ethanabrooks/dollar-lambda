import abc

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
        return self.f(cs)

    @classmethod
    def bind(cls, p, f):
        """
        :type p: Parser
        :type f: Callable[str, List[Tuple[Any, str]]]
        """

        def g(cs):
            for (a, _cs) in p.parse(cs):
                yield from f(a).parse(_cs)

        return Parser(lambda cs: list(g(cs)))

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


class Sat(Parser):
    def __init__(self, p):
        def g():
            c = yield Item()
            if p(c):
                yield self.ret(c)
            else:
                yield self.zero()

        def f(cs):
            return Parser.do(g()).parse(cs)

        super().__init__(f)


class Eq(Sat):
    def __init__(self, s):
        super().__init__(lambda s1: s == s1)


def parser():
    p = Eq("--hello")
    res1 = yield p
    import ipdb; ipdb.set_trace()
    return True


if __name__ == "__main__":
    p = Parser.do(parser())
    print(p.parse(["--hello"]))
    print(p.parse("--hell"))
