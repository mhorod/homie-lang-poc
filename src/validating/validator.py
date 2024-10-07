from tree import *
from error_reporting import Message, Error
from builtin import *
from validating.errors import *

from tokens import Token, NameKind
from enum import Enum, auto

def validate(program_node: ProgramNode) -> List[Error]:
    # this function has the same name as method of Validator, let's check the type to make sure there are no typos
    if not isinstance(program_node, ProgramNode):
        raise Exception
    simple_types = set(BUILTIN_SIMPLE_TYPES.keys())
    builtin_functions = {key: Fun(val.generic_arg_count, len(val.ty.arg_types), None) for key, val in BUILTIN_FUNCTIONS.items()}
    return Validator(program_node, simple_types, builtin_functions).errors

@dataclass
class Dis:
    generic_count: int
    variants_to_arg_count: Dict[str, int]
    declaration_node: Optional[DisNode]

@dataclass
class Fun:
    generic_count: int
    arg_count: int
    declaration_node: Optional[FunNode]

class ContextFrame:
    generics: Dict[str, Token]
    locals: Dict[str, Token]

    def __init__(self):
        self.generics = {}
        self.locals = {}

    def add_generics(self, generics: GenericParamsNode):
        for token in generics.params:
            self.generics[token.text] = token

    def add_local(self, local: Token):
        self.locals[local.text] = local

class ErrorFlag:
    pass

class Validator:
    errors: List[Error]
    dises: Dict[str, Dis | ErrorFlag]
    simple_types: Set[str]
    functions: Dict[str, Fun | ErrorFlag]
    stack: List[ContextFrame]

    def __init__(self, program_node: ProgramNode, simple_types: Set[str], builtin_functions: Dict[str, Fun]):
        self.errors = []
        self.dises = {}
        self.simple_types = simple_types
        self.functions = builtin_functions
        self.stack = [ContextFrame()]
        self.find_dis_declarations(program_node)
        self.find_fun_declarations(program_node)
        self.validate(program_node)

    def has_local_var(self, local_name: str) -> bool:
        for frame in self.stack:
            if local_name in frame.locals:
                return True
        return False

    def has_function(self, fun_name: str) -> bool:
        return fun_name in self.functions

    def has_type(self, type_name) -> bool:
        return type_name in self.simple_types or type_name in self.dises

    def add_error(self, err: Error):
        self.errors.append(err)

    def validate(self, node: Node, is_top_expr = False):
        match node:
            case ProgramNode():
                self.validate_program(node)
            case DisNode():
                self.validate_dis(node)
            case FunNode():
                self.validate_fun(node)
            # case WildcardTypeNode():
            #     pass
            case VoidTypeNode():
                pass
            case WriteNode():
                pass
            case GenericParamsNode():
                self.validate_generics(node)
            case DisTypeNode():
                self.validate_dis_type(node)
            case DisConstructorNode():
                self.validate_dis_constructor(node)
            case VarNode():
                self.validate_var(node)
            case MemberNode():
                self.validate_member(node)
            case AssignNode():
                self.validate_assign(node, is_top_expr)
            case FunctionTypeNode():
                self.validate_fun_type(node)
            case ArgNode():
                self.validate_arg(node)
            # case OperatorNode():
            #     pass
            case DisVariantNode():
                self.validate_dis_variant(node)
            case PatternNode():
                self.validate_pattern(node)
            case FitBranchNode():
                self.validate_fit_branch(node)
            case FitExprNode():
                self.validate_fit_expr(node)
            case FitStatementNode():
                self.validate_fit_statement(node)
            case RetNode():
                self.validate_ret(node)
            case BlockNode():
                self.validate_block(node)
            case LetNode():
                self.validate_let(node)
            case ValueNode():
                self.validate_value(node)
            case FunInstNode():
                self.validate_fun_inst(node)
            case CallNode():
                self.validate_call(node)
            # case TupleLikeNode():
            #     pass
            # case FunctionTypeArgsNode():
            #     pass
            case _:
                raise Exception(f"Unexpected tree node: {node}")

    def validate_generics(self, node: GenericParamsNode):
        previous: Dict[str, Token] = {}
        for generic in node.params:
            if generic.text in previous:
                self.add_error(duplicated_generics(generic, previous[generic.text]))
            else:
                previous[generic.text] = generic
        # TODO check if generics name appears in other frames?

    def find_dis_declarations(self, node: ProgramNode):
        previous: Dict[str, DisNode] = {}
        for dis_node in node.items:
            if not isinstance(dis_node, DisNode):
                continue
            name = dis_node.name.text
            error = False
            if name in self.simple_types:
                self.add_error(builtin_dis_collision(dis_node))
                error = True
            if name in previous:
                self.add_error(duplicated_dis(dis_node, previous[name]))
                error = True
            else:
                previous[name] = dis_node

            dis_obj = Dis(len(dis_node.generics.params), {v.name.text: len(v.args) for v in dis_node.variants}, node)
            self.dises[name] = ErrorFlag() if error else dis_obj

    def validate_dis(self, node: DisNode):
        self.stack.append(ContextFrame())
        self.validate(node.generics)
        self.stack[-1].add_generics(node.generics)

        previous: Dict[str, DisVariantNode] = {}
        for variant in node.variants:
            self.validate(variant)
            name = variant.name.text
            if name in previous:
                self.add_error(duplicated_dis_variant(node.name.text, variant, previous[name]))
            else:
                previous[name] = variant

        self.stack.pop()

    def validate_arg(self, node: ArgNode):
        self.validate(node.type)

    def validate_arg_list(self, args: List[ArgNode]):
        previous: Dict[str, ArgNode] = {}
        for arg in args:
            self.validate(arg)
            if arg.name.text in previous:
                self.add_error(duplicated_arg(arg, previous[arg.name.text]))
            else:
                previous[arg.name.text] = arg

    def validate_dis_variant(self, node: DisVariantNode):
        self.validate_arg_list(node.args)

    def find_fun_declarations(self, node: ProgramNode):
        previous: Dict[str, DisNode] = {}
        for fun_node in node.items:
            if not isinstance(fun_node, FunNode):
                continue
            name = fun_node.name.text
            error = False
            if name in previous:
                self.add_error(duplicated_function(fun_node, previous[name]))
                error = True
            else:
                previous[name] = fun_node

            fun_obj = Fun(len(fun_node.generics.params), len(fun_node.args), node)
            self.functions[name] = ErrorFlag() if error else fun_obj

    def validate_fun(self, node: FunNode):
        self.stack.append(ContextFrame())
        self.validate(node.generics)
        self.stack[-1].add_generics(node.generics)

        self.validate_arg_list(node.args)
        for arg in node.args:
            self.stack[-1].add_local(arg.name)

        self.validate(node.ret)
        self.validate(node.body)

        self.stack.pop()

    def validate_program(self, node: ProgramNode):
        for item in node.items:
            self.validate(item)

    def validate_assign(self, node: AssignNode, is_top_expr):
        if not is_top_expr:# TODO to error
            msg = Message(node.location, f"Assignment can only be used in top level expressions")
            self.errors.append(Error(msg))
        if not isinstance(node.var, (VarNode, MemberNode)):
            msg = Message(node.var.location, f"Can only assign to variables and members")
            self.errors.append(Error(msg))

        self.validate(node.var)
        self.validate(node.expr)

    def validate_member(self, node: MemberNode):
        self.validate(node.expr)

    def validate_block(self, node: BlockNode):
        self.stack.append(ContextFrame())
        for statement in node.statements:
            self.validate(statement, is_top_expr=True)
        self.stack.pop()

    def validate_dis_type(self, node: DisTypeNode):
        for generic in node.generics:
            self.validate(generic)

    def validate_ret(self, node: RetNode):
        if node.expr is not None:
            self.validate(node.expr)

    def validate_call(self, node: CallNode):
        self.validate(node.fun)
        for arg in node.arguments:
            self.validate(arg)

    def validate_dis_constructor(self, node: DisConstructorNode):
        for generic in node.generics:
            self.validate(generic)

        match self.dises.get(node.name.text):
            case ErrorFlag():
                pass
            case None:
                self.add_error(dis_does_not_exist(node.name.location, node.name.text))
            case Dis() as dis:
                if dis.generic_count != len(node.generics):
                    self.add_error(dis_generic_arguments_mismatch(node.location, dis.declaration_node, dis.generic_count, len(node.generics)))
                if node.variant_name.text not in dis.variants_to_arg_count:
                    self.add_error(dis_has_no_variant(node.variant_name.location, node.name.text, node.variant_name.text))

    def validate_var(self, node: VarNode):
        if self.has_local_var(node.name.text):
            return
        match self.functions.get(node.name.text):
            case ErrorFlag():
                return
            case Fun() as fun:
                if fun.generic_count != 0:
                    self.add_error(fun_generic_arguments_mismatch(node.name.location, fun.declaration_node, fun.generic_count, 0))
                return

        self.add_error(unknown_variable(node))

    def validate_let(self, node: LetNode):
        self.validate(node.value)

        match self.stack[-1].locals.get(node.name.text):
            case Token() as first_definition:
                self.add_error(duplicated_variable(node, first_definition))
            case None:
                self.stack[-1].add_local(node.name)

    def validate_fit_expr(self, node: FitExprNode):
        self.validate(node.expr)
        for branch in node.branches:
            self.validate(branch)

    def validate_fit_statement(self, node: FitStatementNode):
        self.validate(node.expr)
        for branch in node.branches:
            self.validate(branch)

    def validate_fit_branch(self, node: FitBranchNode):
        if node.left is not None:
            self.validate(node.left)
        self.validate(node.right, is_top_expr=True)

    def validate_pattern(self, node: PatternNode):
        for arg in node.args:
            if arg is not None:
                self.validate(arg)

    def validate_fun_inst(self, node: FunInstNode):
        for generic in node.generics:
            self.validate(generic)

        match self.functions.get(node.name.text):
            case ErrorFlag():
                pass
            case None:
                self.add_error(unknown_function(node))
            case Fun() as fun:
                if len(node.generics) != fun.generic_count:
                    self.add_error(fun_generic_arguments_mismatch(node.name.location, fun.declaration_node, fun.generic_count, len(node.generics)))

    def validate_fun_type(self, node: FunctionTypeNode):
        for arg in node.args:
            self.validate(arg)
        self.validate(node.ret)

    def validate_value(self, node: ValueNode):
        pass
