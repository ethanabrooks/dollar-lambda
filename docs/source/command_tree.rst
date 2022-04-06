:py:class:`CommandTree<dollar_lambda.decorators.CommandTree>` Tutorial
========================================================================

:py:class:`CommandTree <dollar_lambda.decorators.CommandTree>` has already shown up
in the
:ref:`Highlights section<DynamicDispatch>`
and in the :doc:`tutorial`. In this section we will give
a more thorough treatment, exposing some of the underlying logic and
covering all the variations in functionality that :py:class:`CommandTree<dollar_lambda.decorators.CommandTree>`
offers.

:py:class:`CommandTree<dollar_lambda.decorators.CommandTree>` draws inspiration from the
`Click <https://click.palletsprojects.com/>`_ library.
:py:meth:`CommandTree.subcommand <dollar_lambda.decorators.CommandTree.subcommand>` (discussed `here <#commandtree-subcommand>`__)
closely approximates the functionality described in the
`Commands and
Groups <https://click.palletsprojects.com/en/8.1.x/commands/#command>`__
section of the `Click <https://click.palletsprojects.com/>`_ documentation.

:py:meth:`CommandTree.command <dollar_lambda.decorators.CommandTree.command>`
-----------------------------------------------------------------------------

First let's walk through the use of the :py:meth:`CommandTree.command <dollar_lambda.decorators.CommandTree.command>`
decorator, one step at a time. First we define the object:

>>> from dollar_lambda import CommandTree
>>> tree = CommandTree()

Now we define at least one child function:

>>> @tree.command()
... def f1(a: int):
...     print(dict(f1=dict(a=a)))

:py:meth:`CommandTree.command <dollar_lambda.decorators.CommandTree.command>` automatically converts the function arguments
into a parser. We can run the parser and pass its output to our function
``f1`` by calling ``tree``:

>>> tree("-h")
usage: -a A

At this point the parser takes a single option ``-a`` that binds an
``int`` to ``'a'``:

>>> tree("-a", "1")
{'f1': {'a': 1}}

Usually we would call ``tree`` with no arguments, and it would get its
input from ``sys.argv[1:]``.

>>> import sys
>>> sys.argv[1:] = ["-a", "1"] # simulate command line
>>> parsers.TESTING = False # unnecessary outside doctests
>>> tree()
{'f1': {'a': 1}}
>>> parsers.TESTING = True

Now let's add a second child function:

>>> @tree.command()
... def f2(b: bool):
...     print(dict(f2=dict(b=b)))

>>> tree("-h")
usage: [-a A | -b]

``tree`` will execute either ``f1`` or ``f2`` based on which of the
parsers succeeds. This will execute ``f1``:

>>> tree("-a", "1")
{'f1': {'a': 1}}

This will execute ``f2``:

>>> tree("-b")
{'f2': {'b': True}}

This fails:

>>> tree()
usage: [-a A | -b]
The following arguments are required: -a

Often in cases where there are alternative sets of argument like this,
there is also a set of shared arguments. We can define a parent function
to make our help text more concise and to allow the user to run the
parent function when the child arguments are not provided.

>>> tree = CommandTree()
...
>>> @tree.command()
... def f1(a: int): # this will be the parent function
...     return dict(f1=dict(a=a))

Now define a child function, ``g1``:

>>> @f1.command() # note f1, not tree
... def g1(a:int, b: bool):
...     print(dict(g1=dict(b=b)))

Make sure to include all the arguments of ``f1`` in ``g1`` or else
``g1`` will fail when it is invoked. In its current state, ``tree``
sequences the arguments of ``f1`` and ``g1``:

>>> tree("-h")
usage: -a A -b

As before we can define an additional child function to induce
alternative argument sets:

>>> @f1.command() # note f1, not tree
... def g2(a: int, c: str):
...     print(dict(g2=dict(c=c)))

Note that our usage message shows ``-a A`` preceding the brackets
because it corresponds to the parent function:

>>> tree("-h")
usage: -a A [-b | -c C]

To execute ``g1``, we give the ``-b`` flag:

>>> tree("-a", "1", "-b")
{'g1': {'b': True}}

To execute ``g2``, we give the ``-c`` flag:

>>> tree("-a", "1", "-c", "foo")
{'g2': {'c': 'foo'}}

Also, note that ``tree`` can have arbitrary depth:

>>> @g1.command() # h1 is a child of g1
... def h1(a: int, b: bool, d: float):
...     print(dict(h1=dict(d=d)))

Note the additional ``-d D`` argument on the left side of the ``|``
pipe:

>>> tree("-h")
usage: -a A [-b -d D | -c C]

That comes from the third argument of ``h1``.

:py:meth:`CommandTree.subcommand <dollar_lambda.decorators.CommandTree.subcommand>`
-------------------------------------------------------------------------------------

Often we want to explicitly specify which function to execute by naming
it on the command line. This would implement functionality similar to
:external:py:meth:`argparse.ArgumentParser.add_subparsers`
or
:external:py:class:`click.Group`.

For this we would use the :py:meth:`CommandTree.subcommand <dollar_lambda.decorators.CommandTree.subcommand>` decorator:

>>> tree = CommandTree()
...
>>> @tree.command()
... def f1(a: int):
...     print(dict(f1=dict(a=a)))
...
>>> @f1.subcommand() # note subcommand, not command
... def g1(a:int, b: bool):
...     print(dict(g1=dict(b=b)))
...
>>> @f1.subcommand() # again, subcommand, not command
... def g2(a: int, c: str):
...     print(dict(g2=dict(c=c)))

Now the usage message indicates that ``g1`` and ``g2`` are required
arguments:

>>> tree("-h")
usage: -a A [g1 -b | g2 -c C]

Now we would select g1 as follows:

>>> tree("-a", "1", "g1", "-b")
{'g1': {'b': True}}

And g2 as follows:

>>> tree("-a", "1", "g2", "-c", "foo")
{'g2': {'c': 'foo'}}

You can freely mix and match :py:meth:`CommandTree.subcommand <dollar_lambda.decorators.CommandTree.subcommand>`
and :py:meth:`CommandTree.command <dollar_lambda.decorators.CommandTree.command>`:

>>> tree = CommandTree()
...
>>> @tree.command()
... def f1(a: int):
...     print(dict(f1=dict(a=a)))
...
>>> @f1.subcommand()
... def g1(a:int, b: bool):
...     print(dict(g1=dict(b=b)))
...
>>> @f1.command() # note command, not subcommand
... def g2(a: int, c: str):
...     print(dict(g2=dict(c=c)))

Note that the left side of the pipe (corresponding to the ``g1``
function) requires a ``"g1"`` argument to run but the right side
(corresponding to the ``g2`` function) does not:

>>> tree("-h")
usage: -a A [g1 -b | -c C]
