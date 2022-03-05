from monad_argparse.parser.error import UnexpectedError
from monad_argparse.parser.parse import Parse
from monad_argparse.parser.parser import A, Parser
from monad_argparse.parser.result import Result
from monad_argparse.parser.sequence import Sequence


def done() -> Parser[Sequence[A]]:
    """
    >>> from monad_argparse import argument, flag
    >>> done().parse_args()
    []
    >>> done().parse_args("arg")
    UnexpectedError(unexpected='arg')
    >>> (argument("arg") >> done()).parse_args("a")
    [('arg', 'a')]
    >>> (argument("arg") >> done()).parse_args("a", "b")
    UnexpectedError(unexpected='b')
    >>> (flag("arg").many() >> done()).parse_args("--arg", "--arg")
    [('arg', True), ('arg', True)]
    >>> (flag("arg").many() >> done()).parse_args("--arg", "--arg", "x")
    UnexpectedError(unexpected='x')
    """

    def f(cs: Sequence[str]) -> Result[Parse[Sequence[A]]]:
        if cs:
            c, *_ = cs
            return Result(UnexpectedError(c))
        return Result(Parse(parsed=Sequence([]), unparsed=cs))

    return Parser(f)
