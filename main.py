from lex import lex
from parse import parse
from tree import *
from tokens import Source

def print_tree(tree, indent=0):
    if isinstance(tree, list):
        for t in tree:
            print_tree(t, indent + 1)
    else:
        print("  " * indent, tree)

with open("main.hom", "r") as f:
    source = Source("main.hom", f.read())

tokens = lex(source)
print(tokens)
program = parse(tokens)
print(program)
if not isinstance(program, list):
    print("Result:")
    print_tree(program)
    program.exec(Context())