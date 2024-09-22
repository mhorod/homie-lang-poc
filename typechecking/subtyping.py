from typechecking.types import *

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
    if isinstance(t1, ErrorTy) or isinstance(t2, ErrorTy):
        return ErrorTy()
    elif t1 is None and t2 is None:
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
    elif isinstance(t1, DisTy) and isinstance(t2, DisTy):
        if t1.name == t2.name and t1.generic_types == t2.generic_types:
            return DisTy(t1.name, t1.generic_types, find_superpattern(t1.pattern, t2.pattern))
        else:
            return ErrorTy()
    else:
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
    if isinstance(sub, DisTy) and isinstance(sup, DisTy):
        return sub.name == sup.name and sub.generic_types == sup.generic_types and is_subpattern(sub.pattern, sup.pattern)
    return False
