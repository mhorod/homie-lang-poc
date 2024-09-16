
from typing import *

from dataclasses import dataclass
from enum import Enum, auto

from source import *

class TokenKind:
    pass

class KeywordKind(TokenKind, Enum):
    KwFun = auto()
    KwFit = auto()
    KwDis = auto()
    KwGiv = auto()
    KwMod = auto()
    KwLet = auto()
    KwRet = auto()

class DelimKind(TokenKind, Enum):
    OpenBrace = auto()
    CloseBrace = auto()
    OpenParen = auto()
    CloseParen = auto()
    OpenBracket = auto()
    CloseBracket = auto()

class SymbolKind(TokenKind, Enum):
    Colon = auto()
    Semicolon = auto()
    Comma = auto()
    Dot = auto()
    QuestionMark = auto()
    ExclamationMark = auto()
    Arrow = auto()
    FatArrow = auto()
    Underscore = auto()
    DoubleColon = auto()
    Equals = auto()

class WhitespaceKind(TokenKind, Enum):
    Whitespace = auto()
    Comment = auto()

class NumberKind(TokenKind, Enum):
    Integer = auto()

class StringKind(TokenKind, Enum):
    String = auto()

class NameKind(TokenKind, Enum):
    VarName = auto()
    EnumName = auto()

class ErrorKind(TokenKind, Enum):
    Error = auto()

@dataclass
class Token:
    text: str
    kind: TokenKind
    location: Location

    def __repr__(self):
        return f"{self.kind}: \"{self.text}\""