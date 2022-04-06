Nesting output
==============

By default introducing a ``.`` character into the name of an
:py:func:`argumnet <dollar_lambda.parser.argument>`, :py:func:`option <dollar_lambda.parser.option>`,
or :py:func:`flag <dollar_lambda.parser.flag>` will induce nested output:

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
