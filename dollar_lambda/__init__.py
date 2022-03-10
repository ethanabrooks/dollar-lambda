"""
This package provides an alternative to [`argparse`](https://docs.python.org/3/library/argparse.html) based on functional first principles.
This means that this package can handle many kinds of argument-parsing patterns that are either very awkward, difficult, or impossible with `argparse`.

# Tutorial
Here is an example developed in the `argparse` tutorial:

```
import argparse
parser = argparse.ArgumentParser(description="calculate X to the power of Y")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-v", "--verbose", action="store_true")
group.add_argument("-q", "--quiet", action="store_true")
parser.add_argument("x", type=int, help="the base")
parser.add_argument("y", type=int, help="the exponent")
args = parser.parse_args()
```

Here is the equivalent in this package:

>>> p = nonpositional(
...     (flag("verbose") | flag("quiet")),
...     option("x", type=int, help="the base"),
...     option("y", type=int, help="the exponent"),
... ) >> done()
...
>>> def main(x, y, verbose=False, quiet=False):
...     return dict(x=x, y=y, verbose=verbose, quiet=quiet)

It succeeds for either `--verbose` or `--quiet`:
>>> main(**p.parse_args("-x", "1", "-y", "2", "--verbose"))
{'x': 1, 'y': 2, 'verbose': True, 'quiet': False}
>>> main(**p.parse_args("-x", "1", "-y", "2", "--quiet"))
{'x': 1, 'y': 2, 'verbose': False, 'quiet': True}

But fails for both:
>>> p.parse_args("-x", "1", "-y", "2", "--verbose", "--quiet")
usage: [--verbose | --quiet] -x X -y Y
x: the base
y: the exponent
Unrecognized argument: --quiet

And fails for neither:
>>> p.parse_args("-x", "1", "-y", "2")
usage: [--verbose | --quiet] -x X -y Y
x: the base
y: the exponent
Expected '--verbose'. Got '-x'

Let's walk through this step by step. First, let's learn what `flag`, `option` and `done` do.

## High-Level Parsers
These three functions create high-level parsers. `flag` binds a boolean value to a variable
whereas `option` binds an arbitrary value to a variable. `done` does not bind any values to variables,
but causes the parser to fail in some cases.

### `flag`
>>> p = flag("verbose")
>>> p.parse_args("--verbose")
{'verbose': True}

By default `flag` fails when it does not receive expected input:
>>> p.parse_args()
usage: --verbose
The following arguments are required: --verbose

Alternately, you can set a default value:
>>> flag("verbose", default=False).parse_args()
{'verbose': False}

### `option`
`option` is similar but takes an argument:
By default, `option` expects a single `-` for single-character variable names (as in `-x`),
as opposed to `--` for longer names (as in `--xenophon`):

>>> option("x").parse_args("-x", "1")
{'x': '1'}
>>> option("xenophon").parse_args("--xenophon", "1")
{'xenophon': '1'}

Use the `type` argument to convert the input to a different type:
>>> option("x", type=int).parse_args("-x", "1")  # converts "1" to an int
{'x': 1}

### `done`
Without `done` the parser will not complain about leftover (unparsed) input:

>>> flag("verbose").parse_args("--verbose", "--quiet")
{'verbose': True}

`--quiet` is not parsed here but this does not cause the parser to fail.
If we want to prevent leftover inputs, we can use `done`:

>>> (flag("verbose") >> done()).parse_args("--verbose", "--quiet")
usage: --verbose
Unrecognized argument: --quiet

`done` is usually necessary to get `nonpositional` to behave in the way that you expect,
but more on that later.

## Parser Combinators
Parser combinators are functions that combine multiple parsers into new, more complex parsers.
Our example uses three such functions: `nonpositional`, `|` or `Parser.__or__`,
and `>>` or `Parser.__rshift__`.

### `Parser.__or__`

The `|` operator is used for alternatives. Specifically, it will try the first parser,
and if that fails, try the second:

>>> p = flag("verbose") | flag("quiet")
>>> p.parse_args("--quiet") # flag("verbose") fails
{'quiet': True}
>>> p.parse_args("--verbose") # flag("verbose") succeeds
{'verbose': True}

By default one of the two flags would be required to prevent failure:
>>> p.parse_args() # neither flag is provided so this fails
usage: [--verbose | --quiet]
The following arguments are required: --verbose

To permit the omission of both flags, use `empty` or supply a default value:

>>> (flag("verbose") | flag("quiet") | empty()).parse_args() # flags fail, but empty() succeeds
{}
>>> (flag("verbose") | flag("quiet", default=False)).parse_args() # flag("verbose") fails but flag("quiet", default=False) succeeds
{'quiet': False}

This is just sugar for

>>> (flag("verbose") | flag("quiet") | defaults(quiet=False)).parse_args() # flag("verbose") fails but flag("quiet", default=False) succeeds
{'quiet': False}

### `Parser.__rshift__`

The `>>` operator is used for sequential composition. It applies the first parser and then
hands the output of the first parser to the second parser. If either parser fails, the composition fails:

>>> p = flag("verbose") >> done()
>>> p.parse_args("--verbose")
{'verbose': True}
>>> p.parse_args("--something-else")  # first parser will fail
usage: --verbose
Expected '--verbose'. Got '--something-else'
>>> p.parse_args("--verbose", "--something-else")  # second parser will fail
usage: --verbose
Unrecognized argument: --something-else

### `nonpositional`
This function takes a sequence of parsers as arguments and attempts all permutations of them,
returning the first permutations that is successful:

>>> p = nonpositional(flag("verbose"), flag("quiet"))
>>> p.parse_args("--verbose", "--quiet")
{'verbose': True, 'quiet': True}
>>> p.parse_args("--quiet", "--verbose")  # reverse order also works
{'quiet': True, 'verbose': True}

For just two parsers you can use `+`, or `Parser.__add__`, instead of `nonpositional`:
>>> p = flag("verbose") + flag("quiet")
>>> p.parse_args("--verbose", "--quiet")
{'verbose': True, 'quiet': True}
>>> p.parse_args("--quiet", "--verbose")  # reverse order also works
{'quiet': True, 'verbose': True}

This will not cover all permutations for more than two parsers:
>>> p = flag("verbose") + flag("quiet") + option("x")
>>> p.parse_args("--verbose", "-x", "1", "--quiet")
usage: --verbose --quiet -x X
Expected '--quiet'. Got '-x'

To see why note the implicit parentheses:
>>> p = (flag("verbose") + flag("quiet")) + option("x")

In order to cover the case where `-x` comes between `--verbose` and `--quiet`,
use `nonpositional`:
>>> p = nonpositional(flag("verbose"), flag("quiet"), option("x"))
>>> p.parse_args("--verbose", "-x", "1", "--quiet")  # works
{'verbose': True, 'x': '1', 'quiet': True}

If alternatives or defaults appear among the arguments to `nonpositional`, you will probably want
to add `>>` followed by `done` (or another parser) after `nonpositional`. Otherwise,
the parser will not behave as expected:

>>> p = nonpositional(flag("verbose", default=False), flag("quiet"))
>>> p.parse_args("--quiet", "--verbose")  # you expect this to bind `True` to `verbose`, but it doesn't
{'verbose': False, 'quiet': True}

Why is happening? There are two permutions:

- `flag("verbose", default=False) >> flag("quiet")` and
- `flag("quiet") >> flag("verbose", default=False)`

In our example, both permutations are actually succeeding. This first succeeds by falling
back to the default, and leaving the last word of the input, `--verbose`, unparsed.
Either interpretation is valid, and `nonpositional` returns one arbitrarily -- just not the one we expected.

Now let's add `>> done()` to the end:
>>> p = nonpositional(flag("verbose", default=False), flag("quiet")) >> done()

This ensures that the first permutation will fail because the leftover `--verbose` input will
cause the `done` parser to fail:
>>> p.parse_args("--quiet", "--verbose")
{'quiet': True, 'verbose': True}

## Putting it all together
Let's recall the original example:

>>> p = nonpositional(
...     (flag("verbose") | flag("quiet")),
...     option("x", type=int, help="the base"),
...     option("y", type=int, help="the exponent"),
... ) >> done()
...
>>> def main(x, y, verbose=False, quiet=False):
...     return dict(x=x, y=y, verbose=verbose, quiet=quiet)

As we've seen `flag("verbose") | flag("quiet")` succeeds on either `--verbose` or `--quiet`
(but one or the other is required).

`option("x", type=int)` succeeds on `-x X`, where `X` is
some integer, binding that integer to the variable `"x"`. Similarly for `option("y", type=int)`.

`nonpositional` takes the three parsers:

- `flag("verbose") | flag("quiet")`
- `option("x", type=int)`
- `option("y", type=int)`

and applies them in every order, until some order succeeds.
Finally `done()` ensures that only one of these parser permutations will succeed, preventing ambiguity.

## Alternative syntax
There are a few alternative ways to express the functionality that we've seen so far.
We will consider them from most succinct (and least flexible) to least succinct (and most flexible).

### `command`
`command` is a decorator that uses creates a parser based on the function's signature:

>>> @command(help=dict(x="the base", y="the exponent"))
... def main(x: int, y: int, verbose: bool = False, quiet: bool = False):
...     return dict(x=x, y=y, verbose=verbose, quiet=quiet)
>>> main("-x", "1", "-y", "2", "--verbose")
{'x': 1, 'y': 2, 'verbose': True, 'quiet': False}
>>> main("-h")
usage:
    -x X
    -y Y
    --verbose
    --quiet
x: the base
y: the exponent

### `Args`

There are two alternative ways to express the same functionality. First, if there were many more
arguments to `nonpositional`, we might want to use `Args`, which is sugar for `nonpositional`
and slightly less expressive:

>>> from dataclasses import dataclass
>>> @dataclass  # make sure not to forget this!
... class MyArgs(Args):
...    x: int = field(help="the base")
...    y: int = field(help="the exponent")

Make sure to import `field` from `dollar_lambda`, not from `dataclasses`.

>>> p1 = flag("verbose") | flag("quiet")
>>> p = MyArgs.parser() + p1 >> done()
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
{'x': 1, 'y': 2, 'verbose': True}


### `defaults`

In our examples, default values are defined in a separate `main` function. Some users will
prefer defining defaults in the parser definition, as in most parsing libraries.
In many cases, one can do this using `Args`:

>>> @dataclass  # make sure not to forget this!
... class MyArgs(Args):
...    x: int = field(help="the base", default=1)
...    y: int = field(help="the exponent", default=2)

>>> MyArgs.parse_args()
{'x': 1, 'y': 2}

But since the logic of our original example is a bit more complicated, we will need to use the `defaults`
parser instead. Here is how:

>>> p = nonpositional(
...     (
...         flag("verbose") + defaults(quiet=False)  # either --verbose and default "quiet" to False
...         | flag("quiet") + defaults(verbose=False)  # or --quiet and default "verbose" to False
...     ),
...     option("x", type=int, help="the base"),
...     option("y", type=int, help="the exponent"),
... ) >> done()

Now we don't need a separate function to provide default values:
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
{'x': 1, 'y': 2, 'verbose': True, 'quiet': False}

## Variations on the example
### Something `argparse` can't do

What if there was a special argument, `verbosity`,
that only makes sense if the user chooses `--verbose`?

>>> p = (
...     nonpositional(
...         ((flag("verbose") + option("verbosity", type=int)) | flag("quiet")),
...         option("x", type=int),
...         option("y", type=int),
...     )
...     >> done()
... )

Remember that `+` or `Parser.__add__` evaluates two parsers in both orders
and stopping at the first order that succeeds. So this allows us to
supply `--verbose` and `--verbosity` in any order.

Now:
>>> p.parse_args("-x", "1", "-y", "2", "--quiet")
{'x': 1, 'y': 2, 'quiet': True}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose", "--verbosity", "3")
{'x': 1, 'y': 2, 'verbose': True, 'verbosity': 3}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
usage: [--verbose --verbosity VERBOSITY | --quiet] -x X -y Y
Expected '--verbose'. Got '-x'

### `Parser.many`

What if we want to specify verbosity by the number of times that `--verbose` appears?
For this we need `Parser.many`. Before showing how we could use `Parser.many` in this setting,
let's look at how it works.

`parser.many` takes `parser` and tries to apply it as many times as possible.
`Parser.many` is a bit like the `*` pattern, if you are familiar with regexes.
`parser.many` always succeeds:

>>> p = flag("verbose").many()
>>> p.parse_args()  # succeeds
{}
>>> p.parse_args("blah")  # still succeeds
{}
>>> p.parse_args("--verbose", "blah")  # still succeeds
{'verbose': True}
>>> p.parse_args("--verbose", "--verbose", return_dict=False)
[('verbose', True), ('verbose', True)]

As you can see, `return_dict=False` returns a list of tuples instead of a dict, so that you
can have duplicate keys.

Now returning to the original example:

>>> p = (
...     nonpositional(
...         flag("verbose").many(),
...         option("x", type=int),
...         option("y", type=int),
...     )
...     >> done()
... )
>>> args = p.parse_args("-x", "1", "-y", "2", "--verbose", "--verbose", return_dict=False)
>>> args
[('x', 1), ('y', 2), ('verbose', True), ('verbose', True)]
>>> verbosity = args.count(('verbose', True))
>>> verbosity
2

### `Parser.many1`



>>> p = (
...     nonpositional(
...         ((flag("verbose").many1()) | flag("quiet")),
...         option("x", type=int),
...         option("y", type=int),
...     )
...     >> done()
... )

You can also customize the order of the arguments:
>>> p = (
...     (
...         flag("verbose") + defaults(quiet=False)
...         | flag("quiet") + defaults(verbose=False)
...     )
...     >> option("x", type=int)  # note >> on this line
...     >> option("y", type=int)  # and this line
...     >> done()
... )

Now `--quiet` and `--verbose` must appear before `-x`, and `-x` must appear before `-y`:
>>> p.parse_args("--verbose", "-x", "1", "-y", "2")
{'verbose': True, 'quiet': False, 'x': 1, 'y': 2}
>>> p.parse_args("-x", "1", "--verbose", "-y", "2")
usage: [--verbose | --quiet] -x X -y Y
Expected '--verbose'. Got '-x'
>>> p.parse_args("--verbose", "-y", "2", "-x", "1")
usage: [--verbose | --quiet] -x X -y Y
Expected '-x'. Got '-y'
"""


__pdoc__ = {}

from dollar_lambda.args import Args, field
from dollar_lambda.decorators import CommandTree, command
from dollar_lambda.parser import (
    Parser,
    apply,
    apply_item,
    argument,
    defaults,
    done,
    empty,
    equals,
    flag,
    item,
    nonpositional,
    option,
    sat,
    sat_item,
    type_,
    wrap_help,
)

__all__ = [
    "Parser",
    "empty",
    "apply",
    "apply_item",
    "argument",
    "done",
    "equals",
    "flag",
    "item",
    "nonpositional",
    "option",
    "sat",
    "sat_item",
    "type_",
    "Args",
    "defaults",
    "field",
    "wrap_help",
    "command",
    "CommandTree",
]


__pdoc__["Parser.__add__"] = True
__pdoc__["Parser.__or__"] = True
__pdoc__["Parser.__rshift__"] = True
__pdoc__["Parser.__ge__"] = True
