from typing import *
from tree import *
from copy import deepcopy
from error_reporting import *

from tokens import NumberKind, StringKind

from typechecking.types import *
from typechecking.subtyping import *
from typechecking.context import *

def typecheck(program):
    typechecker = Typechecker()
    typechecker.ctx.simple_types['Int'] = SimpleType('Int')
    typechecker.ctx.simple_types['String'] = SimpleType('String')

    typechecker.typecheck(program)
    return typechecker.ctx, typechecker.report


class Typechecker:
    def __init__(self):
        self.ctx = TypingContext({}, {})
        self.report = ErrorReport()

    def typecheck(self, tree):
        if isinstance(tree, ProgramNode):
            self.typecheck_program(tree)
        elif isinstance(tree, Write):
            return
        elif isinstance(tree, FitNode):
            self.type_fit(tree)
        elif isinstance(tree, LetNode):
            ty = self.type_expr(tree.value)
            self.ctx.add_local_var(tree.name.text, ty)
        elif isinstance(tree, CallNode):
            self.type_call(tree)
        elif isinstance(tree, DisNode):
            self.type_dis_node(tree)
        elif isinstance(tree, FunNode):
            self.type_fun(tree)
        elif isinstance(tree, BlockNode):
            self.ctx.push()
            for statement in tree.statements:
                self.typecheck(statement)
            self.ctx.pop()
        elif isinstance(tree, RetNode):
            self.type_expr(tree.expr)
        else:
            raise Exception(f"Cannot type {tree}")

    def typecheck_program(self, program: ProgramNode):
        dises = self.find_dis_declarations(program)
        self.ctx.dises = dises
        functions = self.find_function_declarations(program)
        self.ctx.functions = functions

        for e in dises.values():
            self.typecheck_dis_declaration(e)

        for f in functions.values():
            self.typecheck_function_declaration(f)

        for item in program.items:
            self.typecheck(item)

    def type_var(self, var: VarNode):
        name = var.name.text
        if self.ctx.has_local_var(name):
            return self.ctx.get_local_var_type(name)
        if self.ctx.has_function(name):
            return self.ctx.get_function(name).ty
        self.report.error(Error(Message(var.location, f"Unknown variable: {name}")))
        return ErrorTy()

    def type_let(self, let: LetNode):
        var_type = self.type_expr(let.value)
        self.ctx.add_local_var(let.name, var_type)
        return None

    def type_fun(self, fun: FunNode):
        fun_ty = self.ctx.get_function(fun.name.text)
        self.ctx.push()
        self.ctx.add_generics(fun.generics)
        
        for arg, arg_ty in zip(fun.args, fun_ty.ty.arg_types):
            self.validate_type(arg_ty)
            self.ctx.add_local_var(arg.name.text, arg_ty)
        self.validate_type(fun_ty.ty.result_type)
        self.typecheck(fun.body)
        self.ctx.pop()

    def type_function_instantiation(self, fun_inst: FunInstNode):
        name = fun_inst.name.text
        if self.ctx.has_function(name):
            decl = self.ctx.get_function(name)
            generics = []
            for ty in fun_inst.generics:
                converted = self.convert_type(ty)
                self.validate_type(converted)
                generics.append(converted)
            return self.instantiate_function(name, decl, generics)
        else:
            raise Exception(f"Unknown function {fun_inst.name}")

    def type_value(self, expr: Value):
        if isinstance(expr.token.kind, NumberKind):
            return SimpleType('Int')
        elif isinstance(expr.token.kind, StringKind):
            return SimpleType('String')
        else:
            raise Exception(f"Unsupported value type: {type(expr.val)}")

    def type_dis_constructor(self, expr: DisConstructorNode):
        if not self.ctx.has_dis(expr.name.text):
            raise Exception(f"dis {expr.name} does not exist")
        dis_decl = self.ctx.get_dis(expr.name.text)
        if not dis_decl.has_variant(expr.variant_name.text):
            raise Exception(f"dis {expr.name} has no variant {expr.variant_name}")
        
        if dis_decl.generic_arg_count != len(expr.generics):
            raise Exception(f"dis {expr.dis_name} expects {dis_decl.generic_arg_count} generic arguments but got {len(expr.generics)}")
        
        generics = [self.convert_type(generic) for generic in expr.generics]

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
        elif isinstance(expr, Value):
            expr.ty = self.type_value(expr)
            return expr.ty
        elif isinstance(expr, DisConstructorNode):
            expr.ty = self.type_dis_constructor(expr)
            return expr.ty
        elif isinstance(expr, VarNode):
            expr.ty = self.type_var(expr)
            return expr.ty
        elif isinstance(expr, FitNode):
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
        else:
            raise Exception(f"Cannot get type of expression {expr}")

    def type_dis_node(self, dis: DisNode):
        dis_ty = self.ctx.get_dis(dis.name.text)
        for variant in dis_ty.variants:
            for arg in variant.args:
                self.validate_type(arg.ty)

    def type_member(self, member: MemberNode):
        expr_ty = self.type_expr(member.expr)
        if not isinstance(expr_ty, DisTy):
            raise Exception(f"Cannot get member {member.member_name} on type {expr_ty}")
        elif expr_ty.pattern is None:
            err = Error(Message(member.member_name.location, f"Cannot get member {member.member_name.text} on type {expr_ty}"))
            print_error(err)
            raise Exception(f"Cannot get member {member.member_name} on type {expr_ty}")
        else:
            dis_decl = self.ctx.get_dis(expr_ty.name)
            variant = dis_decl.get_variant(expr_ty.pattern.name)
            if not variant.has_arg(member.member_name.text):
                raise Exception(f"Variant {variant} has no member {member.member_name}")
            arg_ty = deepcopy(substitute(variant.get_arg(member.member_name.text).ty, expr_ty.generic_types))
            if isinstance(arg_ty, DisTy) and expr_ty.pattern.children:
                arg_ty.pattern = expr_ty.pattern.children[variant.arg_index(member.member_name.text)]
            return arg_ty

    def type_fit(self, fit: FitNode):
        expr = fit.expr
        expr_ty = self.type_expr(expr)
        if not isinstance(expr_ty, DisTy):
            msg = Message(expr.location, f"Expected dis type, got {expr_ty}")
            print_error(Error(msg))
            return ErrorTy()

        ty = self.type_fit_branch(expr, expr_ty, fit.branches[0])
        for branch in fit.branches[1:]:
            ty = find_supertype(ty, self.type_fit_branch(expr, expr_ty, branch))
        return ty

    def type_fit_branch(self, fit_expr: ExprNode, fit_expr_ty: Ty, branch: FitBranchNode):
        if not isinstance(fit_expr, VarNode) or not isinstance(branch.left, PatternNode):
            return self.type_expr(branch.right)
        else:
            pat = self.convert_pattern(branch.left)
            self.ctx.push()
            self.ctx.add_local_var(fit_expr.name.text, DisTy(fit_expr_ty.name, fit_expr_ty.generic_types, pat))
            result = self.type_expr(branch.right)
            self.ctx.pop()
            return result



    def type_call(self, call: CallNode):
        fun_ty = self.type_expr(call.fun)
        arg_tys = [self.type_expr(arg) for arg in call.arguments]

        if isinstance(fun_ty, ErrorTy) or any(isinstance(arg, ErrorTy) for arg in arg_tys):
            return ErrorTy()

        if not isinstance(fun_ty, FunTy):
            raise Exception(f"Type {fun_ty} is not callable")
        if len(fun_ty.arg_types) != len(call.arguments):
            raise Exception(f"Function {fun_ty} requires {len(fun_ty.arg_types)} arguments but {len(call.arguments)} were provided")
        
        
        for arg_ty, expected_ty in zip(arg_tys, fun_ty.arg_types):
            if not is_subtype(arg_ty, expected_ty):
                raise Exception(f"Function expects argument of type {expected_ty} but {arg_ty} was provided")
        return fun_ty.result_type

            
        
    def convert_type(self, parsed_type: TypeNode):
        if isinstance(parsed_type, DisTypeNode):
            if self.ctx.has_generic(parsed_type.name.text):
                if parsed_type.generics:
                    raise Exception(f"Type variable {parsed_type.name} cannot be generic")
                else:
                    return TyVar(self.ctx.get_generic(parsed_type.name.text))
            elif parsed_type.name.text in self.ctx.simple_types and not self.ctx.has_dis(parsed_type.name.text):
                if parsed_type.generics:
                    raise Exception(f"Type {parsed_type.name} is not generic")
                return self.ctx.simple_types[parsed_type.name.text]
            else:
                return DisTy(parsed_type.name.text, [self.convert_type(gen) for gen in parsed_type.generics], None)
        elif isinstance(parsed_type, FunctionTypeNode):
            arg_types = [self.convert_type(arg) for arg in parsed_type.args]
            ret_type = self.convert_type(parsed_type.ret)
            return FunTy(arg_types, ret_type)
        elif isinstance(parsed_type, DisConstructorNode):
            return DisTy(parsed_type.name.text, [self.convert_type(gen) for gen in parsed_type.generics], TyPattern(parsed_type.variant_name.text, None))
        elif parsed_type is None:
            return parsed_type
        else:
            raise Exception(f"Cannot convert {parsed_type} into Ty")
        
    def convert_pattern(self, p: Pattern | Value | None):
        # TODO: typecheck pattern with known dis variants
        if p is None:
            return None
        elif isinstance(p, Value):
            return self.type_value(p)
        else:
            return TyPattern(p.name.text, [self.convert_pattern(arg) for arg in p.args])

    
    def find_function_declarations(self, program):
        function_declarations = {}
        for item in program.items:
            if isinstance(item, FunNode):
                if item.name.text in function_declarations:
                    raise Exception(f"duplicated function: {item.name}")

                self.ctx.push()
                self.ctx.add_generics(item.generics)
                arg_types = [self.convert_type(arg.type) for arg in item.args]
                ret_type = self.convert_type(item.ret)
                self.ctx.pop()

                decl = FunctionDeclaration(len(item.generics), FunTy(arg_types, ret_type))
                function_declarations[item.name.text] = decl
        return function_declarations


    def typecheck_function_declaration(self, decl: FunctionDeclaration):
        tys = decl.ty.arg_types + [decl.ty.result_type]
        for ty in tys:
            self.validate_type(ty)
        
    def validate_pattern(self, ty: Ty, pattern: TyPattern | None):
        if pattern is None:
            return
        if not isinstance(ty, DisTy):
            raise Exception(f"Cannot match non-dis type to {pattern.name}!")
        dis_def = self.ctx.get_dis(ty.name)
        if not dis_def.has_variant(pattern.name):
            raise Exception(f"dis {ty.name} has no variant {pattern.name}")
        variant_def = dis_def.get_variant(pattern.name)
        if pattern.children is None:
            return
        if variant_def.get_arg_count() != len(pattern.children):
            raise Exception(f"Variant {ty.name}::{pattern.name} has {variant_def.get_arg_count()} args, not {len(pattern.children)} arguments")
        for (arg_ty, child_pattern) in zip(variant_def.get_arg_types(), pattern.children):
            self.validate_pattern(arg_ty, child_pattern, self.ctx)
        

    def validate_type(self,  ty: Ty):
        if ty is None:
            return
        elif isinstance(ty, TyVar):
            return
        elif isinstance(ty, FunTy):
            for arg_ty in ty.arg_types:
                self.validate_type(arg_ty)
            self.validate_type(ty.result_type)
        elif isinstance(ty, DisTy):
            if not self.ctx.has_dis(ty.name):
                raise Exception(f"There is no type {ty.name}")
            for generic_ty in ty.generic_types:
                self.validate_type(generic_ty)
            if ty.pattern is None:
                return
            dis_def = self.ctx.get_dis(ty.name)
            if not dis_def.has_variant(ty.pattern.name):
                err = Error(Message(ty.name.location, f"There is no type {ty.name.text}"))
                print_error(err)
            self.validate_pattern(ty, ty.pattern)

    def find_dis_declarations(self, program: ProgramNode):
        dis_declarations = {}
        for item in program.items:
            if isinstance(item, DisNode):
                if item.name.text in dis_declarations:
                    raise Exception(f"Duplicated dis: {item.name}")
                self.ctx.push()
                self.ctx.add_generics(item.generic_names)
                variants = [] 
                for branch in item.branches:
                    # if branch.name in variants:
                    #     raise Exception(f"Duplicated dis branch: {item.name}")
                    args = [Arg(arg.name.text, self.convert_type(arg.type)) for arg in branch.args]
                    variants.append(VariantDeclaration(branch.name.text, args))
                self.ctx.pop()
                dis_declarations[item.name.text] = DisDeclaration(len(item.generic_names), variants)
        return dis_declarations

    def typecheck_dis_declaration(self, decl: DisDeclaration | SimpleType):
        if isinstance(decl, SimpleType):
            return
        for variant in decl.variants:
            for arg_type in variant.get_arg_types():
                self.validate_type(arg_type)


    def instantiate_function(self, name: str, decl: FunctionDeclaration, args: List[Ty]):
        if decl.generic_arg_count != len(args):
            raise Exception(f"Function {name} requires {decl.arg_count} arguments, but got {len(args)}")
        return substitute(decl.ty, args)