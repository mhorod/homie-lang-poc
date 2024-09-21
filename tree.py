from __future__ import annotations
from typing import *

from dataclasses import dataclass
from enum import Enum, auto

import ast

class ASTNodeKind(Enum):
    ProgramType = auto()
    Fit = auto()
    FitBranch = auto()
    Pattern = auto()
    Let = auto()
    Enum = auto()
    EnumBranch = auto()
    Arg = auto()
    EnumType = auto()
    FunctionType = auto()
    Block = auto()
    Fun = auto()
    Call = auto()
    Value = auto()
    Return = auto()
    TypePath = auto()
    ObjPath = auto()

type Type = EnumType | FunctionType | WildcardType

@dataclass
class WildcardType:
    pass

@dataclass
class ProgramType:
    kind = ASTNodeKind.ProgramType
    items: list

    def exec(self, context=None):
        context = context if context is not None else Context()
        for item in self.items:
            item.exec(context)

@dataclass
class Write:
    value: str
    def __init__(self, value: str):
        self.value = ast.literal_eval(value)

@dataclass
class EnumType:
    kind = ASTNodeKind.EnumType
    name: str
    generics: List[Type]


@dataclass
class TypePath:
    kind = ASTNodeKind.TypePath
    parts: List[EnumType]

    def exec(self, context: Context):
        return Call(self, []).exec(context)

@dataclass
class EnumConstructor:
    enum_name: str
    generics: List[Type]
    variant_name: str

    def exec(self, ctx):
        return Call(self, []).exec(ctx) 

@dataclass
class Var:
    name: str
    def exec(self, context: Context):
        print(f"Searching for object {self.name}")
        if self.name in context.stack[-1]:
            return context.stack[-1][self.name]
        elif self.name in context.functions:
            return context.functions[self.name]
        else:
            print(f"Cannot find name {self.name}")

@dataclass
class Member:
    expr: Expr
    member_name: str

    def exec(self, context: Context):
        return self.expr.exec(context).children[self.member_name]

@dataclass
class FunctionType:
    kind = ASTNodeKind.FunctionType
    args: List[Type]
    ret: Type

@dataclass
class Arg:
    kind = ASTNodeKind.Arg
    name: str
    type: Type

class Associativity(Enum):
    NONE = auto()
    LEFT = auto()
    RIGHT = auto()

@dataclass
class Operator:
    kind: Any
    precedence: int
    associativity: Associativity


# Enum
@dataclass
class EnumBranch:
    kind = ASTNodeKind.EnumBranch
    name: str
    args: List[Arg]


@dataclass
class EnumNode:
    kind = ASTNodeKind.Enum
    name: str
    generic_names: List[str]
    branches: List[EnumBranch]

    def exec(self, context: Context):
        print(f"Enum def: {self}")
        context.enums[self.name] = self

    

# Match
@dataclass
class Pattern:
    kind = ASTNodeKind.Pattern
    name: str
    args: List[Pattern | Value | None]


def fits(p: Pattern | Value | None, obj: object):
    if p is None:
        return True
    elif isinstance(p, Value):
        return obj == p.val
    elif isinstance(p, Pattern):
        if not isinstance(obj, Object):
            return False
        if obj.branch.name != p.name:
            return False
        for (arg_def, val) in zip(obj.branch.args, p.args):
            child = obj.children[arg_def.name]
            if not fits(val, child):
                return False
        return True

@dataclass
class FitBranch:
    kind = ASTNodeKind.FitBranch
    left: Pattern | Value | None
    right: Expr
    
@dataclass
class Fit:
    kind = ASTNodeKind.Fit
    var: Expr 
    branches: List[FitBranch]

    def exec(self, context: Context):
        obj = self.var.exec(context)
        for branch in self.branches:
            if fits(branch.left, obj):
                return branch.right.exec(context) 
        


# Expr
type Expr = Block | Fit | Let | Return

@dataclass
class Return:
    kind = ASTNodeKind.Return
    expr: Expr

    def exec(self, context: Context):
        result = self.expr.exec(context)
        context.exiting_function = True
        return result
        

@dataclass
class Block:
    kind = ASTNodeKind.Block
    expressions: List[Expr]

    def exec(self, context: Context):
        for expr in self.expressions:
            result = expr.exec(context)
            if context.exiting_function:
                return result



@dataclass
class Let:
    kind = ASTNodeKind.Let
    name: str
    value: Expr

    def exec(self, context: Context):
        context.stack[-1][self.name] = self.value.exec(context)

@dataclass
class Value:
    kind = ASTNodeKind.Value
    val: object

    def exec(self, context: Context):
        return self.val

# Fun

@dataclass
class Fun:
    kind = ASTNodeKind.Fun
    name: str
    generics: List[str]
    arguments: List[Arg]
    ret: Type
    body: Expr

    def exec(self, context: Context):
        context.functions[self.name] = self
        

@dataclass
class FunInstantiation:
    name: str
    generics: List[Type]

    def exec(self, context: Context):
        return context.functions[self.name]

@dataclass
class Call:
    kind = ASTNodeKind.Call
    fun: Expr | EnumConstructor
    arguments: List[Expr]

    def exec(self, context: Context):
        if isinstance(self.fun, EnumConstructor):
            return self.exec_create_call(context)
        else:
            return self.exec_function_call(context)
        
        
    def exec_function_call(self, context: Context):
        frame = {}
        fun_def = self.fun.exec(context)
        for (arg_expr, arg_def) in zip(self.arguments, fun_def.arguments):
            frame[arg_def.name] = arg_expr.exec(context)
        context.stack.append(frame)
        result = fun_def.body.exec(context)
        context.stack.pop()
        context.exiting_function = False
        return result

    def exec_create_call(self, context: Context):
        enum_def = context.enums[self.fun.enum_name]
        branch_def = next(b for b in enum_def.branches if b.name == self.fun.variant_name)
        children = {}
        for (arg_expr, arg_def) in zip(self.arguments, branch_def.args):
            children[arg_def.name] = arg_expr.exec(context)
        
        obj = Object(enum_def, branch_def, children)

        return obj



@dataclass
class Object:
    enum_def: Enum
    branch: EnumBranch
    children: dict[str, object]

    def __str__(self):
        children_str = ", ".join([f"{child_name}: {child}" for child_name, child in self.children.items()])
        if children_str:
            children_str = f"({children_str})"
        return f"{self.branch.name}{children_str}"



class Context:
    functions: Dict[str, Fun]
    enums: Dict[str, Enum]
    def __init__(self):
        self.stack = [{}]
        self.functions = {}
        self.enums = {}
        self.exiting_function = False

if __name__ == "__main__":
    context = Context()

    program = Block([
        EnumNode("Bool", [], [
            EnumBranch("True", []),
            EnumBranch("False", []),
        ]),
        Fun("hehe", [], [Arg("b", EnumType("Bool", []))], EnumType("None", []), Block([
            Return(Fit(ObjPath(["b"]), [
                FitBranch(Pattern("True", []), Value("Tak")),
                FitBranch(Pattern("False", []), Value("Nie")),
            ])),
        ])),
        Return(Call(ObjPath(["hehe"]), [Create(TypePath([EnumType("Bool", []), EnumType("False", [])]), [])])),
    ])

    print(program.exec(context))