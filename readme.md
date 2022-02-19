# Monad Argparse

### An alternative to `argparse` based on [Functional Pearls: Monadic Parsing in Haskell](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf)

Arguments


```python
from monad_argparse import Argument

Argument("name").parse_args("Ethan")
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




    RuntimeError('Item failed')



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
p = Argument("first") >> Argument("second")
p.parse_args("a", "b")
```




    [('first', 'a'), ('second', 'b')]



This is shorthand for the following:


```python
from monad_argparse import Parser


def g():
    x1 = yield Argument("first")
    x2 = yield Argument("second")
    yield Parser.return_(x1 + x2)


Parser.do(g).parse_args("a", "b")
```




    [('first', 'a'), ('second', 'b')]



Variable arguments


```python
p = Argument("many").many()
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


```python
p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
p = p1 >> Argument("a")
p.parse_args("--verbose", "value")
```




    [('verbose', True), ('a', 'value')]



What about doing this many times?


```python
p2 = p1.many()
p = p2 >> Argument("a")
p.parse_args("--verbose", "value")
```




    [('verbose', True), ('a', 'value')]



The result is awkwardly nested. To deal with this, we use `Parser.do`:


```python
def g():  # type: ignore[no-redef]
    xs = yield p2
    x = yield Argument("a")
    yield Parser.return_(xs + x)


Parser.do(g).parse_args("--verbose", "--quiet", "value")
```




    [('verbose', True), ('quiet', True), ('a', 'value')]



A common pattern is to alternate checking for positional arguments with checking for non-positional arguments:


```python
def g():  # type: ignore[no-redef]
    xs1 = yield p2
    x1 = yield Argument("first")
    xs2 = yield p2
    x2 = yield Argument("second")
    xs3 = yield p2
    yield Parser.return_(xs1 + x1 + xs2 + x2 + xs3)


Parser.do(g).parse_args("a", "--verbose", "b", "--quiet")
```




    [('first', 'a'), ('verbose', True), ('second', 'b'), ('quiet', True)]
