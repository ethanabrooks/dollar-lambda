# Monad Argparse

### An alternative to `argparse` based on [Functional Pearls: Monadic Parsing in Haskell](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf)

Arguments


```python
from monad_argparse import argument

argument("name").parse_args("Ethan")
```




    [('name', 'Ethan')]



Flags


```python
from monad_argparse import Flag

Flag("verbose").parse_args("--verbose")
```




    [('verbose', True)]



Options


```python
from monad_argparse import Option

Option("value").parse_args("--value", "x")
```




    [('value', 'x')]



Failure


```python
Option("value").parse_args("--value")
```




    ArgumentError(token=None, description='Missing: argument for --value')



Alternatives (or "Sums")


```python
p = Flag("verbose") | Option("value")
p.parse_args("--verbose")
```




    [('verbose', True)]




```python
p.parse_args("--value", "x")
```




    [('value', 'x')]



Sequencing


```python
p = argument("first") >> argument("second")
p.parse_args("a", "b")
```




    [('first', 'a'), ('second', 'b')]



Variable arguments


```python
p = argument("many").many()
p.parse_args("a", "b")
```




    [('many', 'a'), ('many', 'b')]




```python
p = (Flag("verbose") | Flag("quiet")).many()
p.parse_args("--verbose", "--quiet")
```




    [('verbose', True), ('quiet', True)]




```python
p.parse_args("--quiet", "--verbose")
```




    [('quiet', True), ('verbose', True)]




```python
p.parse_args("--quiet")
```




    [('quiet', True)]




```python
p.parse_args("--quiet", "--quiet", "--quiet")
```




    [('quiet', True), ('quiet', True), ('quiet', True)]



Combine sequences and sums

from typing import Sequence, Union


```python
p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
p2 = argument("a")
p = p1 >> argument("a")
p.parse_args("--verbose", "value")
```




    [('verbose', True), ('a', 'value')]



What about doing this many times?


```python
p2 = p1.many()
p = p2 >> argument("a")
p.parse_args("--verbose", "value")
```




    [('verbose', True), ('a', 'value')]



`monad_argparse` of course defines a `nonpositional` utility for handling non-positional arguments as well. But seeing how easy it is to implement such a parser illustrates the power and flexibility of this library.
First let's introduce a simple utility function: `empty()`. This parser always returns the empty list.


```python
from monad_argparse import Parser

p = Parser.empty()
p.parse_args("any", "arguments")
```




    []



Using this function, we can define a parser for nonpositional arguments.


```python
from functools import reduce


def nonpositional(*parsers):
    if not parsers:
        return Parser.empty()

    def get_alternatives():
        """
        For each parser in `parsers`, this function returns a new parser,
        sequencing that parser with `nonpositional` applied to the rest of the parsers.
        """
        for i, head in enumerate(parsers):
            tail = [
                p for j, p in enumerate(parsers) if j != i
            ]  # get the parsers not including `head`
            yield head >> nonpositional(*tail)

    return reduce(
        lambda a, b: a | b, get_alternatives()
    )  # This applies the `|` operator to all the parsers in `get_alternatives()`
```

Let's test it:


```python
p = nonpositional(Flag("verbose"), Flag("debug"))
p.parse_args("--verbose", "--debug")
```




    [('verbose', True), ('debug', True)]




```python
p.parse_args("--debug", "--verbose")
```




    [('debug', True), ('verbose', True)]




```python
p = nonpositional(Flag("verbose"), Flag("debug"), argument("a"))
p.parse_args("--debug", "hello", "--verbose")
```




    [('debug', True), ('a', 'hello'), ('verbose', True)]
