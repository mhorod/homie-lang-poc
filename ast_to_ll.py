from dataclasses import dataclass
import tree
import compiler
import sys
from typechecker import TypingContext, EnumDeclaration,VariantDeclaration, EnumTy
import typechecker

@dataclass
class LLContext:
    var_to_id: dict[str, int]
    arg_to_id: dict[str, int]
    enum_defs: dict[str, EnumDeclaration]


def to_ll(program: tree.ProgramType, ctx: TypingContext):
    ll = []
    for item in program.items:
        if isinstance(item, tree.Fun):
            ll.append(fun_to_ll(item, ctx))
        elif isinstance(item, tree.EnumNode):
            for i, variant in enumerate(item.branches):
                ll.append(compiler.constructor(item.name, i, len(variant.args)))
    return compiler.Program(ll)


def var_to_ll(var: tree.Var, ctx: LLContext):
    if var.name in ctx.var_to_id:
        return compiler.Var(ctx.var_to_id[var.name])
    elif var.name in ctx.arg_to_id:
        return compiler.Arg(ctx.arg_to_id[var.name])
    else:
        return compiler.FunName(var.name)

def fun_inst_to_ll(fun_inst: tree.FunInstantiation, ctx: LLContext):
    return compiler.FunName(fun_inst.name)

def call_to_ll(call: tree.Call, ctx: LLContext):
    args = [expr_to_ll(arg, ctx) for arg in call.arguments]
    fun = expr_to_ll(call.fun, ctx)
    return compiler.Call(fun, args)

def member_to_ll(member: tree.Member, ctx: LLContext):
    enum_def = ctx.enum_defs[member.expr.ty.name]
    variant_def = enum_def.get_variant(member.expr.ty.pattern.name)
    arg_id = variant_def.arg_index(member.member_name)
    return compiler.Member(expr_to_ll(member.expr, ctx), arg_id)

def return_to_ll(ret: tree.Return, ctx: LLContext):
    return compiler.Return(expr_to_ll(ret.expr, ctx))


def let_to_ll(let: tree.Let, ctx: LLContext):
    var_id = ctx.var_to_id[let.name]
    return compiler.Let(var_id, expr_to_ll(let.value, ctx))


def pattern_to_ll(ty: EnumTy, pattern: tree.Pattern | None, ctx: LLContext):
    if pattern is None:
        return None
    enum_def = ctx.enum_defs[ty.name]
    variant_def = enum_def.get_variant(pattern.name)
    children = []
    for (pattern_part, arg) in zip(pattern.args, variant_def.args):
        arg_ty = typechecker.substitute(arg.ty, ty.generic_types)
        if not isinstance(arg_ty, EnumTy):
            children.append(None)
        else: 
            children.append(pattern_to_ll(arg_ty, pattern_part, ctx))
    variant_id = enum_def.get_variant_id(pattern.name)
    return compiler.Pattern(variant_id, children)


def fit_to_ll(fit: tree.Fit, ctx: LLContext):
    obj = expr_to_ll(fit.var, ctx)
    children = [compiler.FitBranch (
        pattern_to_ll(fit.var.ty, branch.left, ctx), 
        expr_to_ll(branch.right, ctx)
    ) for branch in fit.branches]
    return compiler.Fit(obj, children)

def enum_cons_to_ll(cons: tree.EnumConstructor, ctx:LLContext):
    enum_def = ctx.enum_defs[cons.enum_name]
    if enum_def.get_variant(cons.variant_name).get_arg_count() == 0:
        return compiler.Create(enum_def.get_variant_id(cons.variant_name), [])
    else: 
        return compiler.FunName(compiler.constructor_name(cons.enum_name, enum_def.get_variant_id(cons.variant_name)))
    

def expr_to_ll(expr: tree.Expr, ctx: LLContext):
    if isinstance(expr, tree.Var):
        return var_to_ll(expr, ctx)
    elif isinstance(expr, tree.FunInstantiation):
        return fun_inst_to_ll(expr, ctx)
    elif isinstance(expr, tree.Call):
        return call_to_ll(expr, ctx)
    elif isinstance(expr, tree.Member):
        return member_to_ll(expr, ctx)
    elif isinstance(expr, tree.Return):
        return return_to_ll(expr, ctx)
    elif isinstance(expr, tree.Fit):
        return fit_to_ll(expr, ctx)
    elif isinstance(expr, tree.Let):
        return let_to_ll(expr, ctx)
    elif isinstance(expr, tree.EnumConstructor):
        return enum_cons_to_ll(expr, ctx)
    else:
        raise Exception(f"Unexpected tree node: {expr}")



def fun_to_ll(fun: tree.Fun, ty_ctx: TypingContext):
    local_var_count = 0
    var_to_id = {}

    for expr in fun.body.expressions:
        if isinstance(expr, tree.Let):
            if expr.name not in var_to_id:
                var_to_id[expr.name] = local_var_count
                local_var_count += 1

    arg_to_id = {arg.name: i for (i, arg) in enumerate(fun.arguments)}

    ctx = LLContext(var_to_id, arg_to_id, ty_ctx.enums)
    body = [compiler.Ignore(expr_to_ll(expr, ctx)) if not isinstance(expr, tree.Return) and not isinstance(expr, tree.Let) and not hasattr(expr, "ty") else expr_to_ll(expr, ctx) for expr in fun.body.expressions]
    return compiler.Fun(fun.name, local_var_count, body)
    

    

