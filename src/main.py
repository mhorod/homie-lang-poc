from lex import lex
from parsing.parse import parse
from tokens import Source
from typechecking.typechecker import typecheck
from ast_to_ll import to_ll
from compiler import compile
from validating.validator import validate
from parsing.combinators import Result, ResultStatus
from error_reporting import print_error, print_error_report
import sys

def my_exit(ok: bool):
    ok ^= '--flip-error-code' in sys.argv
    exit(0 if ok else 1)

def run_file(file):
    with open(file, "r") as f:
        source = Source(file, f.read())

    tokens = lex(source)

    if '--tokens' in sys.argv:
        print(tokens)
        my_exit(True)

    parsing_result = parse(tokens)

    if parsing_result.status != ResultStatus.Ok:
        for error in parsing_result.errors:
            print_error(error)
        my_exit(False)

    program = parsing_result.parsed
    if '--parse' in sys.argv:
        print(program)
        my_exit(True)

    validation_errors = validate(program)

    if validation_errors:
        for error in validation_errors:
            print_error(error)
        my_exit(False)

    if '--validate' in sys.argv:
        my_exit(True)

    ctx, report = typecheck(program)

    if report.has_errors():
        print_error_report(report)
        my_exit(False)

    program = to_ll(program, ctx)

    if '--ll' in sys.argv:
        print(program.pretty_print())
        my_exit(True)

    print(compile(program))
    my_exit(True)

if __name__ == "__main__":
    run_file(sys.argv[1])
