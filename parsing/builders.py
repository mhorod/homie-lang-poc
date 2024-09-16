from tree import *

class EnumTypeBuilder:
    def __init__(self):
        self.enum_type = EnumType(None, None)

    def name(self, name):
        self.enum_type.name = name

    def generics(self, generics):
        self.enum_type.generics = generics

    def build(self):
        return self.enum_type


class ArgBuilder:
    def __init__(self):
        self.arg = Arg(None, None)

    def name(self, name):
        self.arg.name = name
    
    def type(self, type):
        self.arg.type = type

    def build(self):
        return self.arg


class EnumBranchBuilder:
    def __init__(self):
        self.enum_branch = EnumBranch(None, None)

    def name(self, name):
        self.enum_branch.name = name

    def args(self, args):
        self.enum_branch.args = args

    def build(self):
        return self.enum_branch
    


class EnumNodeBuilder:
    def __init__(self):
        self.enum_node = EnumNode(None, None, None)

    def name(self, name):
        self.enum_node.name = name

    def generic_names(self, generic_names):
        self.enum_node.generic_names = generic_names
    
    def branches(self, branches):
        self.enum_node.branches = branches

    def build(self):
        return self.enum_node


class FitBranchBuilder:
    def __init__(self):
        self.fit_branch = FitBranch(None, None)
    
    def left(self, left):
        self.fit_branch.left = left

    def right(self, right):
        self.fit_branch.right = right

    def build(self):
        return self.fit_branch

class FitBuilder:
    def __init__(self):
        self.fit = Fit(None, None)
    
    def var(self, var):
        self.fit.var = var
    
    def branches(self, branches):
        self.fit.branches = branches

    def build(self):
        return self.fit


class LetBuilder:
    def __init__(self):
        self.let = Let(None, None)

    def name(self, name):
        self.let.name = name

    def value(self, value):
        self.let.value = value

    def build(self):
        return self.let

class FunBuilder:
    def __init__(self):
        self.fun = Fun(None, None, None, None, None)
    
    def name(self, name):
        self.fun.name = name

    def generics(self, generics):
        self.fun.generics = generics

    def arguments(self, arguments):
        self.fun.arguments = arguments

    def ret(self, type):
        self.fun.type = type

    def body(self, body):
        self.fun.body = body

    def build(self):
        return self.fun