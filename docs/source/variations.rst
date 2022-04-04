Variations on the tutorial example
==================================
In the :doc:`tutorial`, we worked through an example, drawn from
:doc:`argparse<python:library/argparse>` and showed how to express
that logic using the higher-level :py:func:`@command<dollar_lambda.command>`
syntax. In this section we will explore some variations in the logic
in that example that would be difficult or impossible to handle with
:doc:`argparse<python:library/argparse>`.

Positional arguments
--------------------

What if we wanted to supply ``x`` and ``y`` as positional arguments?

>>> from dollar_lambda import flag, option
>>> flags = flag("verbose") | flag("quiet")
>>> p = option("x", type=int) >> option("y", type=int) >> flags
>>> p.parse_args("-h")
usage: -x X -y Y [--verbose | --quiet]

This introduces a new parser combinator:
:py:meth:`>><dollar_lambda.Parser.__rshift__>` which evaluates parsers in
sequence. In this example, it would first evaluate the
``option("x", type=int)`` parser, and if that succeeded, it would hand
the unparsed remainder on to the ``option("y", type=int)`` parser, and
so on until all parsers have been evaluated or no more input remains. If
any of the parsers fail, the combined parser fails:

>>> p.parse_args("-x", "1", "-y", "2", "--quiet") # succeeds
{'x': 1, 'y': 2, 'quiet': True}
>>> p.parse_args("-typo", "1", "-y", "2", "--quiet") # first parser fails
usage: -x X -y Y [--verbose | --quiet]
Expected '-x'. Got '-typo'
>>> p.parse_args("-x", "1", "-y", "2", "--typo") # third parser fails
usage: -x X -y Y [--verbose | --quiet]
Expected '--verbose'. Got '--typo'

Unlike with :py:func:`nonpositional<dollar_lambda.nonpositional>` in the previous section,
:py:meth:`>><dollar_lambda.Parser.__rshift__>` requires the user to
provide arguments in a fixed order:

>>> p.parse_args("-y", "2", "-x", "1", "--quiet") # fails
usage: -x X -y Y [--verbose | --quiet]
Expected '-x'. Got '-y'

When using positional arguments, it might make sense to drop the ``-x``
and ``-y`` flags:

>>> from dollar_lambda import argument
>>> p = argument("x", type=int) >> argument("y", type=int) >> flags
>>> p.parse_args("-h")
usage: X Y [--verbose | --quiet]
>>> p.parse_args("1", "2", "--quiet")
{'x': 1, 'y': 2, 'quiet': True}

:py:func:`argument<dollar_lambda.argument>` will bind input to a variable without checking for any
special flag strings like ``-x`` or ``-y`` preceding the input.

Variable numbers of arguments
-----------------------------

What if there was a special argument, ``verbosity``, that only makes
sense if the user chooses ``--verbose``?

>>> from dollar_lambda import nonpositional
>>> p = nonpositional(
...     (flag("verbose") + option("verbosity", type=int)) | flag("quiet"),
...     option("x", type=int),
...     option("y", type=int),
... )

Remember that :py:meth:`+<dollar_lambda.Parser.__add__>` evaluates two
parsers in both orders and stopping at the first order that succeeds. So
this allows us to supply ``--verbose`` and ``--verbosity`` in any order.

>>> p.parse_args("-x", "1", "-y", "2", "--quiet")
{'x': 1, 'y': 2, 'quiet': True}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose", "--verbosity", "3")
{'x': 1, 'y': 2, 'verbose': True, 'verbosity': 3}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
usage: [--verbose --verbosity VERBOSITY | --quiet] -x X -y Y
Expected '--verbose'. Got '-x'

We could express the same logic with the
:py:func:`@command<dollar_lambda.command>` decorator:

>>> from dollar_lambda import command
>>> @command(
...     parsers=dict(
...         kwargs=flag("verbose") + option("verbosity", type=int) | flag("quiet")
...     ),
...     help=dict(x="the base", y="the exponent"),
... )
... def main(x: int, y: int, **kwargs):
...     pass  # do work

This is also a case where you might want to use
:py:class:`CommandTree<dollar_lambda.CommandTree>`

>>> from dollar_lambda import CommandTree
>>> tree = CommandTree()
...
>>> @tree.command(help=dict(x="the base", y="the exponent"))
... def base_function(x: int, y: int):
...     pass # do work
...
>>> @base_function.command()
... def verbose_function(x: int, y: int, verbose: bool, verbosity: int):
...     args = dict(x=x, y=y, verbose=verbose, verbosity=verbosity)
...     print("invoked verbose_function with args", args)
...
>>> @base_function.command()
... def quiet_function(x: int, y: int, quiet: bool):
...     pass # do work
...
>>> tree("-x", "1", "-y", "2", "--verbose", "-verbosity", "3")
invoked verbose_function with args {'x': 1, 'y': 2, 'verbose': True, 'verbosity': 3}

:py:meth:`many<dollar_lambda.Parser.many>`
------------------------------------------

What if we want to specify verbosity by the number of times that
``--verbose`` appears? For this we need
:py:meth:`Parser.many<dollar_lambda.Parser.many>`. Before showing
how we could use :py:meth:`.many<dollar_lambda.Parser.many>`
in this setting, let's look at how it works.

:py:meth:`parser.many<dollar_lambda.Parser.many>` takes ``parser`` and tries to apply it as many times as
possible. :py:meth:`Parser.many<dollar_lambda.Parser.many>` is a bit like the ``*`` pattern, if you are
familiar with regexes. :py:meth:`Parser.many<dollar_lambda.Parser.many>` always succeeds:

>>> p = flag("verbose").many()
>>> p.parse_args() # succeeds
{}
>>> p.parse_args("--verbose") # still succeeds
{'verbose': True}
>>> p.parse_args("--verbose", "--verbose") # succeeds, binding list to 'verbose'
{'verbose': [True, True]}

Now returning to the original example:

>>> p = nonpositional(
...     flag("verbose").many(),
...     option("x", type=int),
...     option("y", type=int),
... )
>>> args = p.parse_args("-x", "1", "-y", "2", "--verbose", "--verbose")
>>> args
{'x': 1, 'y': 2, 'verbose': [True, True]}
>>> verbosity = len(args['verbose'])
>>> verbosity
2

:py:meth:`many1<dollar_lambda.Parser.many1>`
--------------------------------------------

In the previous example, the parse will default to ``verbosity=0`` if no
``--verbose`` flags are given. What if we wanted users to be explicit
about choosing a "quiet" setting? In other words, what if the user
actually had to provide an explicit ``--quiet`` flag when no
``--verbose`` flags were given?

For this, we use :py:meth:`Parser.many1<dollar_lambda.Parser.many1>`. This method is like ``Parser.many``
except that it fails when on zero successes (recall that :py:meth:`.many<dollar_lambda.Parser.many>`
always succeeds). So if :py:meth:`Parser.many<dollar_lambda.Parser.many>` is like regex ``*``,
:py:meth:`Parser.many1<dollar_lambda.Parser.many1>` is like ``+``.
Let's take a look:

>>> p = flag("verbose").many()
>>> p.parse_args() # succeeds
{}
>>> p = flag("verbose").many1() # note many1(), not many()
>>> p.parse_args() # fails
usage: --verbose [--verbose ...]
The following arguments are required: --verbose
>>> p.parse_args("--verbose") # succeeds
{'verbose': True}

To compel that ``--quiet`` flag from our users, we can do the
following:

>>> p = nonpositional(
...     ((flag("verbose").many1()) | flag("quiet")),
...     option("x", type=int),
...     option("y", type=int),
... )

Now omitting both ``--verbose`` and ``--quiet`` will fail:

>>> p.parse_args("-x", "1", "-y", "2")
usage: [--verbose [--verbose ...] | --quiet] -x X -y Y
Expected '--verbose'. Got '-x'
>>> p.parse_args("--verbose", "-x", "1", "-y", "2") # this succeeds
{'verbose': True, 'x': 1, 'y': 2}
>>> p.parse_args("--quiet", "-x", "1", "-y", "2") # and this succeeds
{'quiet': True, 'x': 1, 'y': 2}
