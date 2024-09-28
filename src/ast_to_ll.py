from dataclasses import dataclass
import tree
import compiler
import sys
from typechecking.typechecker import TypingContext, DisDeclaration, DisTy
import typechecking.typechecker as typechecker

@dataclass
class LLContext:
    var_to_id: dict[str, int]
    arg_to_id: dict[str, int]
    enum_defs: dict[str, DisDeclaration]


def to_ll(program: tree.ProgramNode, ctx: TypingContext):
    ll = []
    for item in program.items:
        if isinstance(item, tree.FunNode):
            ll.append(fun_to_ll(item, ctx))
        elif isinstance(item, tree.DisNode):
            for i, variant in enumerate(item.variants):
                ll.append(compiler.constructor(item.name.text, i + 1, len(variant.args)))
    return compiler.Program(ll)


def var_to_ll(var: tree.VarNode, ctx: LLContext):
    name = var.name.text
    if name in ctx.var_to_id:
        return compiler.VarArg(compiler.VarAddress(ctx.var_to_id[name]))
    elif name in ctx.arg_to_id:
        return compiler.VarArg(compiler.ArgAddress(ctx.arg_to_id[name]))
    else:
        return compiler.FunName(var.name.text)

def var_adress_to_ll(var: tree.VarNode, ctx: LLContext):
    name = var.name.text
    if name in ctx.var_to_id:
        return compiler.VarAddress(ctx.var_to_id[name])
    elif name in ctx.arg_to_id:
        return compiler.ArgAddress(ctx.arg_to_id[name])
    else:
        raise Exception(f"Not addressable {var}")

def fun_inst_to_ll(fun_inst: tree.FunInstNode, ctx: LLContext):
    return compiler.FunName(fun_inst.name.text)

def call_to_ll(call: tree.CallNode, ctx: LLContext):
    args = [expr_to_ll(arg, ctx) for arg in call.arguments]
    fun = expr_to_ll(call.fun, ctx)
    return compiler.Call(fun, args)

def member_address_to_ll(member: tree.MemberNode, ctx: LLContext):
    enum_def = ctx.enum_defs[member.expr.ty.name]
    variant_def = enum_def.get_variant(member.expr.ty.pattern.name)
    arg_id = variant_def.arg_index(member.member_name.text)
    return compiler.MemberAddress(expr_to_ll(member.expr, ctx), arg_id)

def member_to_ll(member: tree.MemberNode, ctx: LLContext):
    return compiler.Member(member_address_to_ll(member, ctx))

def ret_to_ll(ret: tree.RetNode, ctx: LLContext):
    return compiler.Return(expr_to_ll(ret.expr, ctx))


def let_to_ll(let: tree.LetNode, ctx: LLContext):
    var_id = ctx.var_to_id[let.name.text]
    return compiler.Let(var_id, expr_to_ll(let.value, ctx))


def pattern_to_ll(ty: DisTy, pattern: tree.Pattern | None, ctx: LLContext):
    if pattern is None:
        return None
    enum_def = ctx.enum_defs[ty.name]
    variant_def = enum_def.get_variant(pattern.name.text)
    children = []
    for (pattern_part, arg) in zip(pattern.args, variant_def.args):
        arg_ty = typechecker.substitute(arg.ty, ty.generic_types)
        if not isinstance(arg_ty, DisTy):
            children.append(None)
        else:
            children.append(pattern_to_ll(arg_ty, pattern_part, ctx))
    variant_id = enum_def.get_variant_id(pattern.name.text)
    return compiler.Pattern(variant_id, children)


def fit_to_ll(fit: tree.FitNode, ctx: LLContext):
    obj = expr_to_ll(fit.expr, ctx)
    children = [compiler.FitBranch (
        pattern_to_ll(fit.expr.ty, branch.left, ctx),
        expr_to_ll(branch.right, ctx)
    ) for branch in fit.branches]
    return compiler.Fit(obj, children)

def enum_cons_to_ll(cons: tree.DisConstructorNode, ctx:LLContext):
    enum_def = ctx.enum_defs[cons.name.text]
    if enum_def.get_variant(cons.variant_name.text).get_arg_count() == 0:
        return compiler.Create(enum_def.get_variant_id(cons.variant_name.text), [])
    else:
        return compiler.FunName(compiler.constructor_name(cons.name.text, enum_def.get_variant_id(cons.variant_name.text)))

def write_to_ll(write: tree.Write, ctx: LLContext):
    return compiler.Print(write.value)


def expr_to_ll(expr: tree.ExprNode, ctx: LLContext):
    if isinstance(expr, tree.VarNode):
        return var_to_ll(expr, ctx)
    elif isinstance(expr, tree.FunInstNode):
        return fun_inst_to_ll(expr, ctx)
    elif isinstance(expr, tree.CallNode):
        return call_to_ll(expr, ctx)
    elif isinstance(expr, tree.MemberNode):
        return member_to_ll(expr, ctx)
    elif isinstance(expr, tree.RetNode):
        return ret_to_ll(expr, ctx)
    elif isinstance(expr, tree.FitNode):
        return fit_to_ll(expr, ctx)
    elif isinstance(expr, tree.LetNode):
        return let_to_ll(expr, ctx)
    elif isinstance(expr, tree.DisConstructorNode):
        return enum_cons_to_ll(expr, ctx)
    elif isinstance(expr, tree.Write):
        return write_to_ll(expr, ctx)
    elif isinstance(expr, tree.ValueNode):
        return value_to_ll(expr, ctx)
    elif isinstance(expr, tree.AssignNode):
        return assign_to_ll(expr, ctx)
    else:
        raise Exception(f"Unexpected tree node: {expr}")

def assign_to_ll(assign: tree.AssignNode, ty_ctx: TypingContext):
    if isinstance(assign.var, tree.VarNode):
        lhs = var_adress_to_ll(assign.var, ty_ctx)
    elif isinstance(assign.var, tree.MemberNode):
        lhs = member_address_to_ll(assign.var, ty_ctx)
    else:
        raise Exception(f"Unexpected assignment: {assign}")
    return compiler.Assign(lhs, expr_to_ll(assign.expr, ty_ctx))

def fun_to_ll(fun: tree.FunNode, ty_ctx: TypingContext):
    local_var_count = 0
    var_to_id = {}

    for expr in fun.body.statements:
        if isinstance(expr, tree.LetNode):
            if expr.name.text not in var_to_id:
                var_to_id[expr.name.text] = local_var_count
                local_var_count += 1

    arg_to_id = {arg.name.text: i for (i, arg) in enumerate(fun.args)}

    ctx = LLContext(var_to_id, arg_to_id, ty_ctx.dises)
    body = [expr_to_ll(expr, ctx) for expr in fun.body.statements]
    return compiler.Fun(fun.name.text, local_var_count, body)

def value_to_ll(val: tree.ValueNode, ty_ctx: TypingContext):
    return compiler.IntValue(val.token.text)
