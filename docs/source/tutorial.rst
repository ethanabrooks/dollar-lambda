Tutorial
========

We've already seen many of the concepts that power ``$λ`` in the
:ref:`index:Highlights` section. This tutorial will address these
concepts one at a time and expose the reader to some nuances of usage.

An example from :doc:`argparse<python:library/argparse>`
--------------------------------------------------------

Many of you are already familiar with :doc:`argparse<python:library/argparse>`. You may even
recognize this example from the
`argparse docs <https://docs.python.org/3/howto/argparse.html#conflicting-options>`_:

::

   import argparse
   parser = argparse.ArgumentParser(description="calculate X to the power of Y")
   group = parser.add_mutually_exclusive_group()
   group.add_argument("-v", "--verbose", action="store_true")
   group.add_argument("-q", "--quiet", action="store_true")
   parser.add_argument("x", type=int, help="the base")
   parser.add_argument("y", type=int, help="the exponent")
   args = parser.parse_args()

Here is one way to express this logic in ``$λ``:

>>> from dollar_lambda import command, flag
>>> @command(
...     parsers=dict(kwargs=(flag("verbose") | flag("quiet")).optional()),
...     help=dict(x="the base", y="the exponent"),
... )
... def main(x: int, y: int, **kwargs):
...     print(dict(x=x, y=y, **kwargs))

Here is the help text for this parser:

>>> main("-h")
usage: -x X -y Y [--verbose | --quiet]
x: the base
y: the exponent

As indicated, this succeeds given ``--verbose``

>>> main("-x", "1", "-y", "2", "--verbose")
{'x': 1, 'y': 2, 'verbose': True}

or ``--quiet``

>>> main("-x", "1", "-y", "2", "--quiet")
{'x': 1, 'y': 2, 'quiet': True}

or neither

>>> main("-x", "1", "-y", "2")
{'x': 1, 'y': 2}

.. Note::

   Ordinarily , we would not feed ``main`` any arguments, and it would get
   them from the command line:

   >>> import sys
   >>> sys.argv[1:] = ["-x", "1", "-y", "2"] # simulate command line input
   >>> parsers.TESTING = False # unnecessary outside doctests
   >>> main()
   {'x': 1, 'y': 2}
   >>> parsers.TESTING = True

Equivalent in lower-level syntax
--------------------------------

To better understand what is going on here, let's remove the syntactic
sugar:

>>> from dollar_lambda import nonpositional, option
>>> p = nonpositional(
...     (flag("verbose") | flag("quiet")).optional(),
...     option("x", type=int, help="the base"),
...     option("y", type=int, help="the exponent"),
... )
...
>>> def main(x, y, **kwargs):
...     return dict(x=x, y=y, **kwargs)
...
>>> main(**p.parse_args("-x", "1", "-y", "2", "--verbose"))
{'x': 1, 'y': 2, 'verbose': True}
>>> main(**p.parse_args("-x", "1", "-y", "2", "--quiet"))
{'x': 1, 'y': 2, 'quiet': True}
>>> main(**p.parse_args("-x", "1", "-y", "2"))
{'x': 1, 'y': 2}

Now let's walk through this step by step.

High-Level Parsers
------------------

In the de-sugared implementation there are two different parser
constructors: :py:func:`flag<dollar_lambda.parsers.flag>`, which binds a boolean value to a variable, and
:py:func:`option<dollar_lambda.parsers.option>`, which binds an arbitrary value to a variable.

:py:func:`flag<dollar_lambda.parsers.flag>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

>>> p = flag("verbose")
>>> p.parse_args("--verbose")
{'verbose': True}

By default :py:func:`flag<dollar_lambda.parsers.flag>` fails when it does not receive expected input:

>>> p.parse_args()
usage: --verbose
The following arguments are required: --verbose

Alternately, you can set a default value:

>>> flag("verbose", default=False).parse_args()
{'verbose': False}

:py:func:`option<dollar_lambda.parsers.option>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:py:func:`option<dollar_lambda.parsers.option>` is similar but takes an argument:
By default, :py:func:`option<dollar_lambda.parsers.option>`, expects a single
``-`` for single-character variable names (as in
``-x``), as opposed to ``--`` for longer names (as in ``--xenophon``):

>>> option("x").parse_args("-x", "1")
{'x': '1'}
>>> option("xenophon").parse_args("-xenophon", "1")
{'xenophon': '1'}

Use the ``type`` argument to convert the input to a different type:

>>> option("x", type=int).parse_args("-x", "1") # converts "1" to an int
{'x': 1}

Parser Combinators
------------------

Parser combinators are functions that combine multiple parsers into new,
more complex parsers. Our example uses two such functions:
:py:func:`nonpositional<dollar_lambda.parsers.nonpositional>` and
:py:meth:`|<dollar_lambda.parsers.Parser.__or__>`.

:py:meth:`|<dollar_lambda.parsers.Parser.__or__>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :py:meth:`|<dollar_lambda.parsers.Parser.__or__>` operator is used for
alternatives. Specifically, it will try the first parser, and if that
fails, try the second:

>>> p = flag("verbose") | flag("quiet")
>>> p.parse_args("--quiet") # flag("verbose") fails
{'quiet': True}
>>> p.parse_args("--verbose") # flag("verbose") succeeds
{'verbose': True}

By default one of the two flags would be required to prevent failure:

>>> p.parse_args() # neither flag is provided so this fails usage:
usage: [--verbose | --quiet]
The following arguments are required: --verbose

We can permit the omission of both flags by using
:py:meth:`optional<dollar_lambda.parsers.Parser.optional>`, as we
saw earlier, or we can supply a default value:

>>> (flag("verbose") | flag("quiet")).optional().parse_args() # flags fail, but that's ok
{}
>>> (flag("verbose") | flag("quiet", default=False)).parse_args()
{'quiet': False}

In the second example,  ``flag("verbose")`` fails but
``flag("quiet", default=False)`` succeeds.

.. Note::
   Unlike logical "or" but like Python ``or``, the

   :py:meth:`|<dollar_lambda.parsers.Parser.__or__>` operator is not commutative:

   >>> from dollar_lambda import argument
   >>> (flag("verbose") | argument("x")).parse_args("--verbose")
   {'verbose': True}

   :py:func:`argument<dollar_lambda.parsers.argument>` binds to positional arguments. If it comes first, it will
   think that ``"--verbose"`` is the expression that we want to bind to
   ``x``:

   >>> from dollar_lambda import argument
   >>> (argument("x") | flag("verbose")).parse_args("--verbose")
   {'x': '--verbose'}

:py:func:`nonpositional<dollar_lambda.parsers.nonpositional>` and :py:meth:`+<dollar_lambda.parsers.Parser.__add__>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
:py:func:`nonpositional<dollar_lambda.parsers.nonpositional>` takes a sequence of parsers as arguments and attempts
all permutations of them, returning the first permutations that is
successful:

>>> p = nonpositional(flag("verbose"), flag("quiet"))
>>> p.parse_args("--verbose", "--quiet")
{'verbose': True, 'quiet': True}
>>> p.parse_args("--quiet", "--verbose") # reverse order also works
{'quiet': True, 'verbose': True}

For just two parsers you can use
:py:meth:`+<dollar_lambda.parsers.Parser.__add__>` instead of :py:func:`nonpositional<dollar_lambda.parsers.nonpositional>`:

>>> p = flag("verbose") + flag("quiet")
>>> p.parse_args("--verbose", "--quiet")
{'verbose': True, 'quiet': True}
>>> p.parse_args("--quiet", "--verbose") # reverse order also works
{'quiet': True, 'verbose': True}

This will not cover all permutations for more than two parsers:

>>> p = flag("verbose") + flag("quiet") + option("x")
>>> p.parse_args("--verbose", "-x", "1", "--quiet")
usage: --verbose --quiet -x X
Expected '--quiet'. Got '-x'

To see why note the implicit parentheses:

>>> p = (flag("verbose") + flag("quiet")) + option("x")

In order to cover the case where ``-x`` comes between ``--verbose`` and
``--quiet``, use :py:meth:`nonpositional<dollar_lambda.parsers.nonpositional>`

>>> p = nonpositional(flag("verbose"), flag("quiet"), option("x"))
>>> p.parse_args("--verbose", "-x", "1", "--quiet") # works
{'verbose': True, 'x': '1', 'quiet': True}

Putting it all together
-----------------------

Let's recall the original example without the syntactic sugar:

>>> p = nonpositional(
...     (flag("verbose") | flag("quiet")).optional(),
...     option("x", type=int, help="the base"),
...     option("y", type=int, help="the exponent"),
... )
>>> def main(x, y, verbose=False, quiet=False):
...     print(dict(x=x, y=y, verbose=verbose, quiet=quiet))

As we've seen, ``(flag("verbose") | flag("quiet")).optional()`` succeeds
on either ``--verbose`` or ``--quiet`` or neither.

``option("x", type=int)`` succeeds on ``-x X``, where ``X`` is some
integer, binding that integer to the variable ``"x"``. Similarly for
``option("y", type=int)``.

:py:meth:`nonpositional<dollar_lambda.parsers.nonpositional>` takes the three parsers:

-  ``(flag("verbose") | flag("quiet")).optional()``
-  ``option("x", type=int)``
-  ``option("y", type=int)``

and applies them in every order, until some order succeeds.

Applying the syntactic sugar:

>>> @command(
...     parsers=dict(kwargs=(flag("verbose") | flag("quiet")).optional()),
...     help=dict(x="the base", y="the exponent"),
... )
...
... def main(x: int, y: int, **kwargs):
...     pass # do work

Here the ``parsers`` argument reserves a function argument (in this
case, ``kwargs``) for a custom parser (in this case,
``(flag("verbose") | flag("quiet")).optional()``) using our lower-level
syntax. The ``help`` argument assigns help text to the arguments (in
this case ``x`` and ``y``).
