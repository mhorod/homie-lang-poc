from typechecking.types import SimpleType, TyVar, FunTy, FunctionDeclaration
from tokens import Token

from dataclasses import replace

INT_TYPE = SimpleType('Int')
CSTRING_TYPE = SimpleType('CString')
VOID_TYPE = SimpleType('Void')

BUILTIN_SIMPLE_TYPES = {
    'Int' : INT_TYPE,
    'CString': CSTRING_TYPE,
    'Void': VOID_TYPE
}

TOKENS_BUILTINS_MAP = {
    '+': '__builtin_operator_add',
    '-': '__builtin_operator_sub',
    '*': '__builtin_operator_mul',
    '/': '__builtin_operator_div',
    '%': '__builtin_operator_mod'
}

def fix_builtin_token(token: Token) -> Token:
    return replace(token, text = TOKENS_BUILTINS_MAP[token.text])

BUILTIN_FUNCTIONS =  {
    **{ name : FunctionDeclaration(0, FunTy([INT_TYPE, INT_TYPE], INT_TYPE)) for name in TOKENS_BUILTINS_MAP.values() },
    '__builtin_operator_eq' : FunctionDeclaration(1, FunTy([INT_TYPE, INT_TYPE, TyVar(0, 'T'), TyVar(0, 'T')], TyVar(0, 'T'))),
    '__builtin_operator_less' : FunctionDeclaration(1, FunTy([INT_TYPE, INT_TYPE, TyVar(0, 'T'), TyVar(0, 'T')], TyVar(0, 'T')))
}
