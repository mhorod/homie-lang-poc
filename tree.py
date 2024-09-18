from __future__ import annotations
from typing import *

from dataclasses import dataclass
from enum import Enum, auto

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
class ObjPath:
    kind = ASTNodeKind.ObjPath
    parts: List[str]

    def exec(self, context: Context):
        print(f"Searching for object {self.parts}")
        if len(self.parts) == 1:
            if self.parts[0] in context.functions:
                return context.functions[self.parts[0]]
        
        obj = context.stack[-1][self.parts[0]]
        for part in self.parts[1:]:
            obj = obj.children[part]
        return obj

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
    print(f"fitting {p}, {obj}")
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
            print("is my child stuped: ", val, child, fits(val, child))
            if not fits(val, child):
                return False
        return True
    else:
        print("wtaf this pattern: ", p, type(p))

@dataclass
class FitBranch:
    kind = ASTNodeKind.FitBranch
    left: Pattern | Value | None
    right: Expr
    
@dataclass
class Fit:
    kind = ASTNodeKind.Fit
    var: ObjPath 
    branches: List[FitBranch]

    def exec(self, context: Context):
        obj = self.var.exec(context)
        for branch in self.branches:
            print(f"Matching pattern: {branch.left}")
            if fits(branch.left, obj):
                print("It's a match!")
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
        print(f"Returning {result}")
        return result
        

@dataclass
class Block:
    kind = ASTNodeKind.Block
    expressions: List[Expr]

    def exec(self, context: Context):
        print("Executing block")
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
        print(f"Setting {self.name}'s value")
        context.stack[-1][self.name] = self.value.exec(context)

@dataclass
class Value:
    kind = ASTNodeKind.Value
    val: object

    def exec(self, context: Context):
        print(f"Loading value: {self.val}")
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
        print(f"Creating function: {self.name}")
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
    fun: ObjPath | EnumConstructor
    arguments: List[Expr]

    def exec(self, context: Context):
        if isinstance(self.fun, EnumConstructor):
            return self.exec_create_call(context)
        else:
            return self.exec_function_call(context)
        
        
    def exec_function_call(self, context: Context):
        print(f"Calling function: {self.fun} {self.arguments}")
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

        print(f"Creating object: {obj}")
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