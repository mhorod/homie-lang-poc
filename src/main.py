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

def run_file(file):
    with open(file, "r") as f:
        source = Source(file, f.read())

    tokens = lex(source)

    if '--tokens' in sys.argv:
        print(tokens)
        return

    parsing_result = parse(tokens)

    if '--parse' in sys.argv:
        print(parsing_result)
        return

    if parsing_result.status == ResultStatus.Ok:
        program = parsing_result.parsed

        ctx, report = typecheck(program)
        print_error_report(report)

        if not report.has_errors():
            program = to_ll(program, ctx)

            if '--ll' in sys.argv:
                print(program.pretty_print())
                return
            if '--compile' in sys.argv:
                print(compile(program))
    else:
        for error in parsing_result.errors:
            print_error(error)


if __name__ == "__main__":
    run_file(sys.argv[1])
