#! /usr/bin/env python
from monad_argparse import monad, parser

if __name__ == "__main__":
    import doctest

    fail_count, _ = doctest.testmod(monad)
    assert fail_count == 0
    fail_count, _ = doctest.testmod(parser)
    assert fail_count == 0
