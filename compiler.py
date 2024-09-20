from __future__ import annotations
from typing import *

from dataclasses import dataclass
from enum import Enum, auto

type Expr = Create | Fit | FunName | Call | Var | Arg | Member

type Statement = Let | Return



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
            extern _make_obj
            extern heap

            {'\n'.join(f.to_asm(ctx) for f in self.functions)}
        """
        return '\n'.join(l for l in (l.strip() for l in result.split('\n')) if l != '')

    def pretty_print(self) -> str:
        return '\n\n'.join(f.pretty_print(0) for f in self.functions)
    
@dataclass
class Arg:
    i: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            mov rax, [rbp + {8 + 8 * self.i}]
        """
    def pretty_print(self, depth = 0) -> str:
        return f"[{self.i}]"

@dataclass
class Var:
    var: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            mov rax, [rbp - {8 + 8 * self.var}]
        """
    def pretty_print(self, depth = 0) -> str:
        return f"({self.var})"

@dataclass
class Member:
    """returns ith member"""
    obj: Expr
    i: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            {self.obj.to_asm(ctx)}
            {get_addr_from_rax()}
            add rax, {8 * self.i}
            mov rax, [rax]
        """
    def pretty_print(self, depth = 0) -> str:
        return f"({self.obj.pretty_print(depth)}).{self.i}"




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
        create_children = ""
        for child in self.children:
            create_children += f"""
                {child.to_asm(ctx)}
                push rax
            """
        return f"""
                {create_children}
                push qword {len(self.children)}
                push qword {self.type_id}
                call _make_obj
            """
    def pretty_print(self, depth = 0) -> str:
        return f"({' '.join([f"<{self.type_id}>"] + [child.pretty_print(depth + 1) for child in self.children])})"

def constructor(enum_name: str, variant_id: int, no_args: int) -> Fun:
    return Fun(constructor_name(enum_name, variant_id), 0, [Return(Create(variant_id, [Arg(i) for i in range(no_args)]))])

def get_addr_from_rax() -> str:
    return f"""
        and rax, r12
        sub rax, [heap]
        neg rax
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