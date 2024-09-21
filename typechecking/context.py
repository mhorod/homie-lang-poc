from __future__ import annotations
from typechecking.types import *

class TypingContextFrame:
    def __init__(self):
        self.locals = {}
        self.generic_nums_ctx = {}
    
    def add_local_var(self, name: str, ty: Ty):
        self.locals[name] = ty
    
    def has_local_var(self, name: str) -> bool:
        return name in self.locals

    def get_local_var_type(self, name: str) -> Ty:
        return self.locals[name]
    
    def has_generic(self, name):
        return name in self.generic_nums_ctx
    
    def get_generic(self, name):
        return self.generic_nums_ctx[name]


class TypingContext:
    def __init__(self, dises, functions):
        self.dises = dises
        self.functions = functions
        self.simple_types = {}
        self.stack = [TypingContextFrame()]

    def push(self):
        self.stack.append(TypingContextFrame())

    def pop(self):
        self.stack.pop()

    def has_generic(self, name) -> bool:
        for frame in self.stack[::-1]:
            if frame.has_generic(name):
                return True
        return False
    
    def get_generic(self, name):
        for frame in self.stack[::-1]:
            if frame.has_generic(name):
                return frame.get_generic(name)
        return False


    def has_dis(self, name) -> bool:
        return name in self.dises
    
    def get_dis(self, name) -> DisDeclaration:
        return self.dises[name]

    def has_function(self, name) -> bool:
        return name in self.functions

    def get_function(self, name) -> FunctionDeclaration:
        return self.functions[name]
    
    def add_local_var(self, name: str, ty: Ty):
        self.stack[-1].locals[name] = ty
    
    def has_local_var(self, name: str) -> bool:
        for frame in self.stack[::-1]:
            if frame.has_local_var(name):
                return True
        return False

    def get_local_var_type(self, name: str) -> Ty:
        for frame in self.stack[::-1]:
            if frame.has_local_var(name):
                return frame.get_local_var_type(name)

    def add_generics(self, generics: List[str]):
        for i, name in enumerate(generics):
            self.stack[-1].generic_nums_ctx[name] = i