from tokens import *
from tree import *

from parsing.combinators import *
from parsing.helpers import *
from parsing.expressions import *

def parse(tokens: List[Token]) -> Result:
    return program_parser().run(TokenCursor(tokens))

def program_parser():
    return (
        sequence()
            .then_parse(repeat(item_parser()))
            .then_drop(kind(EofKind.Eof))
            .map(flatten)
            .map(ProgramNode)
    )

def item_parser():
    return enum_parser() | function_parser() | expr_parser() | fail("item")

def enum_parser():
    variants_parser = braced(interspersed_positive(dis_variant_parser(), kind(SymbolKind.Comma)))
    return (
        builder(DisNode.Builder)
            .then_drop(kind(KeywordKind.KwDis))
            .commit()
            .then_parse(DisNode.Builder.name, kind(NameKind.EnumName))
            .then_parse(DisNode.Builder.generics, optional(generic_params_parser(), []))
            .then_parse(DisNode.Builder.variants, variants_parser)
    )

def generic_params_parser():
    inner_parser = bracketed(interspersed_positive(kind(NameKind.EnumName), kind(SymbolKind.Comma)))
    return (
        builder(GenericParamsNode.Builder)
            .then_parse(GenericParamsNode.Builder.params, optional(inner_parser, []))
    )

def dis_variant_parser():
    return (
        builder(DisVariantNode.Builder)
            .then_parse(DisVariantNode.Builder.name, kind(NameKind.EnumName))
            .commit()
            .then_parse(DisVariantNode.Builder.args, optional(args_parser(), []))
    )

def arg_parser():
    return (
        builder(ArgNode.Builder)
            .then_parse(ArgNode.Builder.name, ExpectKind(NameKind.VarName))
            .commit()
            .then_drop(kind(SymbolKind.Colon))
            .then_parse(ArgNode.Builder.type, type_parser())
    )

def args_parser():
    return parenthesized(interspersed(arg_parser(), kind(SymbolKind.Comma)))


def type_parser():
    def make_function_type(args):
        if len(args) == 1:
            return args[0]
        else:
            return FunctionTypeNode(args[:-1], args[-1])

    def type_parser_impl(self):
        return interspersed_positive(dis_constructor_parser(self) | dis_type_parser(self) | fail("type"), ExpectKind(SymbolKind.Arrow)).map(make_function_type)

    return Recursive(type_parser_impl)

def generic_args_parser(type_parser=type_parser()):
    wildcard_parser = builder(WildcardTypeNode.Builder).then_drop(kind(SymbolKind.QuestionMark))
    return bracketed(interspersed_positive(wildcard_parser | type_parser, kind(SymbolKind.Comma)))

def dis_type_parser(type_parser=type_parser()):
    return (
        builder(DisTypeNode.Builder)
            .then_parse(DisTypeNode.Builder.name, kind(NameKind.EnumName))
            .then_parse(DisTypeNode.Builder.generics, optional(generic_args_parser(type_parser), []))
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
        builder(FunNode.Builder)
            .then_drop(kind(KeywordKind.KwFun))
            .commit()
            .then_parse(FunNode.Builder.name, kind(NameKind.VarName))
            .then_parse(FunNode.Builder.generics, generic_params_parser())
            .then_parse(FunNode.Builder.args, args_parser())
            .then_parse(FunNode.Builder.ret, optional(return_type_parser, None))
            .then_parse(FunNode.Builder.body, block_parser(expr_parser()))
    )

def fit_branch_parser(expr_parser):
    return (
        builder(FitBranchNode.Builder)
            .then_drop(not_parse(kind(DelimKind.CloseBrace)))
            .commit()
            .then_parse(FitBranchNode.Builder.left, pattern_parser())
            .then_drop(kind(SymbolKind.FatArrow))
            .then_parse(FitBranchNode.Builder.right, expr_parser)
    )

def fit_parser(expr_parser):
    branches_parser = braced(interspersed_positive(fit_branch_parser(expr_parser), kind(SymbolKind.Comma)))
    return (
        builder(FitNode.Builder)
            .then_drop(kind(KeywordKind.KwFit))
            .commit()
            .then_parse(FitNode.Builder.expr, expr_parser)
            .then_parse(FitNode.Builder.branches, branches_parser)
    )

def ret_parser(expr_parser):
    return (
        builder(RetNode.Builder)
            .then_drop(kind(KeywordKind.KwRet))
            .commit()
            .then_parse(RetNode.Builder.expr, expr_parser)
    )

def wrt_parser():
    return (
        sequence()
        .then_drop(kind(KeywordKind.KwWrt))
        .commit()
        .then_parse(kind(StringKind.String).map(get_text))
        .map(extract)
        .map(Write)
    )

def let_parser(expr_parser):
    return (
        builder(LetNode.Builder)
            .then_drop(kind(KeywordKind.KwLet))
            .commit()
            .then_parse(LetNode.Builder.name, kind(NameKind.VarName))
            .then_drop(kind(SymbolKind.Equals))
            .then_parse(LetNode.Builder.value, expr_parser)
    )


def block_parser(expr_parser):
    single_expr_parser = (
        sequence()
            .then_parse(expr_parser)
            .commit()
            .then_drop(kind(SymbolKind.Semicolon))
    )
    return (
        builder(BlockNode.Builder)
            .then_parse(BlockNode.Builder.statements, braced(repeat(single_expr_parser).map(flatten)))
    )
def expr_parser():
    def expr_parser_impl(self):
        return repeat_positive(operator_parser() | expr_term_parser(self) | fail("expression or operator")).and_then(make_expr)
    return Recursive(expr_parser_impl)


def operator_parser():
    def op(symbol, precedence, associativity):
        return (
            builder(OperatorNode.Builder)
                .then_parse(OperatorNode.Builder.name, kind(symbol))
                .then_parse(OperatorNode.Builder.precedence, supply(lambda: precedence))
                .then_parse(OperatorNode.Builder.associativity, supply(lambda: associativity))
        )

    return (
        op(SymbolKind.Dot, 0, Associativity.LEFT)
        | op(SymbolKind.Asterisk, 2, Associativity.LEFT)
        | op(SymbolKind.Plus, 3, Associativity.LEFT)
        | op(SymbolKind.Equals, 4, Associativity.LEFT)
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
        | dis_constructor_parser()
        | wrt_parser()
        | fail("expression")
        )

def fun_instantiation_parser():
    return (
        builder(FunInstNode.Builder)
            .then_parse(FunInstNode.Builder.name, kind(NameKind.VarName))
            .then_parse(FunInstNode.Builder.generics, generic_args_parser())
    )

def var_parser():
    return builder(VarNode.Builder).then_parse(VarNode.Builder.name, kind(NameKind.VarName))

def enum_pattern_parser(pattern_parser):
    return (
        builder(PatternNode.Builder)
            .then_parse(PatternNode.Builder.name, kind(NameKind.EnumName))
            .commit()
            .then_parse(PatternNode.Builder.args, repeat(enum_pattern_arg_parser(pattern_parser)))
    )

def enum_pattern_arg_parser(pattern_parser):
    return variant_pattern_parser() | catchall_parser() | value_parser() | parenthesized(pattern_parser) | fail("pattern")

def variant_pattern_parser():
    return (
        builder(PatternNode.Builder)
            .then_parse(PatternNode.Builder.name, kind(NameKind.EnumName))
            .then_parse(PatternNode.Builder.args, supply(list))
    )


def pattern_parser():
    def pattern_parser_impl(self):
        return enum_pattern_parser(self) | catchall_parser() | value_parser() | parenthesized(self) | fail("pattern")
    return Recursive(pattern_parser_impl)

def catchall_parser():
    return ExpectKind(SymbolKind.Underscore).map(const(None))

def value_parser():
    return (
        builder(ValueNode.Builder)
        .then_parse(ValueNode.Builder.token, kind(NumberKind.Integer) | kind(StringKind.String) | fail("value"))
    )

def dis_constructor_parser(type_parser=type_parser()):
    return (
        builder(DisConstructorNode.Builder)
            .then_parse(DisConstructorNode.Builder.name, kind(NameKind.EnumName))
            .then_parse(DisConstructorNode.Builder.generics, optional(generic_args_parser(type_parser), []))
            .then_drop(kind(SymbolKind.DoubleColon))
            .commit()
            .then_parse(DisConstructorNode.Builder.variant_name, kind(NameKind.EnumName))
    )
