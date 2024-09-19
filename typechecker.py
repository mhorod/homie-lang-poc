from __future__ import annotations
from typing import *
from dataclasses import dataclass
from tree import *
from copy import deepcopy
import sys

def typecheck(program):
    ctx = TypingContext({}, {})
    ctx.simple_types['Int'] = SimpleType('Int')
    ctx.simple_types['String'] = SimpleType('String')


    enums = find_enum_declarations(program, ctx)
    ctx.enums = enums
    functions = find_function_declarations(program, ctx)
    ctx.functions = functions

    for e in enums.values():
        typecheck_enum_declaration(e, ctx)

    for f in functions.values():
        typecheck_function_declaration(f, ctx)

    do_typing(program, ctx)
    return ctx
    

class TypingContext:
    def __init__(self, enums, functions):
        self.locals = {}
        self.enums = enums
        self.functions = functions
        self.generic_nums_ctx = {}
        self.simple_types = {}
    
    def has_enum(self, name) -> bool:
        return name in self.enums
    
    def get_enum(self, name) -> EnumDeclaration:
        return self.enums[name]

    def has_function(self, name) -> bool:
        return name in self.functions

    def get_function(self, name) -> FunctionDeclaration:
        return self.functions[name]
    
    def with_local_var(self, name: str, ty: Ty) -> TypingContext:
        result = self.clone()
        result.locals[name] = ty
        return result

    def add_local_var(self, name: str, ty: Ty):
        self.locals[name] = ty
    
    def has_local_var(self, name: str) -> bool:
        return name in self.locals

    def get_local_var_type(self, name: str) -> Ty:
        return self.locals[name]
    
    def clone(self):
        result = TypingContext(self.enums, self.functions)
        result.locals = dict(self.locals)
        result.generic_nums_ctx = dict(self.generic_nums_ctx)
        result.simple_types = dict(self.simple_types)
        return result
    
    def with_generic_nums(self, generics: List[str]):
        result = self.clone()
        for i, name in enumerate(generics):
            result.generic_nums_ctx[name] = i
        return result


    
type Ty = TyVar | FunTy | EnumTy | ErrorTy | None | SimpleType

@dataclass
class TyVar:
    index: int

@dataclass
class SimpleType:
    name: str

class ErrorTy:
    pass

@dataclass
class FunctionDeclaration:
    generic_arg_count: int
    ty: FunTy

@dataclass
class EnumDeclaration:
    generic_arg_count: int
    variants: List[VariantDeclaration]

    def has_variant(self, name):
        return any(variant.name == name for variant in self.variants)

    def get_variant(self, name):
        return next(variant for variant in self.variants if variant.name == name)

    def get_variant_id(self, name):
        return next(i for (i, variant) in enumerate(self.variants) if variant.name == name)

@dataclass
class VariantDeclaration:
    name: str
    args: List[Arg]

    def get_arg_count(self):
        return len(self.args)

    def get_arg_types(self):
        return [arg.ty for arg in self.args]
    
    def has_arg(self, name: str):
        return any(arg.name == name for arg in self.args)

    def get_arg(self, name: str):
        return next(arg for arg in self.args if arg.name == name)

    def arg_index(self, name: str):
        return [arg.name for arg in self.args].index(name)

@dataclass
class Arg:
    name: str
    ty: Ty

@dataclass
class FunTy:
    arg_types: List[Ty]
    result_type: Ty

@dataclass
class TyPattern:
    name: str
    children: List[TyPattern | None] | None

@dataclass
class EnumTy:
    name: str
    generic_types: List[Ty]
    pattern: TyPattern | None

def find_function_declarations(program, ctx: TypingContext):
    function_declarations = {}
    for item in program.items:
        if isinstance(item, Fun):
            if item.name in function_declarations:
                raise Exception(f"duplicated function: {item.name}")
            cloned_ctx = ctx.clone()
            cloned_ctx.generic_nums_ctx = {name: i for i, name in enumerate(item.generics)}
            arg_types = [convert_type(arg.type, cloned_ctx) for arg in item.arguments]
            ret_type = convert_type(item.ret, cloned_ctx)
            decl = FunctionDeclaration(len(item.generics), FunTy(arg_types, ret_type))
            function_declarations[item.name] = decl
    return function_declarations


def typecheck_function_declaration(decl: FunctionDeclaration, ctx: TypingContext):
    tys = decl.ty.arg_types + [decl.ty.result_type]
    for ty in tys:
        validate_type(ty, ctx)
    
def validate_pattern(ty: Ty, pattern: TyPattern | None, ctx: TypingContext):
    if pattern is None:
        return
    if not isinstance(ty, EnumTy):
        raise Exception(f"Cannot match non-enum type to {pattern.name}!")
    enum_def = ctx.get_enum(ty.name)
    if not enum_def.has_variant(pattern.name):
        raise Exception(f"Enum {ty.name} has no variant {pattern.name}")
    variant_def = enum_def.get_variant(pattern.name)
    if pattern.children is None:
        return
    if variant_def.get_arg_count() != len(pattern.children):
        raise Exception(f"Variant {ty.name}::{pattern.name} has {variant_def.get_arg_count()} args, not {len(pattern.children)} arguments")
    for (arg_ty, child_pattern) in zip(variant_def.get_arg_types(), pattern.children):
        validate_pattern(arg_ty, child_pattern, ctx)
    


def validate_type(ty: Ty, ctx: TypingContext):
    if ty is None:
        return
    elif isinstance(ty, TyVar):
        return
    elif isinstance(ty, FunTy):
        for arg_ty in ty.arg_types:
            validate_type(arg_ty, ctx)
        validate_type(ty.result_type, ctx)
    elif isinstance(ty, EnumTy):
        if not ctx.has_enum(ty.name):
            raise Exception(f"There is no type {ty.name}")
        for generic_ty in ty.generic_types:
            validate_type(generic_ty, ctx)
        if ty.pattern is None:
            return
        enum_def = ctx.get_enum(ty.name)
        if not enum_def.has_variant(ty.pattern.name):
            raise Exception(f"There is no type {ty.name}")
        validate_pattern(ty, ty.pattern, ctx)



def find_enum_declarations(program, ctx: TypingContext):
    enum_declarations = {}
    for item in program.items:
        if isinstance(item, EnumNode):
            if item.name in enum_declarations:
                raise Exception(f"Duplicated enum: {item.name}")
            cloned_ctx = ctx.clone()
            cloned_ctx.generic_nums_ctx = {name: i for (i, name) in enumerate(item.generic_names)}
            variants = [] 
            for branch in item.branches:
                # if branch.name in variants:
                #     raise Exception(f"Duplicated enum branch: {item.name}")
                args = [Arg(arg.name, convert_type(arg.type, cloned_ctx)) for arg in branch.args]
                variants.append(VariantDeclaration(branch.name, args))
                    
            enum_declarations[item.name] = EnumDeclaration(len(item.generic_names), variants)
    return enum_declarations

def typecheck_enum_declaration(decl: EnumDeclaration | SimpleType, ctx: TypingContext):
    if isinstance(decl, SimpleType):
        return
    for variant in decl.variants:
        for arg_type in variant.get_arg_types():
            validate_type(arg_type, ctx)

def instantiate_function(name: str, decl: FunctionDeclaration, args: List[Ty]):
    if decl.generic_arg_count != len(args):
        raise Exception(f"Function {name} requires {decl.arg_count} arguments, but got {len(args)}")
    return substitute(decl.ty, args)

def substitute(ty: Ty, subst: List[Ty]):
    if isinstance(ty, FunTy):
        arg_types = [substitute(arg, subst) for arg in ty.arg_types]
        result_type = substitute(ty.result_type, subst)
        return FunTy(arg_types, result_type)
    elif isinstance(ty, EnumTy):
        generic_types = [substitute(t, subst) for t in ty.generic_types]
        return EnumTy(ty.name, generic_types, ty.pattern)
    elif isinstance(ty, TyVar):
        return subst[ty.index]
    else:
        return ty

def convert_type(parsed_type: Type, ctx: TypingContext):
    if isinstance(parsed_type, EnumType):
        if parsed_type.name in ctx.generic_nums_ctx:
            if parsed_type.generics:
                raise Exception(f"Type variable {parsed_type.name} cannot be generic")
            else:
                return TyVar(ctx.generic_nums_ctx[parsed_type.name])
        elif parsed_type.name in ctx.simple_types and not ctx.has_enum(parsed_type.name):
            if parsed_type.generics:
                raise Exception(f"Type {parsed_type.name} is not generic")
            return ctx.simple_types[parsed_type.name]
        else:
            return EnumTy(parsed_type.name, [convert_type(gen, ctx) for gen in parsed_type.generics], None)
    elif isinstance(parsed_type, FunctionType):
        arg_types = [convert_type(arg, ctx) for arg in parsed_type.args]
        ret_type = convert_type(parsed_type.ret, ctx)
        return FunTy(arg_types, ret_type)
    elif isinstance(parsed_type, EnumConstructor):
        return EnumTy(parsed_type.enum_name, [convert_type(gen, ctx) for gen in parsed_type.generics], TyPattern(parsed_type.variant_name, None))
    elif parsed_type is None:
        return parsed_type
    else:
        raise Exception(f"Cannot convert {parsed_type} into Ty")
    
def convert_pattern(p: Pattern | Value | None, ctx: TypingContext):
    # TODO: typecheck pattern with known enum variants
    if p is None:
        return None
    elif isinstance(p, Value):
        return type_expr(p, ctx)
    else:
        return TyPattern(p.name, [convert_pattern(arg, ctx) for arg in p.args])


def find_superpattern(p1: TyPattern | None, p2: TyPattern | None) -> TyPattern | None:
    if p1 is None or p2 is None:
        return None
    if p1.name != p2.name:
        return None
    if p1.children is None or p2.children is None:
        return TyPattern(p1.name, None)
    if len(p1.children) != len(p2.children):
        raise Exception("Unreachable reached! TyPattern was supposed to be validated!")
    return TyPattern(p1.name, [find_superpattern(c1, c2) for (c1, c2) in zip(p1.children, p2.children)])

def find_supertype(t1: Ty, t2: Ty) -> Ty:
    '''
    Find type T such that t1 <: T and t2 <: T
    '''
    if t1 is None and t2 is None:
        return None
    elif t1 is None or t2 is None:
        return ErrorTy()
    elif t1 == t2:
        return t1
    elif isinstance(t1, FunTy) and isinstance(t2, FunTy):
        if t1.arg_types != t2.arg_types:
            return ErrorTy()
        result_ty = find_supertype(t1.result_type, t2.result_type)
        if isinstance(result_ty, ErrorTy):
            return ErrorTy()
        return FunTy(t1.arg_types, result_ty)
    elif isinstance(t1, FunTy) or isinstance(t2, FunTy):
        return ErrorTy()
    elif isinstance(t1, EnumTy) and isinstance(t2, EnumTy):
        if t1.name == t2.name and t1.generic_types == t2.generic_types:
            return EnumTy(t1.name, t1.generic_types, find_superpattern(t1.pattern, t2.pattern))
        else:
            return ErrorTy()
    raise Exception("Unreachable reached! Got non-existent type!")

def is_subpattern(sub: TyPattern | None, sup: TyPattern | None) -> bool:
    if sub == sup:
        return True
    if sup is None:
        return True
    if sub is None:
        return False
    if sub.name != sup.name:
        return False 
    if sup.children is None:
        return True
    if sub.children is None:
        return False
    if len(sub.children) != len(sup.children):
        raise Exception("Unreachable reached! TyPattern was supposed to be validated!")
    return all(is_subpattern(a, b) for (a, b) in zip(sub.children, sub.children))

def is_subtype(sub, sup):
    if sub == sup:
        return True
    if isinstance(sub, FunTy) and isinstance(sup, FunTy):
        return (
            len(sub.arg_types) == len(sup.arg_types) 
                and is_subtype(sub.result_type, sup.result_type) 
                and all(is_subtype(b, a) for (a, b) in zip(sub.arg_types, sup.arg_types))
        )
    if isinstance(sub, EnumTy) and isinstance(sup, EnumTy):
        return sub.name == sup.name and sub.generic_types == sup.generic_types and is_subpattern(sub.pattern, sup.pattern)
    return False


def type_var(var: Var, ctx: TypingContext):
    if ctx.has_local_var(var.name):
        return ctx.get_local_var_type(var.name)
    if ctx.has_function(var.name):
        return ctx.get_function(var.name).ty
    raise Exception(f"Unknown variable: {var.name}")

def type_let(let: Let, ctx: TypingContext):
    var_type = type_expr(let.value, ctx)
    ctx.add_local_var(let.name, var_type)
    return None

def type_fun(fun: Fun, ctx: TypingContext):
    fun_ty = ctx.get_function(fun.name)
    ctx = ctx.clone()
    ctx.generic_nums_ctx = {generic: i for (i, generic) in enumerate(fun.generics)}
    
    for arg, arg_ty in zip(fun.arguments, fun_ty.ty.arg_types):
        validate_type(arg_ty, ctx)
        ctx.add_local_var(arg.name, arg_ty)
    validate_type(fun_ty.ty.result_type, ctx)
    do_typing(fun.body, ctx)

def type_function_instantiation(fun_inst: FunInstantiation, ctx: TypingContext):
    if ctx.has_function(fun_inst.name):
        decl = ctx.get_function(fun_inst.name)
        generics = []
        for ty in fun_inst.generics:
            converted = convert_type(ty, ctx)
            validate_type(converted, ctx)
            generics.append(converted)
        return instantiate_function(fun_inst.name, decl, generics)
    else:
        raise Exception(f"Unknown function {fun_inst.name}")

def type_value(expr: Value, ctx: TypingContext):
    if isinstance(expr.val, int):
        return SimpleType('Int')
    elif isinstance(expr.val, str):
        return SimpleType('String')
    else:
        raise Exception(f"Unsupported value type: {type(expr.val)}")

def type_enum_constructor(expr: EnumConstructor, ctx: TypingContext):
    if not ctx.has_enum(expr.enum_name):
        raise Exception(f"Enum {expr.enum_name} does not exist")
    enum_decl = ctx.get_enum(expr.enum_name)
    if not enum_decl.has_variant(expr.variant_name):
        raise Exception(f"Enum {expr.enum_name} has no variant {expr.variant_name}")
    
    if enum_decl.generic_arg_count != len(expr.generics):
        raise Exception(f"Enum {expr.enum_name} expects {enum_decl.generic_arg_count} generic arguments but got {len(expr.generics)}")
    
    generics = [convert_type(generic, ctx) for generic in expr.generics]

    variant = enum_decl.get_variant(expr.variant_name)
    variant_ty = EnumTy(expr.enum_name, generics, TyPattern(expr.variant_name, None))
    arg_tys = [substitute(arg.ty, generics) for arg in variant.args]

    if len(arg_tys) == 0:
        return variant_ty
    else:
        return FunTy(arg_tys, variant_ty)

    

def type_expr(expr: Expr, ctx: TypingContext):
    if isinstance(expr, FunInstantiation):
        expr.ty = type_function_instantiation(expr, ctx)
        return expr.ty
    elif isinstance(expr, Value):
        expr.ty = type_value(expr, ctx)
        return expr.ty
    elif isinstance(expr, EnumConstructor):
        expr.ty = type_enum_constructor(expr, ctx)
        return expr.ty
    elif isinstance(expr, Var):
        expr.ty = type_var(expr, ctx)
        return expr.ty
    elif isinstance(expr, Fit):
        expr.ty = type_fit(expr, ctx)
        return expr.ty
    elif isinstance(expr, Call):
        expr.ty = type_call(expr, ctx)
        return expr.ty
    elif isinstance(expr, Member):
        expr.ty = type_member(expr, ctx)
        return expr.ty
    else:
        raise Exception(f"Cannot get type of expression {expr}")

def type_enum_node(enum: EnumNode, ctx: TypingContext):
    enum_ty = ctx.get_enum(enum.name)
    for variant in enum_ty.variants:
        for arg in variant.args:
            validate_type(arg.ty, ctx)

def type_member(member: Member, ctx: TypingContext):
    expr_ty = type_expr(member.expr, ctx)
    if not isinstance(expr_ty, EnumTy):
        raise Exception(f"Cannot get member {member.member_name} on type {expr_ty}")
    elif expr_ty.pattern is None:
        raise Exception(f"Cannot get member {member.member_name} on type {expr_ty}")
    else:
        enum_decl = ctx.get_enum(expr_ty.name)
        variant = enum_decl.get_variant(expr_ty.pattern.name)
        if not variant.has_arg(member.member_name):
            raise Exception(f"Variant {variant} has no member {member.member_name}")
        arg_ty = deepcopy(substitute(variant.get_arg(member.member_name).ty, expr_ty.generic_types))
        if isinstance(arg_ty, EnumTy) and expr_ty.pattern.children:
            arg_ty.pattern = expr_ty.pattern.children[variant.arg_index(member.member_name)]
        return arg_ty


def type_fit(fit: Fit, ctx: TypingContext):
    expr = fit.var
    expr_ty = type_expr(expr, ctx)

    ty = type_fit_branch(expr, expr_ty, fit.branches[0], ctx)
    for branch in fit.branches[1:]:
        ty = find_supertype(ty, type_fit_branch(expr, expr_ty, branch, ctx))
    return ty

def type_fit_branch(fit_expr: Expr, fit_expr_ty: Ty, branch: FitBranch, ctx: TypingContext):
    if not isinstance(fit_expr, Var) or not isinstance(branch.left, Pattern):
        return type_expr(branch.right, ctx)
    else:
        pat = convert_pattern(branch.left, ctx)
        ctx = ctx.with_local_var(fit_expr.name, EnumTy(fit_expr_ty.name, fit_expr_ty.generic_types, pat))
        result = type_expr(branch.right, ctx)
        return result



def type_call(call: Call, ctx: TypingContext):
    fun_ty = type_expr(call.fun, ctx)
    if not isinstance(fun_ty, FunTy):
        raise Exception(f"Type {fun_ty} is not callable")
    if len(fun_ty.arg_types) != len(call.arguments):
        raise Exception(f"Function {fun_ty} requires {len(fun_ty.arg_types)} arguments but {len(call.arguments)} were provided")
    
    
    for arg, expected_ty in zip(call.arguments, fun_ty.arg_types):
        arg_ty = type_expr(arg, ctx)
        if not is_subtype(arg_ty, expected_ty):
            raise Exception(f"Function expects argument of type {expected_ty} but {arg_ty} was provided")
    return fun_ty.result_type

def do_typing(tree, ctx: TypingContext):
    if isinstance(tree, ProgramType):
        for item in tree.items:
            do_typing(item, ctx)
    elif isinstance(tree, Write):
        return
    elif isinstance(tree, Fit):
        tree.ty = type_fit(tree, ctx)
        return tree.ty
    elif isinstance(tree, Let):
        ty = type_expr(tree.value, ctx)
        ctx.add_local_var(tree.name, ty)
    elif isinstance(tree, Call):
        tree.ty = type_call(tree, ctx)
        return tree.ty
    elif isinstance(tree, EnumNode):
        tree.ty = type_enum_node(tree, ctx)
        return tree.ty
    elif isinstance(tree, Fun):
        tree.ty = type_fun(tree, ctx)
        return tree.ty
    elif isinstance(tree, Block):
        for item in tree.expressions:
            do_typing(item, ctx)
    elif isinstance(tree, Return):
        do_typing(tree.expr, ctx)
    elif isinstance(tree, Member):
        tree.ty = type_member(tree, ctx)
        return tree.ty
    elif isinstance(tree, FunInstantiation):
        tree.ty = type_function_instantiation(tree, ctx)
        return tree.ty
    elif isinstance(tree, Var):
        tree.ty = type_var(tree, ctx)
        return tree.ty
    else:
        raise Exception(f"Cannot type {tree}")
        
    
            

