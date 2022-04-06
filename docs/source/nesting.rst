Nesting and grouping output
============================

.. _Nesting:

Nesting output with the ``.`` character
-----------------------------------------

By default introducing a ``.`` character into the name of an
:py:func:`argumnet <dollar_lambda.parsers.argument>`, :py:func:`option <dollar_lambda.parsers.option>`,
or :py:func:`flag <dollar_lambda.parsers.flag>` will induce nested output:

>>> from dollar_lambda import argument, flag, option
>>> argument("a.b", type=int).parse_args("1")
{'a': {'b': 1}}
>>> option("a.b", type=int).parse_args("--a.b", "1")
{'a': {'b': 1}}
>>> flag("a.b").parse_args("--a.b")
{'a': {'b': True}}

This mechanism handles collisions:

>>> from dollar_lambda import flag
>>> (flag("a.b") >> flag("a.c")).parse_args("--a.b", "--a.c")
{'a': {'b': True, 'c': True}}

even when mixing nested and unnested output:

>>> (flag("a") >> flag("a.b")).parse_args("-a", "--a.b")
{'a': [True, {'b': True}]}

It can also go arbitrarily deep:

>>> (flag("a.b.c") >> flag("a.b.d")).parse_args("-a.b.c", "-a.b.d")
{'a': {'b': {'c': True, 'd': True}}}

This behavior can always be disabled by setting ``nesting=False`` (or
just not using ``.`` in the name).

Grouping with the :py:func:`@parser <dollar_lambda.decorators.parser>` decorator
------------------------------------------------------------------------------------

A common situation when processing command line arguments is to send one subset of
arguments to one function, another subset to another, and so on.
`$λ` provides a convenient syntax for doing this.

Deriving a subset of arguments from a function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Suppose ``f`` is the function that will require some subset of our command line arguments:

>>> from dollar_lambda import parser
>>> @parser()
... def f(a: int, b: float):
...     print("Running f with:", dict(a=a, b=b))

A function wrapped with :py:func:`@parser <dollar_lambda.decorators.parser>` can still be called
like normal:

>>> f(1, 2.0)
Running f with: {'a': 1, 'b': 2.0}

However, it now has a ``.parser`` property:

>>> f.parser.parse_args("-a", "1", "-b", "2.0")
{'a': 1, 'b': 2.0}

This parser can be used to easily feed arguments to ``f`` as follows:

>>> from dollar_lambda import command
>>> @command(parsers=dict(kwargs=f.parser))
... def main(c: bool, **kwargs: dict):
...     print("Running main with", dict(c=c))
...     f(**kwargs)
...
>>> main("-a", "1", "-b", "2.0", "-c")
Running main with {'c': True}
Running f with: {'a': 1, 'b': 2.0}

Deriving subsets from multiple functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Suppose we have a second function, ``f2``:

>>> @parser()
... def f2(c: bool):
...     print("Running f2 with", dict(c=c))

This is how we can bind both the ``f`` arguments and the ``f2`` arguments to the ``kwargs``
argument:

>>> @command(parsers=dict(kwargs=[f.parser, f2.parser]))  # note the list
... def main(d: bool, **kwargs: dict):
...     print("Running main with", dict(d=d))
...     f(kwargs["a"], kwargs["b"])
...     f2(kwargs["c"])
...
>>> main("-a", "1", "-b", "2.0", "-c", "-d")
Running main with {'d': True}
Running f with: {'a': 1, 'b': 2.0}
Running f2 with {'c': True}


Note that we can rearrange the order of command line arguments as long as we don't
break up the function groups:

>>> main("-d", "-c", "-a", "1", "-b", "2.0")  # works
Running main with {'d': True}
Running f with: {'a': 1, 'b': 2.0}
Running f2 with {'c': True}
>>> main("-d", "-a", "1", "-c", "-b", "2.0")  # fails because "-c" is between "-a" and "-b"
usage: -d -a A -b B -c
Expected '-b'. Got '-c'

Nesting :py:func:`@parser <dollar_lambda.decorators.parser>` output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the functions have a lot of arguments, unpacking them like this will be cumbersome.
Moreover, if they have conflicting namespaces, we will need another solution.
To this end, we can use the nesting functionality that we discussed :ref:`earlier <nesting>`.

Let's add an argument to the :py:func:`@parser <dollar_lambda.decorators.parser>` decorator:

>>> @parser("args")
... def f(a: int, b: float):
...     print("Running f with:", dict(a=a, b=b))

Now the parser output will be nested:

>>> f.parser.parse_args("--args.a", "1", "--args.b", "2.0")
{'args': {'a': 1, 'b': 2.0}}

This allows us to easily group arguments for multiple functions, even with
conflicting namespaces:

>>> @parser("args2")
... def f2(a: bool):
...     print("Running f2 with:", dict(a=a))
...
>>> @command(parsers=dict(args=f.parser, args2=f2.parser))
... def main(args: dict, args2: dict, a: bool):
...     print("Running main with", dict(a=a))
...     f(**args)
...     f2(**args2)
...
>>> main("-h")
usage: --args.a ARGS.A --args.b ARGS.B --args2.a -a
>>> main("--args.a", "1", "--args.b", "2.0", "--args2.a", "-a")
Running main with {'a': True}
Running f with: {'a': 1, 'b': 2.0}
Running f2 with: {'a': True}
