from __future__ import annotations
from dataclasses import dataclass
from typing import List

type Ty = TyVar | FunTy | DisTy | ErrorTy | None | SimpleType

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
class DisDeclaration:
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
class DisTy:
    name: str
    generic_types: List[Ty]
    pattern: TyPattern | None

def substitute(ty: Ty, subst: List[Ty]):
    if isinstance(ty, FunTy):
        arg_types = [substitute(arg, subst) for arg in ty.arg_types]
        result_type = substitute(ty.result_type, subst)
        return FunTy(arg_types, result_type)
    elif isinstance(ty, DisTy):
        generic_types = [substitute(t, subst) for t in ty.generic_types]
        return DisTy(ty.name, generic_types, ty.pattern)
    elif isinstance(ty, TyVar):
        return subst[ty.index]
    else:
        return ty