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
