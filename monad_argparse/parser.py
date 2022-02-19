import abc
from typing import Any, Callable, Generator, List, Optional, Tuple, Union

from monad_argparse.do import MA, MB, Monad
from monad_argparse.stateless_iterator import A, StatelessIterator


class MonadZero(Monad[A, MA, MB]):
    @classmethod
    @abc.abstractmethod
    def zero(cls):
        raise NotImplementedError


class MonadPlus(MonadZero[A, MA, MB]):
    @abc.abstractmethod
    def __add__(self, other: "MonadPlus"):
        raise NotImplementedError


StrList = List[str]


class Parser(MonadPlus[Any, "Parser", "Parser"]):
    def __init__(self, f: Callable[[StrList], List[Tuple[A, StrList]]]):
        self.f = f

    def __add__(  # type: ignore[override]  # pyre-ignore[14]
        self,
        other: "Parser",
    ) -> "Parser":
        return Parser(lambda cs: self.parse(cs) + other.parse(cs))

    def __or__(self, p: "Parser") -> "Parser":
        def f(cs: StrList) -> List[Tuple[Any, StrList]]:
            x: List[Tuple[Any, StrList]] = (self + p).parse(cs)
            return [x[0]] if x else []

        return Parser(f)

    def __rshift__(self, p: "Parser") -> "Parser":
        def g() -> Generator[Any, Tuple[Any, StatelessIterator], None]:
            x1 = yield self
            x2 = yield p
            yield self.ret([x1] + [x2])

        return Parser.do(g)

    @classmethod
    def bind(cls, x: "Parser", f: Callable[[A], "Parser"]):
        def g(cs: StrList) -> Generator[Tuple[A, StrList], None, None]:
            a: A
            for (a, _cs) in x.parse(cs):
                f1: Parser = f(a)
                yield from f1.parse(_cs)

        def h(cs: StrList) -> List[Tuple[A, StrList]]:
            return list(g(cs))

        return Parser(h)

    @classmethod
    def build(cls, non_positional, *positional):
        return Parser.do(lambda: non_positional.interleave(*positional))

    def interleave(
        self, *positional: "Parser"
    ) -> Generator[
        "Parser", Union[List[Tuple[Any, StrList]], Tuple[Any, StrList]], None
    ]:
        xs = yield self.many()
        assert isinstance(xs, list)
        try:
            head, *tail = positional
            x = yield head
            assert isinstance(x, tuple)
            l1 = xs + [x]

            def generator() -> Generator["Parser", Tuple[Any, Any], None]:
                return self.interleave(*tail)

            l2 = yield Parser.do(generator)
        except ValueError:
            l2 = yield self.many()
            l1 = xs
            assert isinstance(l1, list)
        assert isinstance(l2, list)
        yield Parser.ret(l1 + l2)

    def many(self) -> "Parser":
        return self.many1() | (self.ret([]))

    def many1(self):
        def g() -> Generator[
            "Parser", Union[Tuple[Any, StrList], List[Tuple[Any, StrList]]], None
        ]:
            a = yield self
            assert isinstance(a, tuple)
            aa = yield self.many()
            assert isinstance(aa, list)
            yield self.ret([a] + aa)

        def f(cs):
            return Parser.do(g).parse(cs)

        return Parser(f)

    def parse(self, cs: StrList) -> List[Tuple[Any, StrList]]:
        return self.f(cs)

    def parse_args(self, args: StrList) -> List[Any]:
        parsed: List[Tuple[List[Any], StrList]] = self.parse(args)
        try:
            (a, _), *_ = parsed
        except ValueError:
            return []
        return a

    @classmethod
    def ret(cls, x: A) -> "Parser":
        def f(cs: StrList) -> List[Tuple[A, StrList]]:
            return [(x, cs)]

        return Parser(f)

    @classmethod
    def zero(cls) -> "Parser":
        empty: List[Tuple[Any, StrList]] = []
        return Parser(lambda cs: empty)


class Item(Parser):
    def __init__(self):
        def g(cs: StrList) -> List[Tuple[str, StrList]]:
            try:
                c, *cs = cs
                return [(c, cs)]
            except ValueError:
                return []

        super().__init__(g)


class Sat(Parser):
    def __init__(self, predicate: Callable[[Any], bool]):
        def g() -> Generator[Parser, Tuple[Any, StatelessIterator], None]:
            c = yield Item()
            if predicate(c):
                yield self.ret(c)
            else:
                yield self.zero()

        def f(cs: StrList) -> List[Tuple[Any, StrList]]:
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
        self,
        long: str,
        short: Optional[str] = None,
        dest: Optional[str] = None,
        value: bool = True,
    ):
        def predicate(x: str) -> bool:
            return x in [f"-{short}", f"--{long}"]

        def g() -> Generator[Parser, Tuple[Any, StatelessIterator], None]:
            yield Sat(predicate)
            yield self.ret(((dest or long), value))

        super().__init__(g)


class Option(DoParser):
    def __init__(
        self,
        long: str,
        short: Optional[str] = None,
        convert: Optional[Callable[[str], Any]] = None,
        dest: Optional[str] = None,
    ):
        def predicate(x: str):
            return x in [f"-{short}", f"--{long}"]

        def g() -> Generator[Parser, str, None]:
            yield Sat(predicate)
            c2 = yield Item()
            key = dest or long
            try:
                value = c2 if convert is None else convert(c2)
                yield self.ret((key, value))
            except Exception:
                yield self.zero()

        super().__init__(g)


class Argument(DoParser):
    def __init__(self, dest):
        def g() -> Generator[Parser, str, None]:
            c = yield Item()
            yield self.ret((dest, c))

        super().__init__(g)


#
def finite_parser():
    p = Flag("verbose", "v") | Flag("quiet", "q") | Option("num", "n", convert=int)
    x0 = yield p.many()
    x1 = yield Argument("a")
    x2 = yield p.many()
    x3 = yield Argument("b")
    x4 = yield p.many()
    yield Parser.ret(x0 + [x1] + x2 + [x3] + x4)


if __name__ == "__main__":
    p = Flag("verbose", "v") | Flag("quiet", "q") | Option("num", "n", convert=int)
    print(
        Parser.do(lambda: p.interleave(Argument("a"), Argument("b"))).parse_args(
            ["first", "--verbose", "--quiet", "second", "--quiet"]
        )
    )

    # print(p.parse(sys.argv[1:]))
