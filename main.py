from lex import lex
from parsing.parse import parse
from tree import ProgramType
from tokens import Source
from typechecker import typecheck

with open("main.hom", "r") as f:
    source = Source("main.hom", f.read())

tokens = lex(source)
program = parse(tokens)
if isinstance(program, ProgramType):
    typecheck(program)
    #program.exec()