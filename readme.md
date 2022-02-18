Based on [Monadic Parser Combinators](https://www.cs.nott.ac.uk/~pszgmh/monparsing.pdf) by Graham Hutton and Erik Meijer.

Arguments


```python
from parser import Argument

print(Argument("name").parse_args(["Ethan"]))
```

    ('name', 'Ethan')


Flags


```python
from parser import Flag

print(Flag("verbose").parse_args(["--verbose"]))
```

    ('verbose', True)


Options


```python
from parser import Option

print(Option("value").parse_args(["--value", "x"]))
```

    ('value', 'x')


Failure


```python
print(Option("value").parse_args(["--value"]))
```

    []


Alternatives (or "Sums")


```python
p = Flag("verbose") | Option("value")
print(p.parse_args(["--verbose"]))
```

    ('verbose', True)



```python
print(p.parse_args(["--value", "x"]))
```

    ('value', 'x')


Sequencing


```python
p = Argument("first") >> Argument("second")
print(p.parse_args(["a", "b"]))
```

    [('first', 'a'), ('second', 'b')]


This is shorthand for the following:


```python
from parser import Parser

def g():
    x1 = yield Argument('first')
    x2 = yield Argument('second')
    yield Parser.ret([x1, x2])

print(Parser.do(g).parse_args(["a", "b"]))
```

    [('first', 'a'), ('second', 'b')]


Variable arguments


```python
p = Argument("many").many()
print(p.parse_args(["a", "b"]))
```

    [('many', 'a'), ('many', 'b')]



```python
p = (Flag("verbose") | Flag("quiet")).many()
print(p.parse_args(["--verbose", "--quiet"]))
```

    [('verbose', True), ('quiet', True)]



```python
print(p.parse_args(["--quiet", "--verbose"]))
```

    [('quiet', True), ('verbose', True)]



```python
print(p.parse_args(["--quiet"]))
```

    [('quiet', True)]



```python
print(p.parse_args(["--quiet", "--quiet", "--quiet"]))
```

    [('quiet', True), ('quiet', True), ('quiet', True)]


Combine sequences and sums


```python
p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
p = p1 >> Argument("a")
print(p.parse_args(["--verbose", "value"]))
```

    [('verbose', True), ('a', 'value')]


What about doing this many times?


```python
p2 = p1.many()
p = p2 >> Argument("a")
print(p.parse_args(["--verbose", "value"]))
```

    [[('verbose', True)], ('a', 'value')]


The result is awkwardly nested. To deal with this, we use `Parser.do`:


```python
def g():
    xs = yield p2
    x = yield Argument('a')
    yield Parser.ret(xs + [x])

print(Parser.do(g).parse_args(["--verbose", "--quiet", "value"]))
```

    [('verbose', True), ('quiet', True), ('a', 'value')]


A common pattern is to alternate checking for positional arguments with checking for non-positional arguments:


```python
def g():
    xs1 = yield p2
    x1 = yield Argument('first')
    xs2 = yield p2
    x2 = yield Argument('second')
    xs3 = yield p2
    yield Parser.ret(xs1 + [x1] + xs2  + [x2] + xs3)

print(Parser.do(g).parse_args(["a", "--verbose", "b", "--quiet"]))
```

    [('first', 'a'), ('verbose', True), ('second', 'b'), ('quiet', True)]


A simpler way to do this is with the `interleave` method:


```python
def g():
    return (Flag("verbose") | Flag("quiet") | Flag("yes")).interleave(
        Argument('first'), Argument('second'))

print(Parser.do(g).parse_args(["a", "--verbose", "b", "--quiet"]))
```

    [('first', 'a'), ('verbose', True), ('second', 'b'), ('quiet', True)]


or `build`:


```python
print(Parser.build(
    Flag("verbose") |
    Flag("quiet") |
    Flag("yes"),
    Argument('first'),
    Argument('second')
).parse_args(["a", "--verbose", "b", "--quiet"]))
```

    [('first', 'a'), ('verbose', True), ('second', 'b'), ('quiet', True)]

