from tokens import *
from tree import *
import tree
import sys

from parsing.combinators import *
from parsing.builders import *
from parsing.helpers import *
from parsing.expressions import *

def parse(tokens: List[Token]) -> ProgramType:
    result =  program_parser().run(TokenCursor(tokens))
    print(result, file=sys.stderr)
    return result.parsed

def program_parser():
    return (
        sequence()
            .then_parse(repeat(item_parser()))
            .then_drop(ExpectEof())
            .map(flatten)
            .map(ProgramType)
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
        else:
            return FunctionType(args[:-1], args[-1])

    def type_parser_impl(self):
        return interspersed_positive(enum_constructor_parser(self) | enum_type_parser(self) | fail("enum type"), ExpectKind(SymbolKind.Arrow)).map(make_function_type)

    return Recursive(type_parser_impl)

def generic_args_parser(type_parser=type_parser()):
    wildcard_parser = kind(SymbolKind.QuestionMark).replace(WildcardType())
    return bracketed(Interspersed(wildcard_parser | type_parser, kind(SymbolKind.Comma)))

def enum_type_parser(type_parser=type_parser()):
    return (
        builder(EnumTypeBuilder)
            .then_parse(EnumTypeBuilder.name, kind(NameKind.EnumName).map(get_text))
            .then_parse(EnumTypeBuilder.generics, optional(generic_args_parser(type_parser), []))
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
    branches_parser = braced(interspersed_positive(fit_branch_parser(expr_parser), kind(SymbolKind.Comma)))
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
    def expr_parser_impl(self):
        return repeat_positive(operator_parser() | expr_term_parser(self) | fail("expression or operator")).and_then(make_expr)
    return Recursive(expr_parser_impl)


def operator_parser():
    return (
        kind(SymbolKind.Dot).replace(Operator(SymbolKind.Dot, 0, Associativity.LEFT))
        | kind(SymbolKind.Plus).replace(Operator(SymbolKind.Plus, 3, Associativity.LEFT))
        | kind(SymbolKind.Asterisk).replace(Operator(SymbolKind.Asterisk, 2, Associativity.LEFT))
    )

def expr_term_parser(expr_parser):
    return (
        value_parser()
        | ret_parser(expr_parser)
        | fit_parser(expr_parser)
        | let_parser(expr_parser)
        | parenthesized(expr_parser)
        | fun_instantiation_parser()
        | var_parser()
        | enum_constructor_parser()
        | fail("expression")
        )

def fun_instantiation_parser():
    return (
        builder(FunInstantiationBuilder)
            .then_parse(FunInstantiationBuilder.name, kind(NameKind.VarName).map(get_text))
            .then_parse(FunInstantiationBuilder.generics, generic_args_parser())
    )

def var_parser():
    return kind(NameKind.VarName).map(get_text).map(Var)

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

def enum_constructor_parser(type_parser=type_parser()):
    return (
        builder(EnumConstructorBuilder)
            .then_parse(EnumConstructorBuilder.enum_name, kind(NameKind.EnumName).map(get_text))
            .then_parse(EnumConstructorBuilder.generics, optional(generic_args_parser(type_parser), []))
            .then_drop(kind(SymbolKind.DoubleColon))
            .commit()
            .then_parse(EnumConstructorBuilder.variant_name, kind(NameKind.EnumName).map(get_text))
    )