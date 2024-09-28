from dataclasses import dataclass

from parsing.combinators import *
from tree import *
from tokens import *

@dataclass
class FunctionCallOperator:
    kind = 0

def make_expr(parts):
    print("MAKING EXPR: ", parts)
    if isinstance(parts[0], OperatorNode):
        msg = Message(parts[0].location, f"Expression cannot begin with an operator")
        return Result.Err([Error(msg)])

    new_parts = []
    unwrapped = unwrap_tuple_like(parts[0])
    if unwrapped.status != ResultStatus.Ok:
        return unwrapped
    else:
        new_parts.append(unwrapped.parsed)

    print("BEFORE: ", parts)
    print("AFTER: ", new_parts)
    print()

    for i in range(1, len(parts)):
        if not isinstance(new_parts[-1], OperatorNode) and not isinstance(parts[i], OperatorNode):
            if isinstance(parts[i], TupleLikeNode):
                new_parts.append(OperatorNode(FunctionCallOperator(), 1, Associativity.LEFT))
            else:
                msg = Message(parts[i].location, "Expected operator or function call")
                return Result.Err([Error(msg)])
        elif isinstance(new_parts[-1], OperatorNode) and isinstance(parts[i], OperatorNode):
            msg = Message(parts[i].location, "Expected expression")
            return Result.Err([Error(msg)])
        new_parts.append(parts[i])

    result = build_expr(new_parts, None)
    if result.status != ResultStatus.Ok:
        return result
    expr, _ = result.parsed
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
    left = unwrap_tuple_like(left)
    if left.status != ResultStatus.Ok:
        return left
    else:
        left = left.parsed

    if operator.name != FunctionCallOperator():
        right = unwrap_tuple_like(right)
        if right.status != ResultStatus.Ok:
            return right
        else:
            right = right.parsed


    if operator.name == FunctionCallOperator():
        node = CallNode(left, right.parts)
        node.location = Location.wrap(left.location, right.location)
        return Result.Ok(node)
    elif operator.name.kind == SymbolKind.Dot:
        if isinstance(right, VarNode):
            node = MemberNode(left, right.name)
            node.location = Location.wrap(left.location, right.location)
            return Result.Ok(node)
        else:
            msg = Message(right.location, f"Expected member name")
            return Result.Err([Error(msg)])
    elif operator.name.kind == SymbolKind.Equals:
        if isinstance(left, (VarNode, MemberNode)):
            node = AssignNode(left, right)
            node.location = Location.wrap(left.location, right.location)
            return Result.Ok(node)
        else:
            msg = Message(left.location, f"Can only assign to variables and members")
            return Result.Err([Error(msg)])
    else:
        op = VarNode(operator.name)
        op.location = operator.location
        call_node = CallNode(op, [left, right])
        call_node.location = Location.wrap(left.location, right.location)
        return Result.Ok(call_node)


def unwrap_tuple_like(node: TupleLikeNode):
    if isinstance(node, TupleLikeNode):
        if len(node.parts) != 1:
            msg = Message(node.location, f"Unexpected function call syntax")
            return Result.Err([Error(msg)])
        else:
            return Result.Ok(node.parts[0])
    else:
        return Result.Ok(node)

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
