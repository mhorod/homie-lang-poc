from tokens import Token
from source import Location
from error_reporting import *
from tree import *

def dis_does_not_exist(location, dis_name):
    msg = Message(location, f"Dis {dis_name} does not exist")
    return Error(msg)

def dis_has_no_variant(location, dis_name, variant_name):
    msg = Message(location, f"Dis {dis_name} has no variant {variant_name}")
    return Error(msg)

def dis_generic_arguments_mismatch(location, dis_node, expected, actual):
    dis_name = dis_node.name.text
    msg = Message(location, f"Dis {dis_name} takes {expected} {pluralize(expected, Words.GENERIC_ARGUMENTS)} but {actual} {pluralize(actual, Words.WAS)} provided")
    def_msg = Message(dis_name_and_generics_span(dis_node), "Defined here")
    return Error(msg, [def_msg])

def fun_generic_arguments_mismatch(location, fun_node, expected, actual):
    fun_name = fun_node.name.text
    msg = Message(location, f"Fun {fun_name} takes {expected} {pluralize(expected, Words.GENERIC_ARGUMENTS)} but {actual} {pluralize(actual, Words.WAS)} provided")
    def_msg = Message(fun_name_and_generics_span(fun_node), "Defined here")
    return Error(msg, [def_msg])


def variant_argument_count_mismatch(location, dis_node, variant_node, actual):
    variant_name = f"{dis_node.name.text}::{variant_node.name.text}"
    expected = len(variant_node.args)
    msg = Message(location, f"Variant {variant_name} takes {expected} {pluralize(expected, Words.ARGUMENTS)} but {actual} {pluralize(actual, Words.WAS)} provided")
    def_msg = Message(variant_node.location, "Defined here")
    return Error(msg, [def_msg])

def function_argument_count_mismatch(location, fun_location, fun_ty, expected, actual):
    msg = Message(location, f"Function takes {expected} {pluralize(expected, Words.ARGUMENTS)} but {actual} {pluralize(actual, Words.WAS)} provided")
    explanation = Message(fun_location, f"Function has type {fun_ty}")
    return Error(msg, [explanation])


def cannot_match_pattern_to_non_dis(location, pat_name, ty):
    msg = Message(location, f"Cannot match pattern {pat_name} to non-dis type {ty}")
    return Error(msg)


def unknown_variable(var: VarNode):
    return Error(Message(var.location, f"Unknown variable: {var.name.text}"))


def unknown_function(fun_inst: FunInstNode):
    return Error(Message(fun_inst.name.location, f"Unknown function: {fun_inst.name.text}"))

def expected_dis_type(location: Location, found):
    msg = Message(location, f"Expected dis type, got {found}")
    return Error(msg)


def type_is_not_callable(location: Location, ty):
    msg = Message(location, f"Type {ty} is not callable")
    return Error(msg)

def function_expects_arg_of_type(location, expected, actual, fun_location, fun_ty):
    msg = Message(location, f"Function expects argument of type {expected} but {actual} was provided")
    explanation = Message(fun_location, f"Function has type {fun_ty}")
    return Error(msg, [explanation])


def cannot_get_member_on_non_dis_type(location, member_name, ty):
    msg = Message(location, f"Cannot get member {member_name} on non-dis type {ty}")
    return Error(msg)

def cannot_get_member_on_non_variant_type(location, member_name, ty, expr_location):
    msg = Message(location, f"Cannot get member {member_name} on non-variant type {ty}")
    help_msg = Message(expr_location, f"help: Consider applying fit to this expression" )
    return Error(msg, [help_msg])

def variant_has_no_member(location, member_name, ty, variant_node):
    msg = Message(location, f"Variant {ty} has no member {member_name}")
    comment = Message(variant_node.location, "Variant defined here")
    return Error(msg, [comment])

def return_type_mismatch(location, ret_ty, fun_ty, fun_node: FunNode):
    msg = Message(location, f"Return type {ret_ty} does not match declared type {fun_ty.result_type}")
    comment = Message(fun_node.ret.location, "Declared here")
    return Error(msg, [comment])
