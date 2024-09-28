from __future__ import annotations
from typing import *

from dataclasses import dataclass
from enum import Enum, auto

type Expr = Create | Fit | FunName | Call | Var | Arg | Member

type Statement = Let | Return

@dataclass
class IntValue:
    """
    Loads value to rax
    """
    value: int

    def to_asm(self, ctx: AsmContext):
        return f"mov rax, {self.value}"

    def pretty_print(self, indent=1):
        return f"{self.value}"

@dataclass
class FitBranch:
    """checks if object on stack fits the pattern and if so, leaves content's result in rax"""
    pattern: Pattern | None
    content: Expr

    def to_asm(self, ctx: AsmContext, fit_end: str):
        branch_end = ctx.unique_id("branch_end")
        if self.pattern is None:
            return f"""
                {self.content.to_asm(ctx)}
                jmp {fit_end}
            """
        else:
            return f"""
                mov rax, [rsp]
                {self.pattern.to_asm(ctx)}
                jnz {branch_end}
                {self.content.to_asm(ctx)}
                jmp {fit_end}
                {branch_end}:
            """

    def pretty_print(self, depth = 0) -> str:
        return f"{"_" if self.pattern is None else self.pattern.pretty_print()} => {self.content.pretty_print(depth + 1)}"

@dataclass
class Fit:
    """leaves result in rax"""
    obj: Expr
    branches: List[FitBranch]

    def to_asm(self, ctx: AsmContext):
        fit_end = ctx.unique_id("fit_end")
        return f"""
            {self.obj.to_asm(ctx)}
            push rax
            {'\n'.join(branch.to_asm(ctx, fit_end) for branch in self.branches[:-1])}
            {self.branches[-1].content.to_asm(ctx)}
            {fit_end}:
            add rsp, 8
        """

    def pretty_print(self, depth = 0) -> str:
        return f"fit {self.obj.pretty_print(depth + 1)} {{{br(depth)}{br(depth).join(b.pretty_print(depth + 1) + "," for b in self.branches)} {br(depth - 1)}}}"




@dataclass
class Pattern:
    """takes object in rax, destroys it. iff pattern matches object ZF is set"""
    type_id: int
    children: List[Pattern | None]

    def to_asm(self, ctx: AsmContext) -> str:
        match_start = ctx.unique_id("match")
        match_end = ctx.unique_id("match_end")
        after_match_end = ctx.unique_id("after_match_end")

        inner_match = ""
        gap = 0

        for child in self.children:
            if child is None:
                gap += 8
            else:
                inner_match += f"""
                    add qword [rsp], {gap}
                    mov rax, [rsp]
                    mov rax, [rax]
                    {child.to_asm(ctx)}
                    jnz {match_end}
                """
                gap = 8

        if inner_match == "":
            return f"""
                {get_variant_from_rax()}
                cmp rax, {self.type_id}
            """

        return f"""
            {match_start}:
                mov rbx, rax
                {get_variant_from_rax()}
                cmp rax, {self.type_id}
                jne {after_match_end}
                mov rax, rbx
                {get_addr_from_rax()}
                push rax
                {inner_match}
            {match_end}:
                pop rax
            {after_match_end}:
        """
    def pretty_print(self, depth = 0) -> str:
        return ' '.join([f"<{self.type_id}>"] + ['_' if c is None else c.pretty_print(depth + 1) for c in self.children])

def br(depth):
    return "\n" + (depth + 1) * " "

@dataclass
class Fun:
    name: str
    local_vars: int
    content: List[Statement]

    def to_asm(self, ctx: AsmContext) -> str:
        ctx.return_token = ctx.unique_id(f"{self.name}_ret")
        ctx.var_count = self.local_vars
        return f"""
            {self.name}:
            mov rbp, rsp
            sub rsp, {self.local_vars * 8}
            {'\n'.join(s.to_asm(ctx) for s in self.content)}
            mov rsp, rbp
            ret
        """

    def pretty_print(self, depth = 0) -> str:
        return f"fun {self.name}[{self.local_vars}] {{{br(depth)}{br(depth).join(s.pretty_print(depth + 1) + ";" for s in self.content)}\n}}"


@dataclass
class Return:
    content: Expr

    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            {self.content.to_asm(ctx)}
            mov rsp, rbp
            ret
        """

    def pretty_print(self, depth = 0) -> str:
        return f"ret {self.content.pretty_print(depth + 1)}"

@dataclass
class Call:
    """calls function and leaves result in rax"""
    function: Expr
    args: List[Expr]

    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            push rbp
            {'\n'.join(f'''
                {arg.to_asm(ctx)}
                push rax
            ''' for arg in reversed(self.args))}
            {self.function.to_asm(ctx)}
            mov rdi, rsp
            call rax
            add rsp, {len(self.args) * 8}
            pop rbp
        """

    def pretty_print(self, depth = 0) -> str:
        return f"({self.function.pretty_print(depth + 1)} {' '.join(arg.pretty_print(depth + 1) for arg in self.args)})"

@dataclass
class Let:
    var: int
    value: Expr

    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            {self.value.to_asm(ctx)}
            mov [rbp - {8 + 8 * self.var}], rax
        """

    def pretty_print(self, depth = 0) -> str:
        return f"let ({self.var}) = {self.value.pretty_print(depth + 1)}"

@dataclass
class FunName:
    name: str
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            mov rax, {self.name}
        """
    def pretty_print(self, depth = 0) -> str:
        return self.name

@dataclass
class Program:
    functions: List[Fun]
    def to_asm(self, ctx: AsmContext) -> str:
        result = f"""
            section .text
            global main
            extern _make_obj0
            extern _make_obj1
            extern _make_obj3
            extern _make_obj7

            {'\n'.join(f.to_asm(ctx) for f in self.functions)}
        """
        return '\n'.join(l for l in (l.strip() for l in result.split('\n')) if l != '')

    def pretty_print(self) -> str:
        return '\n\n'.join(f.pretty_print(0) for f in self.functions)

@dataclass
class ArgAddress:
    i: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            lea rax, [rbp + {8 + 8 * self.i}]
        """
    def pretty_print(self, depth = 0) -> str:
        return f"&[{self.i}]"

@dataclass
class VarAddress:
    var: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            lea rax, [rbp - {8 + 8 * self.var}]
        """
    def pretty_print(self, depth = 0) -> str:
        return f"&({self.var})"

@dataclass
class MemberAddress:
    """returns ith member field address"""
    obj: Expr
    i: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            {self.obj.to_asm(ctx)}
            {get_addr_from_rax()}
            add rax, {8 * self.i}
        """
    def pretty_print(self, depth = 0) -> str:
        return f"&({self.obj.pretty_print(depth)}).{self.i}"

@dataclass
class Deref:
    address: Expr
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            {self.address.to_asm(ctx)}
            mov rax, [rax]
        """
    def pretty_print(self, depth = 0) -> str:
        s = self.address.pretty_print(depth)
        return s[1:] if isinstance(self.address, (ArgAddress, VarAddress, MemberAddress)) else '*' + s

@dataclass
class Assign:
    """assigns *var = obj """
    var: Expr
    obj: Expr
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            {self.var.to_asm(ctx)}
            push rax
            {self.obj.to_asm(ctx)}
            pop rcx
            mov [rcx], rax
        """
    def pretty_print(self, depth = 0) -> str:
        return self.var.pretty_print(depth) + " = " + self.obj.pretty_print(depth)

@dataclass
class Print:
    value: str

    def to_asm(self, ctx: AsmContext):
        str_label = ctx.unique_id("str")
        after_str_label = ctx.unique_id("after_str")
        return f"""
            jmp {after_str_label}
            {str_label}:
            db {', '.join(str(int(b)) for b in self.value.encode('utf-8'))}
            {after_str_label}:
            mov rax, 1
            mov rdi, 1
            mov rsi, {str_label}
            mov rdx, {len(self.value.encode())}
            syscall
        """
    def pretty_print(self, depth = 0) -> str:
        return f"wrt \"{self.value.replace("\n", "\\n").replace("\t", "\\t")}\""

def constructor_name(enum_name: str, variant_id: int):
    return f"__{enum_name}__{variant_id}"

@dataclass
class Create:
    """creates object and puts it in rax"""
    type_id: int
    children: List[Expr]

    def to_asm(self, ctx: AsmContext):
        if len(self.children) == 0:
            return Call(FunName("_make_obj0"), [IntValue(self.type_id)] + self.children).to_asm(ctx)

        if len(self.children) == 1:
            return Call(FunName("_make_obj1"), [IntValue(self.type_id)] + self.children).to_asm(ctx)

        if len(self.children) <= 3:
            padded_children = self.children + [IntValue(0)] * (len(self.children) - 3)
            return Call(FunName("_make_obj3"), [IntValue(self.type_id)] + padded_children).to_asm(ctx)

        if len(self.children) <= 7:
            padded_children = self.children + [IntValue(0)] * (len(self.children) - 7)
            return Call(FunName("_make_obj7"), [IntValue(self.type_id)] + padded_children).to_asm(ctx)

        raise Exception("Object too big to allocate.")

    def pretty_print(self, depth = 0) -> str:
        return f"({' '.join([f"<{self.type_id}>"] + [child.pretty_print(depth + 1) for child in self.children])})"

def constructor(enum_name: str, variant_id: int, no_args: int) -> Fun:
    return Fun(constructor_name(enum_name, variant_id), 0, [Return(Create(variant_id, [Deref(ArgAddress(i)) for i in range(no_args)]))])

def get_addr_from_rax() -> str:
    return f"""
        shl rax, 8
        shr rax, 8
    """

def get_variant_from_rax() -> str:
    return f"""
        shr rax, 56
    """

class AsmContext:
    _id: int
    return_token: str
    var_count: int

    def __init__(self):
        self._id = 0

    def unique_id(self, name: str) -> str:
        self._id += 1
        return f"{name}_{self._id}"

def compile(program: Program) -> str:
    ctx = AsmContext()
    return program.to_asm(ctx)
