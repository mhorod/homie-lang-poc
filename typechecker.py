from __future__ import annotations
from typing import *
from dataclasses import dataclass
from tree import *
import compiler

class Ty:
    pass


class TypingContext:
    def __init__(self):
        self.mapping = {}
        self.enums = {}

    
type Ty = FunTy | EnumTy | VariantTy | ErrorTy | None

class ErrorTy:
    pass

@dataclass
class TyScheme:
    generic_types: List[str]
    ty: Ty

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


@dataclass
class Fun:
    ty: Ty


def find_function_types(program):
    function_declarations = {}
    for item in program.items:
        if isinstance(item, Fun):
            arg_types = [convert_type(arg.type) for arg in item.args]
            ret_type = convert_type(item.ret)
            ty = TyScheme(item.generics, FunTy(arg_types, ret_type))
            function_declarations[item.name] = ty
    return function_declarations

def convert_type(parsed_type: Type):
    if isinstance(parsed_type(EnumType)):
        return EnumTy(parsed_type.name, [convert_type(gen) for gen in parsed_type.generics])
    elif isinstance(parsed_type, FunctionType):
        return FunTy([convert_type(arg) for arg in parsed_type.args], convert_type(parsed_type.ret))
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
        
    
            

