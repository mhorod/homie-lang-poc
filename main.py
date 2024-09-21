from lex import lex
from parsing.parse import parse
from tree import ProgramNode
from tokens import Source
from typechecking.typechecker import typecheck
from ast_to_ll import to_ll
from compiler import compile
from parsing.combinators import Result, ResultStatus
from error_reporting import print_error, print_error_report
import sys

file = "test.hom"
with open(file, "r") as f:
    source = Source(file, f.read())

tokens = lex(source)
parsing_result = parse(tokens)

if parsing_result.status == ResultStatus.Ok:
    program = parsing_result.parsed

    ctx, report = typecheck(program)
    
    if report.has_errors():
        print_error_report(report)

    program = to_ll(program, ctx)

    print(program.pretty_print(), file=sys.stderr)
    #print(compile(program))

    #program.exec()
else:
    for error in parsing_result.errors:
        print_error(error)