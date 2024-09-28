from parsing.combinators import *
from tokens import *

def flatten(items):
    result = []
    for item in items:
        if isinstance(item, list):
            result += item
        else:
            result.append(item)
    return result

def get_text(token):
    return token.text

def extract(xs):
    return xs[0]

def nothing():
    return Nothing()

def const(c):
    return lambda _: c

def delimited(opening_kind, inner, closing_kind):
    return (
        sequence()
            .then_drop(kind(opening_kind))
            .commit()
            .then_parse(inner)
            .then_drop(kind(closing_kind))
            .map(extract)
    )

def parenthesized(inner):
    return delimited(DelimKind.OpenParen, inner, DelimKind.CloseParen)

def bracketed(inner):
    return delimited(DelimKind.OpenBracket, inner, DelimKind.CloseBracket)

def braced(inner):
    return delimited(DelimKind.OpenBrace, inner, DelimKind.CloseBrace)

def kind(token_kind):
    return ExpectKind(token_kind)

def sequence():
    return SequenceParser()

def optional(parser, default):
    return OptionalParser(parser, default)

def repeat(parser):
    return Repeat(parser)

def repeat_positive(parser):
    return Repeat(parser, minimum=1)

def builder(builder_constructor):
    return BuilderParser(builder_constructor)

def fail(message):
    return Fail(message)

def not_parse(parser):
    return Not(parser)


def interspersed(value_parser, separator_parser, trailing=True):
    return Interspersed(value_parser, separator_parser, trailing=trailing)


def interspersed_positive(value_parser, separator_parser, trailing=True):
    return Interspersed(value_parser, separator_parser, minimum=1, trailing=trailing)


def supply(supplier):
    return Supply(supplier)
