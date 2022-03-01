from monad_argparse.parser.error import ArgumentError
from monad_argparse.parser.parse import Parse, Parsed
from monad_argparse.parser.parser import A, Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence


class Empty(Parser[Sequence[A]]):
    """
    >>> from monad_argparse import Argument, Empty, Flag
    >>> Empty().parse_args()
    []
    >>> Empty().parse_args("arg")
    ArgumentError(token='arg', description='Unexpected argument: arg')
    >>> (Argument("arg") >> Empty()).parse_args("a")
    [('arg', 'a')]
    >>> (Argument("arg") >> Empty()).parse_args("a", "b")
    ArgumentError(token='b', description='Unexpected argument: b')
    >>> (Flag("arg").many() >> Empty()).parse_args("--arg", "--arg")
    [('arg', True), ('arg', True)]
    >>> (Flag("arg").many() >> Empty()).parse_args("--arg", "--arg", "x")
    ArgumentError(token='x', description='Unexpected argument: x')
    """

    def __init__(self):
        def f(cs: Sequence[str]) -> Result[Parse[Sequence[A]]]:
            if cs:
                c, *_ = cs
                return Result(
                    ArgumentError(token=c, description=f"Unexpected argument: {c}")
                )
            return Result(Parse(parsed=Parsed(Sequence([])), unparsed=cs))

        super().__init__(f)
