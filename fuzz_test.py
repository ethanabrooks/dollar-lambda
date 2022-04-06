import sys
from random import Random
from typing import NamedTuple, Optional

from hypothesis import given, register_random, settings
from hypothesis import strategies as st
from pytypeclass import List

from dollar_lambda import argument, defaults, flag, item, matches, option, parsers
from dollar_lambda.data_structures import Sequence
from dollar_lambda.parsers import Parser, nonpositional

MAX_RANDOM = 5
MAX_MANY = 3
MAX_NONPOSITIONAL = 3
MAX_MANY_INPUT = 3
MAX_LEAVES = 3


def st_input(type):
    if type is str:
        return st.text()
    elif type is int:
        return st.integers()
    elif type is float:
        return st.floats()
    elif type is bool:
        return st.booleans()
    elif type is Sequence:
        return st.text()


class StOutput(NamedTuple):
    parser: Parser
    inputs: List[str]
    repr: str


@st.composite
def st_argument(draw) -> StOutput:
    dest = draw(st.text())
    help = draw(st_optional_str)
    type = draw(st_type)
    return StOutput(
        parser=argument(dest=dest, help=help, type=type),
        inputs=[draw(st_input(type))],
        repr=f"argument(dest={repr(dest)}, help={help}, type={type.__name__})",
    )


@st.composite
def st_defaults(draw) -> StOutput:
    kwargs = draw(st.dictionaries(st.text(), st_any))
    return StOutput(parser=defaults(**kwargs), inputs=[], repr=f"defaults(**{kwargs})")


@st.composite
def st_done(_) -> StOutput:
    return StOutput(parser=Parser.done(), inputs=[], repr="Parser.done()")


@st.composite
def st_empty(_) -> StOutput:
    return StOutput(parser=Parser.empty(), inputs=[], repr="Parser.empty()")


@st.composite
def st_matches(draw) -> StOutput:
    s = draw(st.text())
    peak = draw(st.booleans())
    regex = False
    return StOutput(
        parser=matches(s=s, peak=peak, regex=regex),
        inputs=[s],
        repr=f"matches(s={repr(s)}, peak={peak}, regex={repr(regex)})",
    )


def st_flag_input(
    dest: str,
    default: Optional[bool] = None,
    short: bool = True,
    string: Optional[str] = None,
):
    def valid_flags():
        if string is None:
            yield [f"--{dest}" if len(dest) > 1 else f"-{dest}"]
        else:
            yield [string]
        if default is not None:
            yield []
        if string is None and short and len(dest) >= 1:
            yield [f"-{dest[0]}"]

    return st.sampled_from(list(valid_flags()))


@st.composite
def st_flag(draw) -> StOutput:
    dest = draw(st.text())
    default = draw(st.booleans() | st.none())
    help = draw(st_optional_str)
    short = draw(st.booleans())
    string = draw(st_optional_str)
    parser = flag(
        dest=dest, default=default, help=help, regex=False, short=short, string=string
    )
    inp = draw(st_flag_input(dest=dest, default=default, short=short, string=string))
    return StOutput(
        parser=parser,
        inputs=inp,
        repr=f"flag(dest={repr(dest)}, default={default}, help={repr(help)}, regex=False, short={short}, string={repr(string)})",
    )


@st.composite
def st_item(draw) -> StOutput:
    name = draw(st.text())
    usage_name = draw(st_optional_str)
    return StOutput(
        parser=item(name=name, usage_name=usage_name),
        inputs=[draw(st.text())],
        repr=f"item(name={repr(name)}, usage_name={repr(usage_name)})",
    )


@st.composite
def st_option(draw) -> StOutput:
    dest = draw(st.text())
    flag = draw(st_optional_str)
    default = draw(st.booleans() | st.none())
    help = draw(st_optional_str)
    short = draw(st.booleans())
    type = draw(st_type)
    parser = option(
        dest=dest,
        flag=flag,
        default=default,
        help=help,
        regex=False,
        short=short,
        type=type,
    )
    inp1 = draw(st_flag_input(dest=dest, default=default, short=short, string=flag))
    inp2 = [draw(st_input(type))] if inp1 else []
    return StOutput(
        parser=parser,
        inputs=inp1 + inp2,
        repr=f"option(dest={repr(dest)}, flag={repr(flag)}, default={default}, help={repr(help)}, regex=False, short={short}, type={type.__name__})",
    )


@st.composite
def st_many(draw, _st_parser_with_input) -> StOutput:
    parser, inputs, repr = draw(_st_parser_with_input)
    inputs = draw(st.lists(st.just(inputs), max_size=MAX_MANY_INPUT))
    inputs = [w for ws in inputs for w in ws]
    return StOutput(
        parser=parser.many(max=MAX_MANY),
        inputs=inputs,
        repr=f"{repr}.many(max={MAX_MANY})",
    )


@st.composite
def st_many1(draw, _st_parser_with_input) -> StOutput:
    parser, inputs, repr = draw(_st_parser_with_input)
    inputs = draw(st.lists(st.just(inputs), min_size=1, max_size=MAX_MANY_INPUT))
    inputs = [w for ws in inputs for w in ws]
    return StOutput(
        parser=parser.many1(max=MAX_MANY),
        inputs=inputs,
        repr=f"{repr}.many1(max={MAX_MANY})",
    )


@st.composite
def st_optional(draw, _st_parser_with_input) -> StOutput:
    parser, inputs, repr = draw(_st_parser_with_input)
    inputs = draw(st.sampled_from([inputs, []]))
    return StOutput(parser=parser.optional(), inputs=inputs, repr=f"{repr}.optional()")


@st.composite
def st_other_unary(draw, _st_parser_with_input) -> StOutput:
    parser, inputs, repr = draw(_st_parser_with_input)
    parser, repr = draw(
        st.sampled_from(
            [
                # (parser.fails(), f"{repr}.fails()"),
                (parser.ignore(), f"{repr}.ignore()"),
                (parser.wrap_help(), f"{repr}.wrap_help()"),
                (parser.optional(), f"{repr}.optional()"),
            ]
        )
    )
    return StOutput(parser=parser, inputs=inputs, repr=repr)


@st.composite
def st_nonpositional(draw, _st_parser_with_input):
    parser_with_input = draw(
        st.lists(_st_parser_with_input, max_size=MAX_NONPOSITIONAL)
    )
    if parser_with_input:
        parsers, inputs, reprs = zip(*parser_with_input)
    else:
        parsers = inputs = reprs = []
    repeated = draw(st.just(None) | _st_parser_with_input)
    repeated_repr = None
    repeated_inputs = []
    if repeated is not None:
        repeated, repeated_input, repeated_repr = repeated
        repeated_inputs = draw(
            st.lists(st.just(repeated_input), max_size=MAX_NONPOSITIONAL - len(inputs))
        )
    parser = nonpositional(*parsers, repeated=repeated, max=MAX_MANY)
    inputs = draw(st.permutations([*inputs, *repeated_inputs]))
    inputs = [i for ii in inputs for i in ii]
    repr = f"nonpositional({', '.join(reprs)}{', ' if reprs else ''}repeated={repeated_repr}, max={MAX_MANY})"
    return StOutput(parser=parser, inputs=inputs, repr=repr)


st_cs = st.lists(st.text()).map(Sequence)
st_optional_str = st.text() | st.none()
st_type = st.sampled_from([str, int, float, bool, Sequence])
st_any = st.deferred(lambda: st_hashable | st_list)  # | st_dict)
st_hashable = st.deferred(
    lambda: st.text() | st.integers() | st.booleans() | st.binary() | st_tuple
)
st_list = st.lists(st_any)
st_tuple = st.tuples(st_any)
st_simple_parser_with_input = st.deferred(
    lambda: st_argument()
    | st_defaults()
    | st_done()
    | st_empty()
    | st_matches()
    | st_item()
    | st_flag()
    | st_option()
)

st_parser_with_input = st.recursive(
    st_simple_parser_with_input,
    lambda p: st_many(p)
    | st_many1(p)
    | st_optional(p)
    | st_nonpositional(p)
    | st_other_unary(p),
    max_leaves=MAX_LEAVES,
)


@st.composite
def st_parser_with_random_input(draw):
    parser, _, repr = draw(st_parser_with_input)
    input = draw(st.lists(st.text(), max_size=MAX_RANDOM))
    return StOutput(parser=parser, inputs=input, repr=repr)


@settings(deadline=2000)
@given(st_parser_with_input)
def happy(parser_with_input):
    parser: Parser
    input: List[str]
    parser, input, repr = parser_with_input
    print(repr)
    result = parser.parse(Sequence(input)).get
    if isinstance(result, Exception):
        raise result


@settings(deadline=300)
@given(st_parser_with_random_input())
def sad(parser_with_random_input):
    parser, inputs, repr = parser_with_random_input
    print(repr)
    parser.parse_args(*inputs)


if __name__ == "__main__":
    sys.setrecursionlimit(10_000)
    parsers.TESTING = True
    parsers.PRINTING = False

    register_random(Random(0))

    if sys.argv[1] == "happy":
        happy()
    elif sys.argv[1] == "sad":
        sad()
