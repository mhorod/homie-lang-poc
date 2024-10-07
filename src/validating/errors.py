from tokens import Token
from source import Location
from error_reporting import *
from tree import *

def builtin_dis_collision(dis: DisNode):
    msg = Message(dis.name.location, f"Dis name {dis.name.text} collides with a builtin")
    return Error(msg)

def duplicated_arg(fun: ArgNode, first_defined: ArgNode):
    reason = Message(fun.location,  f"Duplicated argument identifier: {fun.name}")
    comment = Message(first_defined.location, f"First defined here")
    return Error(reason, [comment])

def duplicated_function(fun: FunNode, first_defined: FunNode):
    reason = Message(fun.name.location,  f"Duplicated function: {fun.name.text}")
    comment = Message(first_defined.name.location, f"First defined here")
    return Error(reason, [comment])

def duplicated_dis(dis: DisNode, first_defined: DisNode):
    reason = Message(dis.name.location,  f"Duplicated dis: {dis.name.text}")
    comment = Message(first_defined.name.location, f"First defined here")
    return Error(reason, [comment])

def duplicated_dis_variant(dis_name, variant: DisVariantNode, first_defined: DisVariantNode):
    reason = Message(variant.name.location,  f"Duplicated variant {variant.name.text} of dis {dis_name}")
    comment = Message(first_defined.name.location, f"First defined here")
    return Error(reason, [comment])

def duplicated_generics(name: Token, first_defined: Token):
    reason = Message(name.location, f"Duplicated generic parameter: {name.text}")
    comment = Message(first_defined.location, "First defined here")
    return Error(reason, [comment])

def duplicated_variable(var: LetNode, first_defined: Token):
    reason = Message(var.name.location,  f"Duplicated variable: {var.name.text}")
    comment = Message(first_defined.location, f"First defined here")
    return Error(reason, [comment])
