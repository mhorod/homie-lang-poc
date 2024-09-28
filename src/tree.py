from __future__ import annotations
from typing import *

from dataclasses import dataclass
from enum import Enum, auto

from source import Location
from tokens import Token
import ast

def buildable(cls):
    fields = cls.__annotations__
    class Builder:
        def __init__(self):
            self.values = {field : None for field in fields}

        def build(self, location: Location):
            obj = cls(*self.values.values())
            obj.location = location
            return obj

    def add_builder_method(name):
        def set_field(self, value):
            self.values[name] = value
        setattr(Builder, name, set_field)

    for name in cls.__annotations__:
        add_builder_method(name)

    cls.Builder = Builder
    return cls



type TypeNode = DisTypeNode | FunctionTypeNode | WildcardTypeNode

class Node:
    location: Location

@buildable
@dataclass
class WildcardTypeNode(Node):
    pass

@buildable
@dataclass
class ProgramNode(Node):
    items: list

@dataclass
class Write:
    value: str
    def __init__(self, value: str):
        self.value = ast.literal_eval(value)

@buildable
@dataclass
class GenericParamsNode(Node):
    params: List[Token]

@buildable
@dataclass
class DisTypeNode(Node):
    name: Token
    generics: List[Type]


@buildable
@dataclass
class DisConstructorNode(Node):
    name: str
    generics: List[Type]
    variant_name: str

@buildable
@dataclass
class VarNode(Node):
    name: str

@buildable
@dataclass
class MemberNode(Node):
    expr: ExprNode
    member_name: Token

@buildable
@dataclass
class FunctionTypeNode:
    args: List[Type]
    ret: Type

@buildable
@dataclass
class ArgNode:
    location: Location
    name: str
    type: Type

class Associativity(Enum):
    NONE = auto()
    LEFT = auto()
    RIGHT = auto()

@buildable
@dataclass
class OperatorNode(Node):
    name: Token
    precedence: int
    associativity: Associativity

@buildable
@dataclass
class DisVariantNode:
    location: Location
    name: Token
    args: List[ArgNode]


@buildable
@dataclass
class DisNode(Node):
    name: Token
    generics: GenericParamsNode
    variants: List[DisVariantNode]

    def get_variant_node(self, name: str):
        for v in self.variants:
            if v.name.text == name:
                return v

@buildable
@dataclass
class PatternNode(Node):
    name: Token
    args: List[Pattern | Value | None]

@buildable
@dataclass
class FitBranchNode(Node):
    location: Location
    left: Pattern | Value | None
    right: ExprNode

@buildable
@dataclass
class FitNode(Node):
    location: Location
    expr: ExprNode
    branches: List[FitBranchNode]

type ExprNode = FitNode
type StatementNode = ExprNode | RetNode | BlockNode

@buildable
@dataclass
class RetNode(Node):
    expr: ExprNode

@buildable
@dataclass
class BlockNode(Node):
    statements: List[StatementNode]


@buildable
@dataclass
class LetNode(Node):
    name: Token
    value: ExprNode

@buildable
@dataclass
class ValueNode(Node):
    token: Token

@buildable
@dataclass
class FunNode(Node):
    name: str
    generics: GenericParamsNode
    args: List[ArgNode]
    ret: Type
    body: BlockNode


@buildable
@dataclass
class FunInstNode(Node):
    name: Token
    generics: List[Type]


@buildable
@dataclass
class CallNode(Node):
    fun: ExprNode | DisConstructorNode
    arguments: List[ExprNode]
