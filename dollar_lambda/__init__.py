"""
This package provides an alternative to [`argparse`](https://docs.python.org/3/library/argparse.html)
based on parser combinators and functional first principles. Arguably, `$λ` is way more expressive than any reasonable
person would ever need... but even if it's not the parser that we need, it's the parser we deserve.

# Installation
```
pip install dollar-lambda
```

# Highlights
`$λ` comes with syntactic sugar that came make building parsers completely boilerplate-free.
However, with more concise syntax comes less flexibility. For more complex parsing situations,
there are modular building blocks that lie behind the syntactic sugar which enable parsers to
handle any reasonable amount of logical complexity.

## The [`@command`](#dollar_lambda.command) decorator
This syntax is best for simple parsers that take a set of unordered arguments:

>>> @command()
... def main(x: int, dev: bool = False, prod: bool = False):
...     return dict(x=x, dev=dev, prod=prod)

Here is the help text generated by this parser:

>>> main("-h")
usage: -x X --dev --prod

And here it is in action:

>>> main("-x", "1", "--dev")
{'x': 1, 'dev': True, 'prod': False}

.. Note::

    Ordinarily you would provide `main` no arguments and
    it would get them from the command line, as in:

        main()

    which would be equivalent to:

        main(*sys.argv[1:])

    In this document, the string arguments are for demonstration purposes only.

`command` takes arguments that allow you to supply
help strings and custom types:

>>> @command(types=dict(x=lambda x: int(x) + 1), help=dict(x="A number that gets incremented."))
... def main(x: int, dev: bool = False, prod: bool = False):
...     return dict(x=x, dev=dev, prod=prod)
...

>>> main("-h")
usage: -x X --dev --prod
x: A number that gets incremented.

>>> main("-x", "1", "--dev")
{'x': 2, 'dev': True, 'prod': False}

## `CommandTree` for dynamic dispatch
For many programs, a user will want to use one entrypoint for one set of
arguments, and another for another set of arguments. Returning to our example,
let's say we wanted to execute `prod_function` when the user provides the
`--prod` flag, and `dev_function` when the user provides the `--dev` flag:

>>> tree = CommandTree()
...
>>> @tree.command()
... def base_function(x: int):
...     print("Ran base_function with arguments:", dict(x=x))
...
>>> @base_function.command()
... def prod_function(x: int, prod: bool):
...     print("Ran prod_function with arguments:", dict(x=x, prod=prod))
...
>>> @base_function.command()
... def dev_function(x: int, dev: bool):
...     print("Ran dev_function with arguments:", dict(x=x, dev=dev))

Let's see how this parser handles different inputs.
If we provide the `--prod` flag, `$λ` automatically invokes
 `prod_function` with the parsed arguments:

>>> tree("-x", "1", "--prod")
Ran prod_function with arguments: {'x': 1, 'prod': True}

If we provide the `--dev` flag, `$λ` invokes `dev_function`:

>>> tree("-x", "1", "--dev")
Ran dev_function with arguments: {'x': 1, 'dev': True}

With this configuration, the parser will run `base_function` if neither
`--prod` nor `--dev` are given:

>>> tree("-x", "1")
Ran base_function with arguments: {'x': 1}

There are many other ways to use `CommandTree`,
including some that make use of the `base_function`.
To learn more, we recommend the [`CommandTree` tutorial](#commandtree-tutorial).

## Lower-level syntax
[`@command`](#dollar_lambda.command) and `CommandTree` cover many use cases,
but they are both syntactic sugar for a lower-level interface that is far
more expressive.

Suppose you want to implement a parser that first tries to parse an option
(a flag that takes an argument),
`-x X` and if that fails, tries to parse the input as a variadic sequence of
floats:

>>> p = option("x", type=int) | argument("y", type=float).many()

We go over this syntax in greater detail in the [tutorial](#tutorial).
For now, suffice to say that `argument` defines a positional argument,
[`many`](#dollar_lambda.Parser.many) allows parsers to be applied
zero or more times, and [`|`](#dollar_lambda.Parser.__or__) expresses alternatives.

Here is the help text:

>>> p.parse_args("-h")
usage: [-x X | [Y ...]]

As promised, this succeeds:

>>> p.parse_args("-x", "1")
{'x': 1}

And this succeeds:

>>> p.parse_args("1", "2", "3", return_dict=False)
[('y', 1.0), ('y', 2.0), ('y', 3.0)]

# Tutorial

We've already seen many of the concepts that power `$λ` in the
[Highlights](#highlights) section. This tutorial will address
these concepts one at a time and expose the reader to some
nuances of usage.

## An example from `argparse`

Many of you are already familiar with `argparse`.
You may even recognize this example from the `argparse` docs:

```
import argparse
parser = argparse.ArgumentParser(description="calculate X to the power of Y")
group = parser.add_mutually_exclusive_group()
group.add_argument("-v", "--verbose", action="store_true")
group.add_argument("-q", "--quiet", action="store_true")
parser.add_argument("x", type=int, help="the base")
parser.add_argument("y", type=int, help="the exponent")
args = parser.parse_args()
```

Here is the exact equivalent in this package:

>>> p = nonpositional(
...     (flag("verbose") | flag("quiet")).optional(),
...     option("x", type=int, help="the base"),
...     option("y", type=int, help="the exponent"),
... )
...
>>> def main(x, y, verbose=False, quiet=False):
...     return dict(x=x, y=y, verbose=verbose, quiet=quiet)

Here is the help text:

>>> p.parse_args("-h")
usage: [--verbose | --quiet] -x X -y Y
x: the base
y: the exponent

As indicated, this succeeds given `--verbose`

>>> main(**p.parse_args("-x", "1", "-y", "2", "--verbose"))
{'x': 1, 'y': 2, 'verbose': True, 'quiet': False}

or `--quiet`

>>> main(**p.parse_args("-x", "1", "-y", "2", "--quiet"))
{'x': 1, 'y': 2, 'verbose': False, 'quiet': True}

or neither

>>> main(**p.parse_args("-x", "1", "-y", "2"))
{'x': 1, 'y': 2, 'verbose': False, 'quiet': False}

Let's walk through this step by step.

## High-Level Parsers
So far we've seen a few different parser constructors.
`flag` binds a boolean value to a variable whereas `option` binds an arbitrary value to a variable.
`done` does not bind any values to variables, but only
succeeds on the end of input.

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

## Parser Combinators
Parser combinators are functions that combine multiple parsers into new, more complex parsers.
Our example uses three such functions: `nonpositional`, [`|`](#dollar_lambda.Parser.__or__)
and [`>>`](#dollar_lambda.Parser.__rshift__).

### [`|`](#dollar_lambda.Parser.__or__)

The [`|`](#dollar_lambda.Parser.__or__) operator is used for alternatives. Specifically, it will try the first parser,
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

We can permit the omission of both flags
by using `optional`, as we saw earlier, or we can supply a default value:

>>> (flag("verbose") | flag("quiet")).optional().parse_args() # flags fail, but that's ok
{}
>>> (flag("verbose") | flag("quiet", default=False)).parse_args() # flag("verbose") fails but flag("quiet", default=False) succeeds
{'quiet': False}

This is just sugar for

>>> (flag("verbose") | flag("quiet") | defaults(quiet=False)).parse_args() # flag("verbose") fails but flag("quiet", default=False) succeeds
{'quiet': False}

Users should note that unlike logical "or" but like Python `or`, the `|` operator is not commutative:

>>> (flag("verbose") | argument("x")).parse_args("--verbose")
{'verbose': True}

>>> (argument("x") | flag("verbose")).parse_args("--verbose")
{'x': '--verbose'}

Users may therefore prefer

### [`>>`](#dollar_lambda.Parser.__rshift__)

The [`>>`](#dollar_lambda.Parser.__rshift__) operator is used for sequential composition. It applies the first parser and then
hands the output of the first parser to the second parser. If either parser fails, the composition fails:

>>> p = flag("verbose")
>>> p.parse_args("--verbose")
{'verbose': True}
>>> p.parse_args("--something-else")  # first parser will fail
usage: --verbose
Expected '--verbose'. Got '--something-else'
>>> p.parse_args("--verbose", "--something-else")  # second parser will fail
usage: --verbose
Unrecognized argument: --something-else

### `nonpositional` and [`+`](#dollar_lambda.Parser.__add__)
`nonpositional` takes a sequence of parsers as arguments and attempts all permutations of them,
returning the first permutations that is successful:

>>> p = nonpositional(flag("verbose"), flag("quiet"))
>>> p.parse_args("--verbose", "--quiet")
{'verbose': True, 'quiet': True}
>>> p.parse_args("--quiet", "--verbose")  # reverse order also works
{'quiet': True, 'verbose': True}

For just two parsers you can use [`+`](#dollar_lambda.Parser.__add__) instead of `nonpositional`:
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

## Putting it all together
Let's recall the original example:

>>> p = nonpositional(
...     (flag("verbose") | flag("quiet")).optional(),
...     option("x", type=int, help="the base"),
...     option("y", type=int, help="the exponent"),
... )
...
>>> def main(x, y, verbose=False, quiet=False):
...     return dict(x=x, y=y, verbose=verbose, quiet=quiet)

As we've seen, `(flag("verbose") | flag("quiet")).optional()` succeeds on either `--verbose` or `--quiet`
or neither.

`option("x", type=int)` succeeds on `-x X`, where `X` is
some integer, binding that integer to the variable `"x"`. Similarly for `option("y", type=int)`.

`nonpositional` takes the three parsers:

- `(flag("verbose") | flag("quiet")).optional()`
- `option("x", type=int)`
- `option("y", type=int)`

and applies them in every order, until some order succeeds.

## Variations on the example
### Variable numbers of arguments

What if there was a special argument, `verbosity`,
that only makes sense if the user chooses `--verbose`?

>>> p = nonpositional(
...    ((flag("verbose") + option("verbosity", type=int)) | flag("quiet")),
...    option("x", type=int),
...    option("y", type=int),
... )

Remember that [`+`](#dollar_lambda.Parser.__add__) evaluates two parsers in both orders
and stopping at the first order that succeeds. So this allows us to
supply `--verbose` and `--verbosity` in any order.

>>> p.parse_args("-x", "1", "-y", "2", "--quiet")
{'x': 1, 'y': 2, 'quiet': True}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose", "--verbosity", "3")
{'x': 1, 'y': 2, 'verbose': True, 'verbosity': 3}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
usage: [--verbose --verbosity VERBOSITY | --quiet] -x X -y Y
Expected '--verbose'. Got '-x'

This is also a case where you might want to use `CommandTree`:

>>> tree = CommandTree()
...
>>> @tree.command(help=dict(x="the base", y="the exponent"))
... def base_function(x: int, y: int):
...     raise RuntimeError("This function will not execute.")
...
>>> @base_function.command()
... def verbose_function(x: int, y: int, verbose: bool, verbosity: int):
...     print(dict(x=x, y=y, verbose=verbose, verbosity=verbosity))
...
>>> @base_function.command()
... def quiet_function(x: int, y: int, quiet: bool):
...     print(dict(x=x, y=y, quiet=quiet))
...
>>> tree("-x", "1", "-y", "2", "--verbose", "--verbosity", "3")
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
>>> p.parse_args("--verbose")  # still succeeds
{'verbose': True}
>>> p.parse_args("--verbose", "--verbose", return_dict=False)
[('verbose', True), ('verbose', True)]

As you can see, `return_dict=False` returns a list of tuples instead of a dict, so that you
can have duplicate keys.

Now returning to the original example:

>>> p = nonpositional(
...     flag("verbose").many(),
...     option("x", type=int),
...     option("y", type=int),
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
is like regex `*`, `Parser.many1` is like [`+`](#dollar_lambda.Parser.__add__). Take a look:

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

>>> p = nonpositional(
...    ((flag("verbose").many1()) | flag("quiet")),
...    option("x", type=int),
...    option("y", type=int),
... )

Now omitting both `--verbose` and `--quiet` will fail:
>>> p.parse_args("-x", "1", "-y", "2")
usage: [--verbose [--verbose ...] | --quiet] -x X -y Y
Expected '--verbose'. Got '-x'
>>> p.parse_args("--verbose", "-x", "1", "-y", "2") # this succeeds
{'verbose': True, 'x': 1, 'y': 2}
>>> p.parse_args("--quiet", "-x", "1", "-y", "2") # and this succeeds
{'quiet': True, 'x': 1, 'y': 2}

# `CommandTree` Tutorial
`CommandTree` has already shown up in the
[Highlights section](#commandtree-for-dynamic-dispatch)
and in the earlier [tutorial](#variations-on-the-example).
In this section we will give a more thorough treatment,
exposing some of the underlying logic and covering all
the variations in functionality that `CommandTree`
offers.

## `CommandTree.command`

First let's walk through the use of the `CommandTree.command` decorator, one step
at a time. First we define the object:

>>> tree = CommandTree()

Now we define at least one child function:

>>> @tree.command()
... def f1(a: int):
...     return dict(f1=dict(a=a))

At this point `tree` is just a parser that takes a single option `-a`:

>>> tree("-h")
usage: -a A

Now let's add a second child function:

>>> @tree.command()
... def f2(b: bool):
...     return dict(f2=dict(b=b))
...
>>> tree("-h")
usage: [-a A | -b]

`tree` will execute either `f1` or `f2` based on which of the parsers succeeds.
This will execute `f1`:

>>> tree("-a", "1")
{'f1': {'a': 1}}

This will execute `f2`:

>>> tree("-b")
{'f2': {'b': True}}

This fails:

>>> tree()
usage: [-a A | -b]
The following arguments are required: -a

Often in cases where there are alternative sets of argument like this,
there is also a set of shared arguments. It would be cumbersome to have to
repeat these for both child functions. Instead we can define a parent function
as follows:

>>> tree = CommandTree()
...
>>> @tree.command()
... def f1(a: int):
...     raise RuntimeError("This function will not execute.")

And a child function, `g1`:

>>> @f1.command()  # note f1, not tree
... def g1(a:int, b: bool):
...     return dict(g1=dict(b=b))

Make sure to include all the arguments of `f1` in `g1` or else
`g1` will fail when it is invoked. In its current state, `tree` sequences
 the arguments of `f1` and `g1`:

>>> tree("-h")
usage: -a A -b

As before we can define an additional child function to induce alternative
argument sets:

>>> @f1.command()  # note f1, not tree
... def g2(a: int, c: str):
...     return dict(g2=dict(c=c))

Note that our usage message shows `-a A` preceding the brackets:
>>> tree("-h")
usage: -a A [-b | -c C]

To execute `g1`, we give the `-b` flag:
>>> tree("-a", "1", "-b")
{'g1': {'b': True}}

To execute `g2`, we give the `-c` flag:
>>> tree("-a", "1", "-c", "foo")
{'g2': {'c': 'foo'}}

Also, note that `tree` can have arbitrary depth:

>>> @g1.command()  # h1 is a child of g1
... def h1(a: int, b: bool, d: float):
...    return dict(h1=dict(d=d))

>>> tree("-h")
usage: -a A [-b -d D | -c C]

## `CommandTree.subcommand`
Often we want to explicitly specify which function to execute by naming it on the command line.
This would implement functionality similar to
[`ArgumentParser.add_subparsers`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_subparsers)

For this we would use the `CommandTree.subcommand` decorator:

>>> tree = CommandTree()
...
>>> @tree.command()
... def f1(a: int):
...     raise RuntimeError("This function should not be called")
...
>>> @f1.subcommand()  # note subcommand, not command
... def g1(a:int, b: bool):
...     return dict(g1=dict(b=b))
...
>>> @f1.subcommand()  # again, subcommand, not command
... def g2(a: int, c: str):
...     return dict(g2=dict(c=c))

Now the usage message indicates that `g1` and `g2` are required arguments:
>>> tree("-h")
usage: -a A [g1 -b | g2 -c C]

Now we would select g1 as follows:
>>> tree("-a", "1", "g1", "-b")
{'g1': {'b': True}}

And g2 as follows:
>>> tree("-a", "1", "g2", "-c", "foo")
{'g2': {'c': 'foo'}}

# Why `$λ`?

`$λ` can handle many kinds of argument-parsing patterns
that are either very awkward, difficult, or impossible with other parsing libraries.
In particular, we emphasize the following qualities:

### Versatile
`$λ` provides high-level functionality equivalent to other parsers. But unlike other parsers,
it permits low-level customization to handle arbitrarily complex parsing patterns.
There are many parsing patterns that `$λ` can handle which are not possible with other parsing libraries.

### Type-safe
`$λ` uses type annotations as much as Python allows. Types are checked using [`MyPy`](
https://mypy.readthedocs.io/en/stable/index.html#) and exported with the package so that users can also benefit from
the type system. Furthermore, with rare exceptions, `$λ` avoids mutations and side-effects and preserves [referential
transparency](https://en.wikipedia.org/wiki/Referential_transparency). This makes it easier for the type-checker _and
for the user_ to reason about the code.

### Concise
`$λ` provides many syntactic shortcuts for cutting down boilerplate:

- operators like [`>>`](#dollar_lambda.Parser.__rshift__), [`|`](#dollar_lambda.Parser.__or__), and [`+`](#dollar_lambda.Parser.__add__) (and [`>=`](#dollar_lambda.Parser.__ge__) if you want to get fancy)
- the `command` decorator and the `CommandTree` object for building tree-shaped parsers
- the `Args` syntax built on top of python `dataclasses`.


As a rule, `$λ` avoids reproducing python functionality and focuses on the main job of
an argument parser: parsing.
"""


__pdoc__ = {}

from dollar_lambda.args import Args, field
from dollar_lambda.decorators import CommandTree, command
from dollar_lambda.parser import (
    Parser,
    apply,
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
)

__all__ = [
    "Parser",
    "empty",
    "apply",
    "argument",
    "done",
    "equals",
    "flag",
    "item",
    "nonpositional",
    "option",
    "sat",
    "Args",
    "defaults",
    "field",
    "command",
    "CommandTree",
]


__pdoc__["Parser.__add__"] = True
__pdoc__["Parser.__or__"] = True
__pdoc__["Parser.__xor__"] = True
__pdoc__["Parser.__rshift__"] = True
__pdoc__["Parser.__ge__"] = True
