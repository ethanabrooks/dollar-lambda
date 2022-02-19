from monad_argparse import Argument, Flag, Option, Parser

if __name__ == "__main__":
    # print(Option.do(options))
    # print(Result.do(results))
    # print(List.do(lists))
    # IO().do(io)

    p = Flag("verbose", "v") | Flag("quiet", "q") | Option("num", "n", convert=int)
    print(
        Parser.do(lambda: p.interleave(Argument("a"), Argument("b"))).parse_args(
            ["first", "--verbose", "--quiet", "second", "--quiet"]
        )
    )

    print(Argument("name").parse_args(["Ethan"]))

    from monad_argparse import Flag

    print(Flag("verbose").parse_args(["--verbose"]))

    from monad_argparse import Option

    print(Option("value").parse_args(["--value", "x"]))

    print(Option("value").parse_args(["--value"]))

    p = Flag("verbose") | Option("value")
    print(p.parse_args(["--verbose"]))

    print(p.parse_args(["--value", "x"]))

    p = Argument("first") >> Argument("second")
    print(p.parse_args(["a", "b"]))

    from monad_argparse import Parser

    def g():
        x1 = yield Argument("first")
        x2 = yield Argument("second")
        yield Parser.ret([x1, x2])

    print(Parser.do(g).parse_args(["a", "b"]))

    p = Argument("many").many()
    print(p.parse_args(["a", "b"]))

    p = (Flag("verbose") | Flag("quiet")).many()
    print(p.parse_args(["--verbose", "--quiet"]))

    print(p.parse_args(["--quiet", "--verbose"]))

    print(p.parse_args(["--quiet"]))

    print(p.parse_args(["--quiet", "--quiet", "--quiet"]))

    p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
    p = p1 >> Argument("a")
    print(p.parse_args(["--verbose", "value"]))

    p2 = p1.many()
    p = p2 >> Argument("a")
    print(p.parse_args(["--verbose", "value"]))

    def g():
        xs = yield p2
        x = yield Argument("a")
        yield Parser.ret(xs + [x])

    print(Parser.do(g).parse_args(["--verbose", "--quiet", "value"]))

    def g():
        xs1 = yield p2
        x1 = yield Argument("first")
        xs2 = yield p2
        x2 = yield Argument("second")
        xs3 = yield p2
        yield Parser.ret(xs1 + [x1] + xs2 + [x2] + xs3)

    print(Parser.do(g).parse_args(["a", "--verbose", "b", "--quiet"]))

    def g():
        return (Flag("verbose") | Flag("quiet") | Flag("yes")).interleave(
            Argument("first"), Argument("second")
        )

    print(Parser.do(g).parse_args(["a", "--verbose", "b", "--quiet"]))

    print(
        Parser.build(
            Flag("verbose") | Flag("quiet") | Flag("yes"),
            Argument("first"),
            Argument("second"),
        ).parse_args(["a", "--verbose", "b", "--quiet"])
    )
