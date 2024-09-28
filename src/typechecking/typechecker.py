from typing import *
from tree import *
from copy import deepcopy
from error_reporting import *

from tokens import NumberKind, StringKind

from typechecking.types import *
from typechecking.subtyping import *
from typechecking.context import *
from typechecking.convert import *
from typechecking.errors import *

def typecheck(program):
    simple_types = {
        'Int' : SimpleType('Int'),
        'String': SimpleType('String'),
        'Void': SimpleType('Void')
    }
    typechecker = Typechecker(simple_types)
    typechecker.typecheck(program)
    return typechecker.ctx, typechecker.report


class Typechecker:
    def __init__(self, simple_types):
        self.ctx = TypingContext()
        self.ctx.simple_types = simple_types
        self.report = ErrorReport()
        self.type_converter = TypeConverter(self.report, self.ctx)

    def typecheck(self, tree):
        if isinstance(tree, ProgramNode):
            self.typecheck_program(tree)
        elif isinstance(tree, Write):
            return
        elif isinstance(tree, FitExprNode) or isinstance(tree, FitStatementNode):
            self.type_fit(tree)
        elif isinstance(tree, LetNode):
            ty = self.type_expr(tree.value)
            self.ctx.add_local_var(tree.name.text, ty)
        elif isinstance(tree, CallNode):
            self.type_call(tree)
        elif isinstance(tree, DisNode):
            pass
        elif isinstance(tree, FunNode):
            self.type_fun(tree)
        elif isinstance(tree, BlockNode):
            self.ctx.push()
            for statement in tree.statements:
                self.typecheck(statement)
            self.ctx.pop()
        elif isinstance(tree, RetNode):
            self.type_ret(tree)
        else:
            self.type_expr(tree)

    def typecheck_program(self, program: ProgramNode):
        dises = self.find_dis_declarations(program)
        self.ctx.dises = dises
        functions = self.find_function_declarations(program)
        self.ctx.functions = functions

        for item in program.items:
            self.typecheck(item)

    def type_var(self, var: VarNode):
        name = var.name.text
        if self.ctx.has_local_var(name):
            return self.ctx.get_local_var_type(name)
        if self.ctx.has_function(name):
            fun_ty = self.ctx.get_function(name)
            if isinstance(fun_ty, ErrorTy):
                return fun_ty
            elif fun_ty.generic_arg_count == 0:
                return fun_ty.ty
            else:
                fun_node = self.ctx.fun_nodes[name][0]
                expected = len(fun_node.generics.params)
                actual = 0
                self.report.error(fun_generic_arguments_mismatch(var.location, fun_node, expected, actual))
                return ErrorTy()
        else:
            self.report.error(unknown_variable(var))
            return ErrorTy()

    def type_let(self, let: LetNode):
        var_type = self.type_expr(let.value)
        self.ctx.add_local_var(let.name, var_type)
        return None

    def type_fun(self, fun: FunNode):
        fun_ty = self.get_fun_type(fun)
        if isinstance(fun_ty, ErrorTy):
            return
        self.ctx.push()
        self.ctx.add_generics(fun.generics)
        for arg, arg_ty in zip(fun.args, fun_ty.arg_types):
            self.ctx.add_local_var(arg.name.text, arg_ty)
        self.typecheck(fun.body)
        self.ctx.pop()

    def type_function_instantiation(self, fun_inst: FunInstNode):
        name = fun_inst.name.text
        if self.ctx.has_function(name):
            decl = self.ctx.get_function(name)
            generics = self.convert_generics(fun_inst.generics)
            if isinstance(decl, ErrorTy) or any(isinstance(ty, ErrorTy) for ty in generics):
                return ErrorTy()
            else:
                return self.instantiate_function(fun_inst, decl, generics)
        else:
            self.report.error(unknown_function(fun_inst))
            self.convert_generics(fun_inst.generics)
            return ErrorTy()

    def convert_generics(self, generics: List[TypeNode]):
        converted_generics = []
        for ty in generics:
            converted = self.type_converter.convert_type(ty)
            converted_generics.append(converted)
        return converted_generics

    def type_value(self, expr: ValueNode):
        if isinstance(expr.token.kind, NumberKind):
            return SimpleType('Int')
        elif isinstance(expr.token.kind, StringKind):
            return SimpleType('String')
        else:
            raise Exception(f"Unsupported value type: {type(expr.val)}")

    def type_dis_constructor(self, expr: DisConstructorNode):
        if not self.ctx.has_dis(expr.name.text):
            self.report.error(dis_does_not_exist(expr.name.location, expr.name.text))
            return ErrorTy()
        dis_decl = self.ctx.get_dis(expr.name.text)

        if dis_decl.generic_arg_count != len(expr.generics):
            expected_count = dis_decl.generic_arg_count
            actual_count = len(expr.generics)
            dis_node = self.ctx.dis_nodes[expr.name.text][0]
            self.report.error(dis_generic_arguments_mismatch(expr.location, dis_node, expected_count, actual_count))
            return ErrorTy()

        if not dis_decl.has_variant(expr.variant_name.text):
            self.report.error(dis_has_no_variant(expr.variant_name.location, expr.name.text, expr.variant_name.text))
            return ErrorTy()

        generics = [self.type_converter.convert_type(generic) for generic in expr.generics]

        variant = dis_decl.get_variant(expr.variant_name.text)
        variant_ty = DisTy(expr.name.text, generics, TyPattern(expr.variant_name.text, None))
        arg_tys = [substitute(arg.ty, generics) for arg in variant.args]

        if len(arg_tys) == 0:
            return variant_ty
        else:
            return FunTy(arg_tys, variant_ty)

    def type_expr(self, expr: ExprNode):
        if isinstance(expr, FunInstNode):
            expr.ty = self.type_function_instantiation(expr)
            return expr.ty
        elif isinstance(expr, ValueNode):
            expr.ty = self.type_value(expr)
            return expr.ty
        elif isinstance(expr, DisConstructorNode):
            expr.ty = self.type_dis_constructor(expr)
            return expr.ty
        elif isinstance(expr, VarNode):
            expr.ty = self.type_var(expr)
            return expr.ty
        elif isinstance(expr, FitExprNode):
            expr.ty = self.type_fit(expr)
            return expr.ty
        elif isinstance(expr, CallNode):
            expr.ty = self.type_call(expr)
            return expr.ty
        elif isinstance(expr, MemberNode):
            expr.ty = self.type_member(expr)
            return expr.ty
        elif isinstance(expr, Write):
            expr.ty = None
            return expr.ty
        elif isinstance(expr, AssignNode):
            expr.ty = self.type_expr(expr.var)
            # todo check if expr.expr has compatible type
            return expr.ty
        else:
            raise Exception(f"Cannot get type of expression {expr}")

    def type_member(self, member: MemberNode):
        expr_ty = self.type_expr(member.expr)
        if isinstance(expr_ty, ErrorTy):
            return ErrorTy()
        elif not isinstance(expr_ty, DisTy):
            self.report.error(cannot_get_member_on_non_dis_type(member.location, member.member_name.text, expr_ty))
            return ErrorTy()
        elif expr_ty.pattern is None:
            err = cannot_get_member_on_non_variant_type(
                member.location,
                member.member_name.text,
                expr_ty,
                member.expr.location)
            self.report.error(err)
            return ErrorTy()
        else:
            dis_decl = self.ctx.get_dis(expr_ty.name)
            variant = dis_decl.get_variant(expr_ty.pattern.name)
            variant_node = self.ctx.dis_nodes[expr_ty.name][0].get_variant_node(expr_ty.pattern.name)
            if not variant.has_arg(member.member_name.text):
                self.report.error(variant_has_no_member(member.location, member.member_name.text, expr_ty, variant_node))
                return ErrorTy()
            arg_ty = deepcopy(substitute(variant.get_arg(member.member_name.text).ty, expr_ty.generic_types))
            if isinstance(arg_ty, DisTy) and expr_ty.pattern.children:
                arg_ty.pattern = expr_ty.pattern.children[variant.arg_index(member.member_name.text)]
            return arg_ty

    def type_fit(self, fit: FitExprNode | FitStatementNode):
        expr = fit.expr
        expr_ty = self.type_expr(expr)
        if isinstance(expr_ty, ErrorTy):
            return ErrorTy()

        is_fit_statement = isinstance(fit, FitStatementNode)

        if not isinstance(expr_ty, DisTy):
            self.report.error(expected_dis_type(expr.location, expr_ty))
            return ErrorTy()

        ty = self.type_fit_branch(expr, expr_ty, fit.branches[0], is_fit_statement)
        for branch in fit.branches[1:]:
            ty = find_supertype(ty, self.type_fit_branch(expr, expr_ty, branch, is_fit_statement))
        return ty

    def type_fit_branch(self, fit_expr: ExprNode, fit_expr_ty: Ty, branch: FitBranchNode, is_fit_statement):
        if not isinstance(fit_expr, VarNode) or not isinstance(branch.left, PatternNode):
            return self.type_fit_branch_right(branch.right, is_fit_statement)
        else:
            pat = self.convert_pattern(branch.left)
            self.validate_pattern_valid_for_ty(branch.left, fit_expr_ty)
            self.ctx.push()
            self.ctx.add_local_var(fit_expr.name.text, DisTy(fit_expr_ty.name, fit_expr_ty.generic_types, pat))
            result = self.type_fit_branch_right(branch.right, is_fit_statement)
            self.ctx.pop()
            return result

    def type_fit_branch_right(self, node, is_fit_statement):
        if is_fit_statement:
            self.typecheck(node)
        else:
            return self.type_expr(node)


    def validate_pattern_valid_for_ty(self, pat: PatternNode | None, ty: Ty):
        if pat is None:
            return True
        if not isinstance(ty, DisTy):
            self.report.error(cannot_match_pattern_to_non_dis(pat.name.location, pat.name.text, ty))
            return False
        dis_decl = self.ctx.get_dis(ty.name)
        dis_node = self.ctx.dis_nodes[ty.name][0]
        if not dis_decl.has_variant(pat.name.text):
            self.report.error(dis_has_no_variant(pat.location, ty.name, pat.name.text))
            return False
        variant_decl = dis_decl.get_variant(pat.name.text)
        variant_node = [v for v in dis_node.variants if v.name.text == pat.name.text][0]
        if variant_decl.get_arg_count() != len(pat.args):
            err = variant_argument_count_mismatch(pat.location, dis_node, variant_node, len(pat.args))
            self.report.error(err)
            return False

        for (arg_ty, child_pattern) in zip(variant_decl.get_arg_types(), pat.args):
            arg_ty = substitute(arg_ty, ty.generic_types)
            self.validate_pattern_valid_for_ty(child_pattern, arg_ty)

    def type_call(self, call: CallNode):
        fun_ty = self.type_expr(call.fun)
        arg_tys = [self.type_expr(arg) for arg in call.arguments]

        if isinstance(fun_ty, ErrorTy) or any(isinstance(arg, ErrorTy) for arg in arg_tys):
            return ErrorTy()
        elif isinstance(fun_ty, FunTy) and any(isinstance(arg, ErrorTy) for arg in fun_ty.arg_types):
            return ErrorTy()

        if not isinstance(fun_ty, FunTy):
            self.report.error(type_is_not_callable(call.fun.location, fun_ty))
            return ErrorTy()

        if len(fun_ty.arg_types) != len(call.arguments):
            expected = len(fun_ty.arg_types)
            actual = len(call.arguments)
            err = function_argument_count_mismatch(call.location, call.fun.location, fun_ty, expected, actual)
            self.report.error(err)


        error = False
        for arg, arg_ty, expected_ty in zip(call.arguments, arg_tys, fun_ty.arg_types):
            if not is_subtype(arg_ty, expected_ty):
                err = function_expects_arg_of_type(arg.location, expected_ty, arg_ty, call.fun.location, fun_ty)
                self.report.error(err)
                error = True
        if error:
            return ErrorTy()
        else:
            return fun_ty.result_type

    def type_ret(self, node: RetNode):
        return_ty = SimpleType('Void') if node.expr is None else self.type_expr(node.expr)
        return return_ty


    def convert_pattern(self, p: Pattern | ValueNode | None):
        # TODO: typecheck pattern with known dis variants
        if p is None:
            return None
        elif isinstance(p, ValueNode):
            return self.type_value(p)
        else:
            return TyPattern(p.name.text, [self.convert_pattern(arg) for arg in p.args])



    def find_dis_declarations(self, program: ProgramNode):
        dis_nodes = self.find_dis_nodes(program)
        self.type_converter.dis_nodes = dis_nodes
        self.ctx.dis_nodes = dis_nodes
        dis_declarations = {}
        for item in program.items:
            if isinstance(item, DisNode):
                if len(dis_nodes[item.name.text]) > 1:
                    dis_declarations[item.name.text] = ErrorTy()
                else:
                    self.ctx.push()
                    self.ctx.add_generics(item.generics)
                    variant_nodes = {}
                    variants = []
                    error = False
                    for variant in item.variants:
                        if variant.name.text in variant_nodes:
                            error = True
                            self.report.error(duplicated_dis_variant(item.name.text, variant, variant_nodes[variant.name.text]))
                        else:
                            args = [Arg(arg.name.text, self.type_converter.convert_type(arg.type)) for arg in variant.args]
                            variants.append(VariantDeclaration(variant.name.text, args))
                            variant_nodes[variant.name.text] = variant
                    self.ctx.pop()
                    if error:
                        dis_declarations[item.name.text] = ErrorTy()
                    else:
                        dis_declarations[item.name.text] = DisDeclaration(len(item.generics.params), variants)
        return dis_declarations

    def find_dis_nodes(self, program: ProgramNode) -> Dict[str, List[DisNode]]:
        dis_nodes = {}
        for item in program.items:
            if isinstance(item, DisNode):
                if not self.unique_generics(item.generics):
                    self.report_duplicated_generics(item.generics)
                if item.name.text in dis_nodes:
                    self.report.error(duplicated_dis(item, dis_nodes[item.name.text][0]))
                    dis_nodes[item.name.text].append(item)
                else:
                    dis_nodes[item.name.text] = [item]
        return dis_nodes


    def find_function_declarations(self, program: ProgramNode):
        fun_nodes = self.find_fun_nodes(program)
        self.ctx.fun_nodes = fun_nodes
        function_declarations = {}
        for name, funs in fun_nodes.items():
            if len(funs) > 1:
                function_declarations[name] = ErrorTy()
            else:
                fun = funs[0]
                if self.unique_generics(fun.generics):
                    decl = FunctionDeclaration(len(fun.generics.params), self.get_fun_type(fun))
                    function_declarations[name] = decl
                else:
                    function_declarations[name] = ErrorTy()
        return function_declarations

    def get_fun_type(self, fun: FunNode):
        if not self.unique_generics(fun.generics):
            return ErrorTy()
        self.ctx.push()
        self.ctx.add_generics(fun.generics)
        arg_types = [self.type_converter.convert_type(arg.type) for arg in fun.args]
        ret_type = self.type_converter.convert_type(fun.ret)
        self.ctx.pop()
        return FunTy(arg_types, ret_type)

    def unique_generics(self, generics: GenericParamsNode):
        names = set(name.text for name in generics.params)
        return len(names) == len(generics.params)

    def report_duplicated_generics(self, generics: GenericParamsNode):
        names = {}
        for name in generics.params:
            if name.text in names:
                self.report.error(duplicated_generics(name, names[name.text]))
            else:
                names[name.text] = name

    def find_fun_nodes(self, program: ProgramNode) -> Dict[str, List[FunNode]]:
        fun_nodes = {}
        for item in program.items:
            if isinstance(item, FunNode):
                if not self.unique_generics(item.generics):
                    self.report_duplicated_generics(item.generics)
                if item.name.text in fun_nodes:
                    self.report.error(duplicated_function(item, fun_nodes[item.name.text][0]))
                    fun_nodes[item.name.text].append(item)
                else:
                    fun_nodes[item.name.text] = [item]
        return fun_nodes

    def instantiate_function(self, fun_inst: FunInstNode, decl: FunctionDeclaration, args: List[Ty]):
        if decl.generic_arg_count != len(args):
            fun_node = self.ctx.fun_nodes[fun_inst.name.text][0]
            expected = decl.generic_arg_count
            actual = len(args)
            self.report.error(fun_generic_arguments_mismatch(fun_inst.location, fun_node, expected, actual))
        return substitute(decl.ty, args)
