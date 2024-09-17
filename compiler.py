from __future__ import annotations
from typing import *

from dataclasses import dataclass
from enum import Enum, auto

type Expr = Create | Fit | FunName | Call | Var | Arg | Member

type Statement = Ignore | Let | Return


@dataclass
class Create:
    """creates object and puts it on the stack"""
    type_id: int
    children: List[Expr]

    def to_asm(self, ctx: AsmContext):
        create_children = ""
        for child in self.children:
            create_children += f"""
                {child.to_asm(ctx)}
            """
        return f"""
                {create_children}
                push qword {len(self.children)}
                push qword {self.type_id}
                call _make_obj
                push rax
            """

@dataclass
class FitBranch:
    """checks if object on stack fits the pattern and if so, leaves content's result on stack"""
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

@dataclass
class Fit:
    """leaves result on stack"""
    obj: Expr
    branches: List[FitBranch]

    def to_asm(self, ctx: AsmContext):
        fit_end = ctx.unique_id("fit_end")
        return f"""
            {self.obj.to_asm(ctx)}
            {'\n'.join(branch.to_asm(ctx, fit_end) for branch in self.branches)}
            {fit_end}:
            pop rax
            mov [rsp], rax
        """




@dataclass
class Pattern:
    """takes object in rax, destroys it. iff pattern matches object ZF is set"""
    type_id: int
    children: List[Pattern | None]

    def to_asm(self, ctx: AsmContext) -> str:
        match_start = ctx.unique_id("match")
        match_end = ctx.unique_id("match_end")

        inner_match = ""
        gap = 8

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

        return f"""
            {match_start}:
                push rax
                mov rax, [rax]
                cmp rax, {self.type_id}
                jne {match_end}
                {inner_match}
            {match_end}:
                pop rax
        """

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
            sub rsp, {self.local_vars * 8}
            mov rbp, rsp
            {'\n'.join(s.to_asm(ctx) for s in self.content)}
            {ctx.return_token}:
            mov rsp, rbp
            add rsp, {self.local_vars * 8}
            ret
        """


@dataclass
class Return:
    content: Expr

    def to_asm(self, ctx: AsmContext) -> str:
        return f""" 
            {self.content.to_asm(ctx)}
            pop rax
            jmp {ctx.return_token}
        """

@dataclass
class Call:
    """calls function and leaves result on the stack"""
    function: Expr
    args: List[Expr]

    def to_asm(self, ctx: AsmContext) -> str:
        return f""" 
            push rbp
            {'\n'.join(arg.to_asm(ctx) for arg in reversed(self.args))}
            {self.function.to_asm(ctx)}
            pop rax
            call rax
            add rsp, {len(self.args) * 8}
            pop rbp
            push rax
        """

@dataclass
class Let:
    var: int
    value: Expr

    def to_asm(self, ctx: AsmContext) -> str:
        return f""" 
            {self.value.to_asm(ctx)}
            pop rax
            mov rbx, rbp
            add rbx, {8 * self.var}
            mov [rbx], rax
        """

@dataclass
class FunName:
    name: str
    def to_asm(self, ctx: AsmContext) -> str:
        return f""" 
            push {self.name}
        """

@dataclass
class Ignore:
    content: Expr
    def to_asm(self, ctx: AsmContext) -> str:
        return f""" 
            {self.content.to_asm(ctx)}
            add rsp, 8
        """

@dataclass
class Program:
    functions: List[Fun]
    def to_asm(self, ctx: AsmContext) -> str:
        result = f"""
            section .text
            global main
            extern _make_obj

            {'\n'.join(f.to_asm(ctx) for f in self.functions)}
        """
        return '\n'.join(l for l in (l.strip() for l in result.split('\n')) if l != '')
    
@dataclass
class Arg:
    i: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            mov rbx, rbp
            add rbx, {8 + 8 * ctx.var_count + 8 * self.i}
            push qword [rbx]
        """

@dataclass
class Var:
    var: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            mov rbx, rbp
            add rbx, {8 * self.var}
            push qword [rbx]
        """

@dataclass
class Member:
    """returns ith member"""
    obj: Expr
    i: int
    def to_asm(self, ctx: AsmContext) -> str:
        return f"""
            {self.obj.to_asm(ctx)}
            pop rax
            add rax, {8 + 8 * self.i}
            push qword [rax]
        """




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


class AsmContext:
    _id: int
    return_token: str
    var_count: int

    def __init__(self):
        self._id = 0

    def unique_id(self, name: str) -> str:
        self._id += 1
        return f"{name}_{self._id}"




program = Program([
    Fun("_print_Nat_Zero", 0, [
        Print("Zero"),
        Return(Create(0, []))
    ]),

    Fun("_print_Nat_Succ", 0, [
        Print("Succ "),
        Ignore(Call(FunName("_print_Nat"), [Member(Arg(0), 0)])),
        Return(Create(0, []))
    ]),

    Fun("_print_Nat", 0, [
        Print("("),
        Ignore(Fit(Arg(0), [
            FitBranch(Pattern(0, []), Call(FunName("_print_Nat_Zero"), [Arg(0)])),
            FitBranch(Pattern(1, [None]), Call(FunName("_print_Nat_Succ"), [Arg(0)])),
        ])),
        Print(")"),
        Return(Create(0, []))
    ]),

    Fun("add", 0, [
        Return(Fit(Create(0, [Arg(0), Arg(1)]), [
            FitBranch(Pattern(0, [None, Pattern(0, [])]), Arg(0)),
            FitBranch(None, Create(1, [Call(FunName("add"), [Arg(0), Member(Arg(1), 0)])])),
        ]))
    ]),

    Fun("mul", 0, [
        Return(Fit(Create(0, [Arg(0), Arg(1)]), [
            FitBranch(Pattern(0, [None, Pattern(0, [])]), Create(0, [])),
            FitBranch(None, Call(FunName("add"), [Call(FunName("mul"), [Arg(0), Member(Arg(1), 0)]), Arg(0)])),
        ]))
    ]),

    Fun("pow", 0, [
        Return(Fit(Create(0, [Arg(0), Arg(1)]), [
            FitBranch(Pattern(0, [None, Pattern(0, [])]), Create(1, [Create(0, [])])),
            FitBranch(None, Call(FunName("mul"), [Call(FunName("pow"), [Arg(0), Member(Arg(1), 0)]), Arg(0)])),
        ]))
    ]),

    Fun("main", 2, [
        Let(0, Create(1, [Create(1, [Create(1, [Create(0, [])])])])),
        Let(1, Create(1, [Create(1, [Create(1, [Create(0, [])])])])),
        Ignore(Call(FunName("_print_Nat"), [Call(FunName("pow"), [Var(0), Var(1)])])),
        Return(Var(0))
    ])
])

ctx = AsmContext()
print(program.to_asm(ctx))