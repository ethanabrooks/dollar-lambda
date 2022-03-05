from monad_argparse.error import UnexpectedError
from monad_argparse.parse import Parse
from monad_argparse.parser import A, Parser
from monad_argparse.result import Result
from monad_argparse.sequence import Sequence


def done() -> Parser[Sequence[A]]:
    """
    >>> from monad_argparse.argument import argument
    >>> from monad_argparse.flag import flag
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
