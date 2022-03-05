from monad_argparse.parser.error import UnexpectedError
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import A, Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence


class Done(Parser[Sequence[A]]):
    """
    >>> from monad_argparse import Argument, Flag
    >>> Done().parse_args()
    []
    >>> Done().parse_args("arg")
    UnexpectedError(unexpected='arg')
    >>> (Argument("arg") >> Done()).parse_args("a")
    [('arg', 'a')]
    >>> (Argument("arg") >> Done()).parse_args("a", "b")
    UnexpectedError(unexpected='b')
    >>> (Flag("arg").many() >> Done()).parse_args("--arg", "--arg")
    [('arg', True), ('arg', True)]
    >>> (Flag("arg").many() >> Done()).parse_args("--arg", "--arg", "x")
    UnexpectedError(unexpected='x')
    """

    def __init__(self):
        def f(cs: Sequence[str]) -> Result[Parse[Sequence[A]]]:
            if cs:
                c, *_ = cs
                return Result(UnexpectedError(c))
            return Result(Parse(parsed=Sequence([]), unparsed=cs))

        super().__init__(f)
