Ignoring arguments
==================

There may be cases in which a user wants to provide certain arguments on
the command line that ``$λ`` should ignore (not return in the output of
``Parser.parse_args`` or pass to the a decorated function). Suppose we
wish to ignore any arguments starting with the ``--config-`` prefix:

>>> from dollar_lambda import flag, option
>>> regex = r"config-\S*"
>>> config_parsers = flag(regex) | option(regex)

In the case of ordered arguments, we simply use the ``ignore`` method:

>>> p = flag("x") >> config_parsers.ignore() >> flag("y")

This will ignore any argument that starts with ``--config-`` and comes
between ``x`` and ``y``:

>>> p.parse_args("-x", "-config-foo", "-y")
{'x': True, 'y': True}

Because of the way we defined ``config_parsers``, this also works with
:py:func:`option<dollar_lambda.option>`:

>>> p.parse_args("-x", "-config-bar", "1", "-y")
{'x': True, 'y': True}

In the case of :py:func:`nonpositional<dollar_lambda.nonpositional>` arguments, use the ``repeated`` keyword:

>>> from dollar_lambda import nonpositional
>>> p = nonpositional(flag("x"), flag("y"), repeated=config_parsers.ignore())

Now neither ``config-foo`` nor ``config-bar`` show up in the output:

>>> p.parse_args("-x", "-y", "-config-foo", "-config-bar", "1")
{'x': True, 'y': True}

This works regardless of order:

>>> p.parse_args("-config-baz", "1", "-y", "-config-foz", "-x")
{'y': True, 'x': True}

And no matter how many matches are found:

>>> p.parse_args(
...     "-config-foo",
...     "1",
...     "-config-bar",
...     "-y",
...     "-config-baz",
...     "2",
...     "-x",
...     "-config-foz",
... )
{'y': True, 'x': True}

The same technique can be used with the :py:class:`@command<dollar_lambda.command>` decorator:

>>> from dollar_lambda import command
>>> @command(repeated=config_parsers.ignore())
... def f(x: bool, y: bool):
...     print(dict(x=x, y=y))
...
>>> f("-x", "-y", "-config-foo", "-config-bar", "1")
{'x': True, 'y': True}

and similarly with :py:class:`CommandTree<dollar_lambda.CommandTree>`.
