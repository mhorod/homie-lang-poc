from __future__ import annotations
from typing import *
from dataclasses import dataclass
from tree import *
import compiler

def typecheck(program):
    functions = find_function_declarations(program)
    enums = find_enum_declarations(program)
    enums['Int'] = SimpleType('Int')
    enums['String'] = SimpleType('String')

    ctx = TypingContext(enums, functions)
    for name, decl in functions.items():
        print(name, decl)
        print()
    for name, decl in enums.items():
        print(name, decl)
    print(functions)

    for f in functions.values():
        typecheck_function_declaration(f, ctx)

    for e in enums.values():
        typecheck_enum_declaration(e, ctx)

class Ty:
    pass


class TypingContext:
    def __init__(self, enums, functions):
        self.locals = {}
        self.enums = enums
        self.functions = functions
    
    def has_enum(self, name) -> bool:
        return name in self.enums
    
    def get_enum(self, name) -> EnumDeclaration:
        return self.enums[name]

    def has_function(self, name) -> bool:
        return name in self.functions

    def get_function(self, name) -> FunctionDeclaration:
        return self.functions[name]
    
    def with_local_var(self, name: str, ty: Ty) -> TypingContext:
        result = TypingContext(self.enums, self.functions)
        result.locals = dict(self.locals)
        result.locals[name] = ty
        return result

    def add_local_var(self, name: str, ty: Ty):
        self.locals[name] = ty
    
    def has_local_var(self, name: str) -> bool:
        return name in self.locals

    def get_local_var_type(self, name: str) -> Ty:
        return self.locals[name]

    
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
    variants: Dict[str, VariantDeclaration]

    def has_variant(self, name):
        return name in self.variants

    def get_variant(self, name):
        return self.variants[name]

@dataclass
class VariantDeclaration:
    args: List[Arg]

    def get_arg_count(self):
        return len(self.args)

    def get_arg_types(self):
        return [arg.ty for arg in self.args]
    
    def has_arg(self, name: str):
        return any(arg.name == name for arg in self.args)

    def get_arg(self, name: str):
        return next(arg for arg in self.args if arg.name == name)

@dataclass
class Arg:
    name: str
    ty: Ty

@dataclass
class FunTy:
    arg_types: List[Ty]
    result_type: Ty

@dataclass
class Pattern:
    name: str
    children: List[Pattern | None] | None

@dataclass
class EnumTy:
    name: str
    generic_types: List[Ty]
    pattern: Pattern | None

def find_function_declarations(program):
    function_declarations = {}
    for item in program.items:
        if isinstance(item, Fun):
            if item.name in function_declarations:
                raise Exception(f"duplicated function: {item.name}")
            generic_nums = {name: i for i, name in enumerate(item.generics)}
            arg_types = [convert_type(arg.type, generic_nums) for arg in item.arguments]
            ret_type = convert_type(item.ret, generic_nums)
            decl = FunctionDeclaration(len(item.generics), FunTy(arg_types, ret_type))
            function_declarations[item.name] = decl
    return function_declarations


def typecheck_function_declaration(decl: FunctionDeclaration, ctx: TypingContext):
    tys = decl.ty.arg_types + [decl.ty.result_type]
    for ty in tys:
        validate_type(ty, ctx)
    
def validate_pattern(ty: Ty, pattern: Pattern | None, ctx: TypingContext):
    if pattern is None:
        return
    if not isinstance(ty, EnumTy):
        raise Exception(f"Cannot match non-enum type to {pattern.name}!")
    validate_type(ty) # probably unnecessary, but won't hurt
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
            raise Exception(f"There is no enum {ty.name}")
        for generic_ty in ty.generic_types:
            validate_type(generic_ty, ctx)
        if ty.pattern is None:
            return
        enum_def = ctx.get_enum(ty.name)
        if not enum_def.has_variant(ty.pattern.name):
            raise Exception(f"There is no enum {ty.name}")
        validate_pattern(ty, ty.pattern, ctx)



def find_enum_declarations(program):
    enum_declarations = {}
    for item in program.items:
        if isinstance(item, EnumNode):
            if item.name in enum_declarations:
                raise Exception(f"Duplicated enum: {item.name}")
            generic_map = {name: i for (i, name) in enumerate(item.generic_names)}
            variants = {}
            for branch in item.branches:
                if branch.name in variants:
                    raise Exception(f"Duplicated enum branch: {item.name}")
                args = [Arg(arg.name, convert_type(arg.type, generic_map)) for arg in branch.args]
                variants[branch.name] = VariantDeclaration(args)
                    
            enum_declarations[item.name] = EnumDeclaration(len(item.generic_names), variants)
    return enum_declarations

def typecheck_enum_declaration(decl: EnumDeclaration, ctx: TypingContext):
    for variant in decl.variants.values():
        for arg_type in variant.get_arg_types():
            validate_type(arg_type, ctx)

def instantiate_function(name: str, decl: FunctionDeclaration, args: List[Ty]):
    if decl.arg_count != len(args):
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

def convert_type(parsed_type: Type, generic_nums_ctx: Dict[str, int]):
    if isinstance(parsed_type, EnumType):
        if parsed_type.name in generic_nums_ctx:
            if parsed_type.generics:
                raise Exception(f"Type variable {parsed_type.name} cannot be generic")
            else:
                return TyVar(generic_nums_ctx[parsed_type.name])
        else:
            return EnumTy(parsed_type.name, [convert_type(gen, generic_nums_ctx) for gen in parsed_type.generics], None)
    elif isinstance(parsed_type, FunctionType):
        arg_types = [convert_type(arg, generic_nums_ctx) for arg in parsed_type.args]
        ret_type = convert_type(parsed_type.ret, generic_nums_ctx)
        return FunTy(arg_types, ret_type)
    elif isinstance(parsed_type, EnumConstructor):
        return EnumTy(parsed_type.enum_name, [convert_type(gen, generic_nums_ctx) for gen in parsed_type.generics], Pattern(parsed_type.variant_name, None))
    

def find_superpattern(p1: Pattern | None, p2: Pattern | None) -> Pattern | None:
    if p1 is None or p2 is None:
        return None
    if p1.name != p2.name:
        return None
    if p1.children is None or p2.children is None:
        return Pattern(p1.name, None)
    if len(p1.children) != len(p2.children):
        raise Exception("Unreachable reached! Pattern was supposed to be validated!")
    return Pattern(p1.name, [find_superpattern(c1, c2) for (c1, c2) in zip(p1.children, p2.children)])

def find_supertype(t1: Ty, t2: Ty) -> Ty:
    '''
    Find type T such that t1 <: T and t2 <: T
    '''
    if t1 is None and t2 is None:
        return None
    if t1 is None or t2 is None:
        return ErrorTy()
    if isinstance(t1, FunTy) and isinstance(t2, FunTy):
        if t1.arg_types != t2.arg_types:
            return ErrorTy()
        result_ty = find_supertype(t1.result_type, t2.result_type)
        if isinstance(result_ty, ErrorTy):
            return ErrorTy()
        return FunTy(t1.arg_types, result_ty)
    if isinstance(t1, FunTy) or isinstance(t2, FunTy):
        return ErrorTy()
    if isinstance(t1, EnumTy) and isinstance(t2, EnumTy):
        if t1.name == t2.name and t1.generic_types == t2.generic_types:
            return EnumTy(t1.name, t1.generic_types, find_superpattern(t1.pattern, t2.pattern))
        else:
            return ErrorTy()
    raise Exception("Unreachable reached! Got non-existent type!")

def is_subpattern(sub: Pattern | None, sup: Pattern | None) -> bool:
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
        raise Exception("Unreachable reached! Pattern was supposed to be validated!")
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
        return sub.name == sup.name and is_subpattern(sub.pattern, sup.pattern)
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
    fun_def = ctx.get_enum(fun.name)

    pass

def type_function_instantiation(fun_inst: FunInstantiation, ctx: TypingContext):
    if ctx.has_function(fun_inst.name):
        decl = ctx.get_function(fun_inst.name)
        for ty in fun_inst.generics:
            validate_type(convert_type(ty), ctx)
        return instantiate_function(fun_inst.name, decl, fun_inst.generics)
    else:
        raise Exception(f"Unknown function {fun_inst.name}")

def type_value(expr: Value, ctx: TypingContext):
    if isinstance(expr.val, int):
        return SimpleType('Int')
    elif isinstance(expr.val, str):
        return SimpleType('String')
    else:
        raise Exception(f"Unsupported value type: {type(expr.val)}")

def type_enum_constructor(expr, EnumConstructor):
    pass

def type_expr(expr: Expr, ctx: TypingContext):
    if isinstance(expr, FunInstantiation):
        return type_function_instantiation(expr, ctx)
    elif isinstance(expr, Value):
        return type_value(expr, ctx)
    elif isinstance(expr, EnumConstructor):
        return type_enum_constructor(expr, ctx)

    
def do_typing(tree, ctx: TypingContext):
    if isinstance(tree, Fit):
        ty = tree.branches[0].ty
        for branch in tree.branches[1:]:
            ty = find_supertype(ty, branch.right.ty)
        return ty

    elif isinstance(tree, Let):
        ty = tree.value.ty
        ctx.mapping[tree.name] = ty
        if isinstance(ty, ErrorTy):
            return ErrorTy()
        else:
            return None

    elif isinstance(tree, Call):
        fun_ty = tree.fun.ty
        if not isinstance(fun_ty, FunTy):
            return ErrorTy()
        if len(fun_ty.arg_types) != len(tree.arguments):
            return ErrorTy()
        if not all(is_subtype(arg.ty, arg_ty) for (arg, arg_ty) in zip(tree.arguments, fun_ty.arg_types)):
            return ErrorTy()
        return fun_ty.result_type
        
    
            

