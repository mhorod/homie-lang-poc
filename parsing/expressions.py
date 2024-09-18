from dataclasses import dataclass

from parsing.combinators import *
from tree import *
from tokens import *

@dataclass
class FunctionCallOperator:
    pass

class FunctionCall:
    def __init__(self, left, right):
        self.left = left
        self.right = right
    
    def to_list(self):
        if isinstance(self.left, FunctionCall):
            return self.left.to_list() + [self.right]
        else:
            return [self.left, self.right]
        
    def flatten(self):
        parts = self.to_list()
        return Call(parts[0], parts[1:])
    
def make_expr(parts):
    if isinstance(parts[0], Operator):
        return Result.Err(f"Expected expression, found {parts[0]}")

    new_parts = [parts[0]]
    for i in range(1, len(parts)):
        if not isinstance(new_parts[-1], Operator) and not isinstance(parts[i], Operator):
            new_parts.append(Operator(FunctionCallOperator(), 1, Associativity.LEFT))
        elif isinstance(new_parts[-1], Operator) and isinstance(parts[i], Operator):
            return Result.Err(f"Expected expression, found {parts[i]}")
        new_parts.append(parts[i])

    result = build_expr(new_parts, None)
    if result.status != ResultStatus.Ok:
        return result
    expr, _ = result.parsed
    expr = flatten_functions(expr)
    return Result.Ok(expr)

def build_expr(nodes, last_operator):    
    left, nodes = nodes[0], nodes[1:]
    while nodes and right_op_first(last_operator, nodes[0]):
        operator, nodes = nodes[0], nodes[1:]
        sub_result = build_expr(nodes, operator)
        if sub_result.status != ResultStatus.Ok:
            return sub_result
        else:
            right, nodes = sub_result.parsed
        left_result = build_node(left, operator, right)
        if left_result.status != ResultStatus.Ok:
            return left_result
        else:
            left = left_result.parsed
    return Result.Ok((left, nodes))

def build_node(left, operator, right):
    if operator.kind == FunctionCallOperator():
        return Result.Ok(FunctionCall(left, right))
    elif operator.kind == SymbolKind.Dot:
        if isinstance(right, Var):
            return Result.Ok(Member(left, right.name))
        else:
            return Result.Err(f"Expected member name, found {right}")
    else:
        return Result.Ok(Call(operator.kind, left, right))

def flatten_functions(expr):
    if isinstance(expr, FunctionCall):
        return flatten_functions(expr.flatten())
    elif isinstance(expr, Call):
        return Call(flatten_functions(expr.fun), [flatten_functions(arg) for arg in expr.arguments])
    elif isinstance(expr, Member):
        return Member(flatten_functions(expr.expr), expr.member_name)
    else:
        return expr



def right_op_first(left, right):
    '''
    Returns true if expression of form x {left} y {right} z
    evaluates to x {left} (y {right} z).

    This happens when {right} binds more tightly than {left}.
    or they are the same right-associative operator
    '''
    if left is None:
        return True

    if left.kind == right.kind:
        return left.associativity == Associativity.RIGHT
    else:
        return left.precedence > right.precedence