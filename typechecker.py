from __future__ import annotations
from typing import *
from dataclasses import dataclass
from tree import *
import compiler

def typecheck(program):
    functions = find_function_declarations(program)
    enums = find_enum_declarations(program)
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
        self.mapping = {}
        self.enums = enums
        self.functions = functions
    
    def has_enum(self, name):
        return name in self.enums

    
type Ty = TyVar | FunTy | EnumTy | VariantTy | ErrorTy | None

@dataclass
class TyVar:
    index: int

class ErrorTy:
    pass

@dataclass
class FunctionDeclaration:
    generic_arg_count: int
    ty: FunTy

@dataclass
class EnumDeclaration:
    generic_arg_count: int
    branches: Dict[str, VariantDeclaration]

@dataclass
class VariantDeclaration:
    args: Dict[str, Ty]

@dataclass
class FunTy:
    arg_types: List[Ty]
    result_type: Ty

@dataclass
class EnumTy:
    name: str
    generic_types: List[Ty]

@dataclass
class VariantTy:
    name: str
    parent: EnumTy

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
        validate_type(ty, ctx, decl.generic_arg_count)

def validate_type(ty: Ty, ctx: TypingContext, generic_arg_count):
    if isinstance(ty, TyVar):
        if ty.index >= generic_arg_count:
            raise Exception(f"There is no variable {ty.index} in current context")
    elif isinstance(ty, FunTy):
        for arg_ty in ty.arg_types:
            validate_type(arg_ty, ctx, generic_arg_count)
        validate_type(ty.result_type, ctx, generic_arg_count)
    elif isinstance(ty, EnumTy):
        if not ctx.has_enum(ty.name):
            raise Exception(f"There is no enum {ty.name}")
        for generic_ty in ty.generic_types:
            validate_type(generic_ty, ctx, generic_arg_count)


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
                args = {arg.name: convert_type(arg.type, generic_map) for arg in branch.args}
                variants[branch.name] = VariantDeclaration(args)
                    
            enum_declarations[item.name] = EnumDeclaration(len(item.generic_names), variants)
    return enum_declarations

def typecheck_enum_declaration(decl: EnumDeclaration, ctx: TypingContext):
    pass

def instantiate_function(name, decl: FunctionDeclaration, args: List[Ty]):
    if decl.arg_count != len(args):
        raise Exception(f"Function {name} requires {decl.arg_count} arguments, but got {len(args)}")
    return substitute(decl.ty, args)

def substitute(ty: Ty, subst: List[Ty]):
    if isinstance(ty, FunTy):
        arg_types = [substitute(arg, subst) for arg in ty.arg_types]
        result_type = substitute(ty.result_type, subst)
        return FunTy(arg_types, result_type)
    elif isinstance(ty, VariantTy):
        return VariantTy(ty.name, substitute(ty.parent, subst))
    elif isinstance(ty, EnumTy):
        generic_types = [substitute(t, subst) for t in ty.generic_types]
        return EnumTy(ty.name, generic_types)
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
            return EnumTy(parsed_type.name, [convert_type(gen, generic_nums_ctx) for gen in parsed_type.generics])
    elif isinstance(parsed_type, FunctionType):
        arg_types = [convert_type(arg, generic_nums_ctx) for arg in parsed_type.args]
        ret_type = convert_type(parsed_type.ret, generic_nums_ctx)
        return FunTy(arg_types, ret_type)
    elif isinstance(parsed_type, EnumConstructor):
        return VariantTy(parsed_type.variant_name, EnumTy(parsed_type.enum_name, parsed_type.generics))
    

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
            return t1
        else:
            return ErrorTy()
    if isinstance(t1, VariantTy) and isinstance(t2, VariantTy):
        if t1 == t2:
            return t1
        else:
            return ErrorTy()
    if isinstance(t1, VariantTy) and isinstance(t2, EnumTy):
        if t1.parent == t2:
            return t2
        else:
            return ErrorTy()
    if isinstance(t1, EnumTy) and isinstance(t2, VariantTy):
        if t1 == t2.parent:
            return t2
        else:
            return ErrorTy()
    raise Exception("Unreachable reached!")

def is_subtype(sub, sup):
    if sub == sup:
        return True
    if isinstance(sub, VariantTy) and isinstance(sup, EnumTy):
        return sub.parent == sup
    if isinstance(sub, FunTy) and isinstance(sup, FunTy):
        return (
            len(sub.arg_types) == len(sup.arg_types) 
                and is_subtype(sub.result_type, sup.result_type) 
                and all(is_subtype(b, a) for (a, b) in zip(sub.arg_types, sup.arg_types))
        )
    return False



    
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
        
    
            

