from dataclasses import dataclass

from parsing.combinators import *
from tree import *
from tokens import *

@dataclass
class FunctionCallOperator:
    kind = 0

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
        call_node =  CallNode(parts[0], parts[1:])
        call_node.location = Location.wrap(parts[0].location, parts[-1].location)
        return call_node

def make_expr(parts):
    if isinstance(parts[0], OperatorNode):
        msg = Message(parts[0].location, f"Expression cannot begin with an operator")
        return Result.Err([Error(msg)])

    new_parts = [parts[0]]
    for i in range(1, len(parts)):
        if not isinstance(new_parts[-1], OperatorNode) and not isinstance(parts[i], OperatorNode):
            new_parts.append(OperatorNode(FunctionCallOperator(), 1, Associativity.LEFT))
        elif isinstance(new_parts[-1], OperatorNode) and isinstance(parts[i], OperatorNode):
            msg = Message(parts[i].location, "Expected expression")
            return Result.Err([Error(msg)])
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
    if operator.name == FunctionCallOperator():
        return Result.Ok(FunctionCall(left, right))
    elif operator.name.kind == SymbolKind.Dot:
        if isinstance(right, VarNode):
            node = MemberNode(left, right.name)
            node.location = Location.wrap(left.location, right.location)
            return Result.Ok(node)
        else:
            msg = Message(right.location, f"Expected member name")
            return Result.Err([Error(msg)])
    else:
        op = VarNode(operator.name)
        op.location = operator.location
        call_node = CallNode(op, [left, right])
        call_node.location = Location.wrap(left.location, right.location)
        return Result.Ok(call_node)

def flatten_functions(expr):
    if isinstance(expr, FunctionCall):
        return flatten_functions(expr.flatten())
    elif isinstance(expr, CallNode):
        new_node = CallNode(flatten_functions(expr.fun), [flatten_functions(arg) for arg in expr.arguments])
        new_node.location = expr.location
        return new_node
    elif isinstance(expr, MemberNode):
        new_node = MemberNode(flatten_functions(expr.expr), expr.member_name)
        new_node.location = expr.location
        return new_node
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

    if left.name.kind == right.name.kind:
        return left.associativity == Associativity.RIGHT
    else:
        return left.precedence > right.precedence
