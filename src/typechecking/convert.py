from error_reporting import *
from tree import *

from typechecking.types import *
from typechecking.context import *
from typechecking.errors import *

class TypeConverter:
    '''
    Validates and converts types explicitly annotated by programmer into typechecker representations
    '''
    def __init__(self, report, ctx: TypingContext):
        self.report = report
        self.ctx = ctx

    def convert_type(self, parsed_type: TypeNode):
        if isinstance(parsed_type, DisTypeNode):
            return self.convert_dis_type(parsed_type)
        elif isinstance(parsed_type, FunctionTypeNode):
            return self.convert_function_type(parsed_type)
        elif isinstance(parsed_type, DisConstructorNode):
            return self.convert_dis_constructor_type(parsed_type)
        elif isinstance(parsed_type, WildcardTypeNode):
            return WildcardTy()
        elif isinstance(parsed_type, VoidTypeNode):
            return SimpleType('Void')
        else:
            raise Exception(f"Cannot convert {parsed_type} into Ty")

    def convert_dis_type(self, parsed_type: DisTypeNode):
        name = parsed_type.name.text
        if self.ctx.has_generic(name):
            if parsed_type.generics:
                msg = Message(parsed_type.location, f"Type variable {name} cannot be generic")
                self.report.error(Error(msg))
                return ErrorTy()
            else:
                index = self.ctx.get_generic(name)
                return TyVar(index, name)
        elif name in self.dis_nodes:
            if len(self.dis_nodes[name]) > 1:
                return ErrorTy()
            dis_node = self.dis_nodes[name][0]
            if len(dis_node.generics.params) != len(parsed_type.generics):
                expected = len(dis_node.generics.params)
                actual= len(parsed_type.generics)
                self.report.error(dis_generic_arguments_mismatch(parsed_type.location, dis_node, expected, actual))
                return ErrorTy()
            else:
                generic_types = [self.convert_type(gen) for gen in parsed_type.generics]
                if any(isinstance(ty, ErrorTy) for ty in generic_types):
                    return ErrorTy()
                return DisTy(parsed_type.name.text, generic_types, CatchallPattern())
        elif parsed_type.name.text in self.ctx.simple_types:
            if parsed_type.generics:
                raise Exception(f"Type {parsed_type.name} is not generic")
            return self.ctx.simple_types[parsed_type.name.text]
        else:
            msg = Message(parsed_type.location, f"Type {name} is not defined")
            self.report.error(Error(msg))
            return ErrorTy()

    def convert_function_type(self, parsed_type: FunctionTypeNode):
        arg_types = [self.convert_type(arg) for arg in parsed_type.args]
        ret_type = self.convert_type(parsed_type.ret)
        if any(isinstance(ty, ErrorTy) for ty in arg_types) or isinstance(ret_type, ErrorTy):
            return ErrorTy()
        return FunTy(arg_types, ret_type)

    def convert_dis_constructor_type(self, parsed_type: DisConstructorNode):
        dis_name = parsed_type.name.text

        if dis_name not in self.dis_nodes:
            msg = Message(parsed_type.name.location, f"Dis {dis_name} is not defined")
            self.report.error(Error(msg))
            return ErrorTy()
        elif len(self.dis_nodes[dis_name]) > 1:
            return ErrorTy()

        dis_node = self.dis_nodes[dis_name][0]

        variant_name = parsed_type.variant_name.text
        for variant in dis_node.variants:
            if variant.name.text == variant_name:
                return DisTy(parsed_type.name.text, [self.convert_type(gen) for gen in parsed_type.generics], TyPattern(parsed_type.variant_name.text, None))

        msg = Message(parsed_type.variant_name.location, f"{dis_name} has no variant {variant_name}")
        self.report.error(Error(msg))

        return ErrorTy()

    def convert_pattern(self, p: Pattern | ValueNode | None):
        # TODO: typecheck pattern with known dis variants
        if isinstance(p, CatchallPatternNode):
            return CatchallPattern()
        elif isinstance(p, ValueNode):
            return self.type_value(p)
        else:
            return TyPattern(p.name.text, tuple([self.convert_pattern(arg) for arg in p.args]))
