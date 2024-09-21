from lex import lex
from parsing.parse import parse
from tree import ProgramType
from tokens import Source
from typechecker import typecheck
from ast_to_ll import to_ll
from compiler import compile
import sys

with open("main.hom", "r") as f:
    source = Source("main.hom", f.read())

tokens = lex(source)
program = parse(tokens)

if isinstance(program, ProgramType):
    ctx = typecheck(program)
    program = to_ll(program, ctx)

    print(program.pretty_print(), file=sys.stderr)
    print(compile(program))

    #program.exec()