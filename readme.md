# Monad Argparse

### An alternative to `monad_argparse` based on [Functional Pearls: Monadic Parsing in Haskell](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf)

Arguments


```python
from monad_argparse import argument

argument("name").parse_args("Ethan")
```




    {'name': 'Ethan'}



Flags


```python
from monad_argparse import flag

flag("verbose").parse_args("--verbose")
```




    {'verbose': True}



Options


```python
from monad_argparse import option

option("value").parse_args("--value", "x")
```




    {'value': 'x'}



Failure


```python
from monad_argparse import Parser

option("value").parse_args("--value")
```

    usage: --value VALUE
    The following arguments are required: VALUE


Alternatives (or "Sums")


```python
p = flag("verbose") | option("value")
p.parse_args("--verbose")
```




    {'verbose': True}




```python
p.parse_args("--value", "x")
```




    {'value': 'x'}



Sequencing


```python
p = argument("first") >> argument("second")
p.parse_args("a", "b")
```




    {'first': 'a', 'second': 'b'}



Variable arguments


```python
p = argument("many").many()
p.parse_args("a", "b")
```




    {'many': 'b'}






```python
p = (flag("verbose") | flag("quiet")).many()
p.parse_args("--verbose", "--quiet")
```




    {'verbose': True, 'quiet': True}






```python
p.parse_args("--quiet", "--verbose")
```




    {'quiet': True, 'verbose': True}






```python
p.parse_args("--quiet")
```




    {'quiet': True}






```python
p.parse_args("--quiet", "--quiet", "--quiet")
```




    {'quiet': True}



Combine sequences and sums


```python
p1 = flag("verbose") | flag("quiet") | flag("yes")
p2 = argument("a")
p = p1 >> argument("a")
p.parse_args("--verbose", "value")
```




    {'verbose': True, 'a': 'value'}



What about doing this many times?


```python
p2 = p1.many()
p = p2 >> argument("a")
p.parse_args("--verbose", "value")
```




    {'verbose': True, 'a': 'value'}



`monad_monad_argparse` of course defines a `nonpositional` utility for handling non-positional arguments as well. But seeing how easy it is to implement such a parser illustrates the power and flexibility of this library.
First let's introduce a simple utility function: `empty()`. This parser always returns the empty list.


```python
from monad_argparse import empty

p = empty()
p.parse_args("any", "arguments")
import operator
```

Using this function, we can define a parser for nonpositional arguments.



```python
from functools import reduce


def nonpositional(*parsers):
    if not parsers:
        return empty()

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

    return reduce(operator.or_, get_alternatives())
```

Let's test it:


```python
from monad_argparse import done

p = (
    nonpositional(flag("verbose", default=False), flag("debug", default=False))
    >> done()
)
p.parse_args("--verbose", "--debug")
```




    {'verbose': True, 'debug': True}






```python
p.parse_args("--debug", "--verbose")
```




    {'debug': True, 'verbose': True}




```python
p.parse_args("--debug")
```




    {'verbose': False, 'debug': True}




```python
p.parse_args("--verbose")
```




    {'verbose': True, 'debug': False}






```python
p = nonpositional(flag("verbose"), flag("debug"), argument("a"))
p.parse_args("--debug", "hello", "--verbose")
```




    {'debug': True, 'a': 'hello', 'verbose': True}
