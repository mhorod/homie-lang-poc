from tokens import *
from tree import *
import tree

from parsing.combinators import *
from parsing.builders import *
from parsing.helpers import *

def parse(tokens: List[Token]) -> ProgramType:
    result =  program_parser().run(TokenCursor(tokens))
    print(result.status)
    print(result.errors)
    return result.parsed

def program_parser():
    return (
        sequence()
            .then_parse(repeat(item_parser()))
            .then_drop(ExpectEof())
            .map(flatten)
            .map(Block)
    )

def item_parser():
    return enum_parser() | function_parser() | expr_parser() | fail("item")

def enum_parser():
    variants_parser = braced(interspersed_positive(enum_variant_parser(), kind(SymbolKind.Comma)))
    return (
        builder(EnumNodeBuilder)
            .then_drop(kind(KeywordKind.KwDis))
            .commit()
            .then_parse(EnumNodeBuilder.name, kind(NameKind.EnumName).map(get_text))
            .then_parse(EnumNodeBuilder.generic_names, optional(generic_params_parser(), []))
            .then_parse(EnumNodeBuilder.branches, variants_parser)
    )

def generic_params_parser():
    return bracketed(Interspersed(kind(NameKind.EnumName).map(get_text), kind(SymbolKind.Comma)))

def enum_variant_parser():
    return (
        builder(EnumBranchBuilder)
            .then_parse(EnumBranchBuilder.name, kind(NameKind.EnumName).map(get_text))
            .commit()
            .then_parse(EnumBranchBuilder.args, optional(args_parser(), []))
    )

def arg_parser():
    return (
        builder(ArgBuilder)
            .then_parse(ArgBuilder.name, ExpectKind(NameKind.VarName).map(get_text))
            .commit()
            .then_drop(kind(SymbolKind.Colon))
            .then_parse(ArgBuilder.type, type_parser())
    )

def args_parser():
    return parenthesized(interspersed(arg_parser(), kind(SymbolKind.Comma)))


def type_parser():        
    def make_function_type(args):
        if len(args) == 1:
            return args[0]
        elif len(args) == 2:
            return FunctionType(args[0], args[1])
        else:
            return FunctionType(args[0], make_function_type(args[1:]))

    def type_parser_impl(self):
        return Interspersed(enum_type_parser(self), ExpectKind(SymbolKind.Arrow)).map(make_function_type)

    return Recursive(type_parser_impl)


def enum_type_parser(type_parser=type_parser()):
    generic_args_parser = bracketed(Interspersed(type_parser, kind(SymbolKind.Comma)))

    return (
        builder(EnumTypeBuilder)
            .then_parse(EnumTypeBuilder.name, kind(NameKind.EnumName).map(get_text))
            .then_parse(EnumTypeBuilder.generics, optional(generic_args_parser, []))
    )

def function_parser():
    return_type_parser = (
        sequence()
        .then_drop(kind(SymbolKind.Arrow))
        .commit()
        .then_parse(type_parser())
        .map(extract)
    )
    return (
        builder(FunBuilder)
            .then_drop(kind(KeywordKind.KwFun))
            .commit()
            .then_parse(FunBuilder.name, kind(NameKind.VarName).map(get_text))
            .then_parse(FunBuilder.generics, optional(generic_params_parser(), []))
            .then_parse(FunBuilder.arguments, args_parser())
            .then_parse(FunBuilder.ret, optional(return_type_parser, None))
            .then_parse(FunBuilder.body, block_parser(expr_parser()))
    )

def fit_branch_parser(expr_parser):
    return (
        builder(FitBranchBuilder)
            .then_drop(not_parse(kind(DelimKind.CloseBrace)))
            .commit()
            .then_parse(FitBranchBuilder.left, pattern_parser())
            .then_drop(kind(SymbolKind.FatArrow))
            .then_parse(FitBranchBuilder.right, expr_parser)
    )

def fit_parser(expr_parser):
    branches_parser = braced(Interspersed(fit_branch_parser(expr_parser), kind(SymbolKind.Comma)))
    return (
        builder(FitBuilder)
            .then_drop(kind(KeywordKind.KwFit))
            .commit()
            .then_parse(FitBuilder.var, expr_parser)
            .then_parse(FitBuilder.branches, branches_parser)
    )

def ret_parser(expr_parser):
    return (
        sequence()
        .then_drop(kind(KeywordKind.KwRet))
        .commit()
        .then_parse(expr_parser)
        .map(extract)
        .map(Return)
    )

def let_parser(expr_parser):
    return (
        builder(LetBuilder)
            .then_drop(kind(KeywordKind.KwLet))
            .commit()
            .then_parse(LetBuilder.name, kind(NameKind.VarName).map(get_text))
            .then_drop(kind(SymbolKind.Equals))
            .then_parse(LetBuilder.value, expr_parser)
    )


def block_parser(expr_parser):
    single_expr_parser = (
        sequence()
            .then_parse(expr_parser)
            .commit()
            .then_drop(kind(SymbolKind.Semicolon))
    )
    return braced(repeat(single_expr_parser)).map(flatten).map(Block)

def expr_parser():
    def make_expr(parts):
        if len(parts) == 1:
            return parts[0]
        else:
            return Call(parts[0], parts[1:])
    def expr_parser_impl(self):
        return repeat_positive(expr_term_parser(self)).map(make_expr)
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
        | fail("expression")
        )

def enum_pattern_parser(pattern_parser):
    return (
        builder(EnumPatternBuilder)
            .then_parse(EnumPatternBuilder.name, kind(NameKind.EnumName).map(get_text))
            .commit()
            .then_parse(EnumPatternBuilder.args, repeat(enum_pattern_arg_parser(pattern_parser)))
    )

def enum_pattern_arg_parser(pattern_parser):
    variant_pattern_parser = kind(NameKind.EnumName).map(get_text).map(lambda name: tree.Pattern(name, []))
    return variant_pattern_parser | catchall_parser() | value_parser() | parenthesized(pattern_parser) | fail("pattern")

def pattern_parser():
    def pattern_parser_impl(self):
        return enum_pattern_parser(self) | catchall_parser() | value_parser() | parenthesized(self) | fail("pattern")
    return Recursive(pattern_parser_impl)

def catchall_parser():
    return ExpectKind(SymbolKind.Underscore).map(const(None))

def value_parser():
    return (
        kind(NumberKind.Integer).map(get_text).map(int).map(Value)
        | kind(StringKind.String).map(get_text).map(Value)
        | fail("value")
    )

def obj_path_parser():
    return (
        sequence()
            .then_parse(kind(NameKind.VarName).map(get_text))
            .then_parse(
                Repeat(
                    sequence()
                    .then_drop(kind(SymbolKind.Dot))
                    .commit()
                    .then_parse(kind(NameKind.VarName).map(get_text))
                ).map(flatten)
            )
            .map(flatten)
            .map(ObjPath)
    )

def type_path_parser():
    return interspersed_positive(enum_type_parser(), kind(SymbolKind.DoubleColon)).map(TypePath)