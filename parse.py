from tokens import *
from tree import *
import tree

from combinators import *

def parse(tokens: List[Token]) -> ProgramType:
    result =  program_parser().run(TokenCursor(tokens))
    print(result.status)
    print(result.errors)
    return result.parsed.value

def flatten(items):
    result = []
    for item in items:
        if isinstance(item, list):
            result += item
        else:
            result.append(item)
    return result

def make(constructor):
    def f(parts):
        return constructor(*parts)
    return f

def get_text(token):
    return token.text

def program_parser():
    return (Repeat(item_parser()) + ExpectEof()) & flatten & Block

def delimited(opening_kind, inner, closing_kind):
    return (Drop(ExpectKind(opening_kind)) >> (inner + Drop(ExpectKind(closing_kind)))) & (lambda result: result[0][0])

def parenthesized(inner):
    return delimited(DelimKind.OpenParen, inner, DelimKind.CloseParen)

def bracketed(inner):
    return delimited(DelimKind.OpenBracket, inner, DelimKind.CloseBracket)

def braced(inner):
    return delimited(DelimKind.OpenBrace, inner, DelimKind.CloseBrace)

def item_parser():
    return enum_parser() | function_parser() | expr_parser()

def enum_parser():
    return Drop(ExpectKind(KeywordKind.KwDis)) >> (
        ExpectKind(NameKind.EnumName) 
        + (Optional(generic_params_parser(), []) & flatten)
        + Drop(ExpectKind(DelimKind.OpenBrace))
        + Interspersed(enum_variant_parser(), ExpectKind(SymbolKind.Comma))
        + Drop(ExpectKind(DelimKind.CloseBrace))
    ) & flatten & make_enum

def generic_params_parser():
    return bracketed(Interspersed(
        ExpectKind(NameKind.EnumName) & get_text, 
        ExpectKind(SymbolKind.Comma)))

def make_enum(args):
    [name, generics, branches] = args 
    generic_names = [param for param in generics]
    return EnumNode(name.text, generic_names, branches)

def enum_variant_parser():
    return (ExpectKind(NameKind.EnumName) + (
        Optional(
            parenthesized(
                Interspersed(
                    ExpectKind(NameKind.VarName) + Drop(ExpectKind(SymbolKind.Colon)) + type_parser(),
                    ExpectKind(SymbolKind.Comma)
                )
            ),
            []
        )
    )) & make_enum_branch

def make_enum_branch(args):
    [name, branch_args] = args
    branch_args = [
        Arg(arg[0].text, arg[1]) for arg in branch_args
    ]
    return EnumBranch(name.text, branch_args)

def type_parser():        
    def type_parser_impl(self):
        return Interspersed(enum_type_parser(self), ExpectKind(SymbolKind.Arrow)) & make_function_type
    return Recursive(type_parser_impl)


def enum_type_parser(type_parser=type_parser()):
    return ExpectKind(NameKind.EnumName) + Optional(
                (Drop(ExpectKind(DelimKind.OpenBracket)) +
                Interspersed(type_parser, ExpectKind(SymbolKind.Comma)) +
                Drop(ExpectKind(DelimKind.CloseBracket))) & flatten,
                []
            ) & make_enum_type


def make_enum_type(args):
    [name, generics] = args
    return EnumType(name.text, generics)


def make_function_type(args):
    if len(args) == 1:
        return args[0]
    elif len(args) == 2:
        return FunctionType(args[0], args[1])
    else:
        return FunctionType(args[0], make_function_type(args[1:]))

def make_args(args):
    return [Arg(name.text, tp) for [name, tp] in args]

def arg_parser():
    return Interspersed(
        ExpectKind(NameKind.VarName) + Drop(ExpectKind(SymbolKind.Colon)) + type_parser(),
        ExpectKind(SymbolKind.Comma)
    ) & make_args

def function_parser():
    return Drop(ExpectKind(KeywordKind.KwFun)) >> (
        (ExpectKind(NameKind.VarName) & (lambda token: token.text))
        + Optional(generic_params_parser(), [])
        + parenthesized(arg_parser())
        + Drop(ExpectKind(SymbolKind.Arrow))
        + type_parser()
        + block_parser(expr_parser()) # TODO: braced? not braced?
    ) & flatten & make(Fun)

def fit_branch_parser(expr_parser):
    return (
        (pattern_parser() + Drop(ExpectKind(SymbolKind.FatArrow)))
        >> expr_parser
    ) & flatten & make(FitBranch)

def fit_parser(expr_parser):
    return Drop(ExpectKind(KeywordKind.KwFit)) >> (
        expr_parser
        + braced(Interspersed(fit_branch_parser(expr_parser), Drop(ExpectKind(SymbolKind.Comma))))
    ) & flatten & make(Fit)

def ret_parser(expr_parser):
    return (Drop(ExpectKind(KeywordKind.KwRet)) >> expr_parser) & make(Return)

def let_parser(expr_parser):
    return (Drop(ExpectKind(KeywordKind.KwLet)) >> ((ExpectKind(NameKind.VarName) & get_text)
        + Drop(ExpectKind(SymbolKind.Equals))
        + expr_parser
    )) & flatten & make(Let)

def block_parser(expr_parser):
    return braced(
        Repeat(expr_parser >> Drop(ExpectKind(SymbolKind.Semicolon))) & flatten
    ) & Block

def expr_parser():
    def make_expr(parts):
        if len(parts) == 1:
            return parts[0]
        else:
            return Call(parts[0], parts[1:])
    def expr_parser_impl(self):
        return (expr_term_parser(self) + Repeat(expr_term_parser(self))) & flatten & make_expr
    return Recursive(expr_parser_impl)


def expr_term_parser(expr_parser):
    return (
        value_parser()
        | ret_parser(expr_parser)
        | fit_parser(expr_parser)
        | let_parser(expr_parser)
        | parenthesized(expr_parser)
        | value_parser()
        | obj_path_parser()
        | type_path_parser()
        )

def pattern_term_parser(pattern_parser):
    return catchall_parser() | value_parser() | (ExpectKind(NameKind.EnumName) & (lambda token: tree.Pattern(token.text, []))) | parenthesized(pattern_parser)

def pattern_parser():
    def make_pattern(parts):
        if len(parts) == 1:
            return parts[0]
        else:
            return tree.Pattern(parts[0].name, parts[1:])
    def pattern_parser_impl(self):
        return Repeat(pattern_term_parser(self)) & make_pattern

    return Recursive(pattern_parser_impl)

def catchall_parser():
    return ExpectKind(SymbolKind.Underscore) & (lambda _: None)

def value_parser():
    return (
        (ExpectKind(NumberKind.Integer) & (lambda token: Value(int(token.text)))) |
        (ExpectKind(StringKind.String) & (lambda token: Value(token.text)))
    )

def obj_path_parser():
    def make_obj_path(parts):
        return ObjPath([part.text for part in parts])
    path_parser = ExpectKind(NameKind.VarName) + Repeat(Drop(ExpectKind(SymbolKind.Dot)) + ExpectKind(NameKind.VarName))
    return path_parser & flatten & flatten & make_obj_path

def type_path_parser():
    def make_type_path(parts):
        return TypePath([part for part in parts])
    path_parser = Interspersed(enum_type_parser(), Drop(ExpectKind(SymbolKind.DoubleColon)))
    return path_parser & flatten & make_type_path