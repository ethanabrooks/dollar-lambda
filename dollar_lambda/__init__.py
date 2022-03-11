"""
**$λ** This package provides an alternative to [`argparse`](https://docs.python.org/3/library/argparse.html) based on functional first principles.
This means that this package can handle many kinds of argument-parsing patterns that are either very awkward, difficult, or impossible with `argparse`.

# Why `$λ`?
`$λ` was built with minimal dependencies from functional first principles.
As a result, it is the most

- versatile
- type-safe
- and concise

argument parser on the market.

### Versatile
`$λ` provides high-level functionality equivalent to other parsers. But unlike other parsers,
it permits low-level customization to handle arbitrarily complex parsing patterns. As we'll see
in the tutorial, there are many parsing patterns that `$λ` can handle which are not possible with
other parsing libraries.
### Type-safe
`$λ` uses type annotations as much as Python allows. Types are checked
using [`MyPy`](https://mypy.readthedocs.io/en/stable/index.html#) and exported with the package
so that users can also benefit from the type system. Furthermore, with rare exceptions, `$λ`
avoids mutations and side-effects and preserves [referential transparency](https://en.wikipedia.org/wiki/Referential_transparency).
This makes it easier for the type-checker _and for the user_ to reason about the code.
### Concise
As we'll demonstrate in the tutorial, `$λ` provides three main syntactic shortcuts for cutting
down boilerplate:

- operators like `>>`, `|`, and `+` (and `>=` if you want to get fancy)
- the `command` decorator and the `CommandTree` object for building tree-shaped parsers
- the `Args` syntax built on top of python `dataclasses`.

As a rule, `$λ` avoids reproducing python functionality and focuses on the main job of
an argument parser: parsing. Arguably, `$λ` is way more expressive than any reasonable
person would ever need... but even if it's not the parser that we need, it's the parser we deserve.

# Installation
You guessed it:
```
pip install dollar-lambda
```

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

### `nonpositional` and `Parser.__add__`
`nonpositional` takes a sequence of parsers as arguments and attempts all permutations of them,
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
>>> p.parse_args("--quiet", "--verbose")  # you expect this to set verbose to True, but it doesn't
{'verbose': False, 'quiet': True}

Why is happening? There are two permutations:

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
We will start with the most succinct, but least flexible implementation and then
demonstrate some alternatives that tradeoff succinctness for flexibility.

### `command`
`command` is a decorator that creates a parser automatically based on
the decorated function's signature:

>>> @command(help=dict(x="the base", y="the exponent"))
... def main(x: int, y: int, verbose: bool = False, quiet: bool = False):
...     return dict(x=x, y=y, verbose=verbose, quiet=quiet)

>>> main("-h")
usage:
    -x X
    -y Y
    --verbose
    --quiet
x: the base
y: the exponent

>>> main("-x", "1", "-y", "2", "--verbose")
{'x': 1, 'y': 2, 'verbose': True, 'quiet': False}

Note that unlike our previous implementation, this will not complain if both or neither
`--verbose` and `--quiet` are given:
>>> main("-x", "1", "-y", "2")
{'x': 1, 'y': 2, 'verbose': False, 'quiet': False}
>>> main("-x", "1", "-y", "2", "--verbose", "--quiet")
{'x': 1, 'y': 2, 'verbose': True, 'quiet': True}

### `CommandTree`
To make the flags mutually exclusive, we can use `CommandTree`:
>>> tree = CommandTree()

First, we make `base_function` the root of our tree:
>>> @tree.command(help=dict(x="the base", y="the exponent"))
... def base_function(x: int, y: int):
...     print(dict(x=x, y=y))

Next, we make `verbose_function` a branch off of `base_function`:
>>> @base_function.command()
... def verbose_function(x: int, y: int, verbose: bool):
...     print(dict(x=x, y=y, verbose=verbose))

Note that `verbose_function` must include all the arguments from `base_function`.
And we make `quiet_function` a second branch:
>>> @base_function.command()
... def quiet_function(x: int, y: int, quiet: bool):
...     print(dict(x=x, y=y, quiet=quiet))

Again we include all arguments from `base_function`.
Now we can invoke `tree.main` to dynamically dispatch the parsed arguments to the function
whose corresponding parser succeeds first:

>>> tree.main("-x", "1", "-y", "2", "--verbose")  # this will dispatch to verbose_function
{'x': 1, 'y': 2, 'verbose': True}
>>> tree.main("-x", "1", "-y", "2", "--quiet")  # this will dispatch to quiet_function
{'x': 1, 'y': 2, 'quiet': True}
>>> tree.main("-x", "1", "-y", "2")  # this will dispatch to base_function
{'x': 1, 'y': 2}
>>> tree.main("-x", "1", "-y", "2", "--verbose", "--verbose")  # this will fail
usage: -x X -y Y [--verbose | --quiet]
x: the base
y: the exponent
Unrecognized argument: --verbose

To make one or the other flag required, the `command` method takes a `required` argument.
>>> tree = CommandTree()
...
>>> @tree.command(help=dict(x="the base", y="the exponent"))
... def base_function(x: int, y: int):
...     raise RuntimeError("Does not execute because children are required.")
...
>>> @base_function.command(required=True)
... def verbose_function(x: int, y: int, verbose: bool):
...     print(dict(x=x, y=y, verbose=verbose))
...
>>> @base_function.command(required=True)
... def quiet_function(x: int, y: int, quiet: bool):
...     print(dict(x=x, y=y, quiet=quiet))
>>> tree.main("-x", "1", "-y", "2", "--verbose")  # succeeds
{'x': 1, 'y': 2, 'verbose': True}
>>> tree.main("-x", "1", "-y", "2")  # fails
usage: -x X -y Y [--verbose | --quiet]
x: the base
y: the exponent
The following arguments are required: --verbose

Note that all children must be required or else `base_function` will execute in the
absence of any flags.

`CommandTree` is especially useful when you want different parse-results to invoke different functions.
One drawback of `CommandTree` is that it cannot be freely combined with other parsers.
Parsers produced by `CommandTree` are specialized for use with decorated functions
and don't play well with more general-purpose parsers.

### `Args`

`Args` is a lighter-weight alternative, providing mostly syntactic sugar and a bit of logic around
the `nonpositional` function:

>>> from dataclasses import dataclass
>>> @dataclass  # make sure not to forget this!
... class MyArgs(Args):
...    x: int = field(help="the base")
...    y: int = field(help="the exponent")

Make sure to import `field` from `dollar_lambda`, not from `dataclasses`.
Now we can use `MyArgs.parser()` in combinations with other parsers:

>>> p1 = flag("verbose") | flag("quiet")
>>> p = MyArgs.parser() + p1 >> done()
>>> p.parse_args("-h")
usage: -x X -y Y [--verbose | --quiet]
x: the base
y: the exponent
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
{'x': 1, 'y': 2, 'verbose': True}

You can omit the `field` expressions:
>>> from dataclasses import dataclass
>>> @dataclass  # make sure not to forget this!
... class MyArgs(Args):
...    x: int
...    y: int
>>> MyArgs.parse_args("-x", "1", "-y", "2")
{'x': 1, 'y': 2}

But you lose help-strings:
>>> MyArgs.parse_args("-h")
usage: -x X -y Y

The `field` expressions can also be used to define default values:

>>> @dataclass  # make sure not to forget this!
... class MyArgs(Args):
...    x: int = field(help="the base", default=1)
...    y: int = field(help="the exponent", default=2)

>>> MyArgs.parse_args()
{'x': 1, 'y': 2}

## Variations on the example
### Variable numbers of arguments

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

This is also a case where you might want to use `CommandTree`:

>>> tree = CommandTree()

>>> @tree.command(help=dict(x="the base", y="the exponent"))
... def base_function(x: int, y: int):
...     print(dict(x=x, y=y))

>>> @base_function.command()
... def verbose_function(x: int, y: int, verbose: bool, verbosity: int):
...     print(dict(x=x, y=y, verbose=verbose, verbosity=verbosity))

>>> @base_function.command()
... def quiet_function(x: int, y: int, quiet: bool):
...     print(dict(x=x, y=y, quiet=quiet))

>>> tree.main("-x", "1", "-y", "2", "--verbose", "--verbosity", "3")
{'x': 1, 'y': 2, 'verbose': True, 'verbosity': 3}

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

In the previous example, the parse will default to `verbosity=0` if no `--verbose` flags
are given.  What if we wanted users to be explicit about choosing a "quiet" setting?
In other words, what if the user actually had to provide an explicit `--quiet` flag when
no `--verbose` flags were given?

For this, we use `Parser.many1`. This method is like `Parser.many` except that it fails
when on zero successes (recall that `Parser.many` always succeeds). So if `Parser.many`
is like regex `*`, `Parser.many1` is like `+`. Take a look:

>>> p = flag("verbose").many()
>>> p.parse_args()  # succeeds
{}
>>> p = flag("verbose").many1()
>>> p.parse_args()  # fails
usage: --verbose [--verbose ...]
The following arguments are required: --verbose
>>> p.parse_args("--verbose")  # succeeds
{'verbose': True}

To compell that `--quiet` flag from our users, we can do the following:

>>> p = (
...     nonpositional(
...         ((flag("verbose").many1()) | flag("quiet")),
...         option("x", type=int),
...         option("y", type=int),
...     )
...     >> done()
... )

Now omitting both `--verbose` and `--quiet` will fail:
>>> p.parse_args("-x", "1", "-y", "2")
usage: [--verbose [--verbose ...] | --quiet] -x X -y Y
Expected '--verbose'. Got '-x'
>>> p.parse_args("--verbose", "-x", "1", "-y", "2") # this succeeds
{'verbose': True, 'x': 1, 'y': 2}
>>> p.parse_args("--quiet", "-x", "1", "-y", "2") # and this succeeds
{'quiet': True, 'x': 1, 'y': 2}
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
