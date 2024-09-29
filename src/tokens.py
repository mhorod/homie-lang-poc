
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
    KwWrt = auto()

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
    Plus = auto()
    Minus = auto()
    Asterisk = auto()
    Slash = auto()
    Percent = auto()

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

class EofKind(TokenKind, Enum):
    Eof = auto()

SYMBOL_MAP = {
    ":" : SymbolKind.Colon,
    ";" : SymbolKind.Semicolon,
    "," : SymbolKind.Comma,
    "." : SymbolKind.Dot,
    "?" : SymbolKind.QuestionMark,
    "!" : SymbolKind.ExclamationMark,
    "->": SymbolKind.Arrow,
    "=>": SymbolKind.FatArrow,
    "_": SymbolKind.Underscore,
    "::": SymbolKind.DoubleColon,
    "=" : SymbolKind.Equals,

    "+": SymbolKind.Plus,
    "-": SymbolKind.Minus,
    "*": SymbolKind.Asterisk,
    "/": SymbolKind.Slash,
    "%": SymbolKind.Percent,

    "(": DelimKind.OpenParen,
    ")": DelimKind.CloseParen,
    "{": DelimKind.OpenBrace,
    "}": DelimKind.CloseBrace,
    "[": DelimKind.OpenBracket,
    "]": DelimKind.CloseBracket,
}

KEYWORD_MAP = {
    "fun" : KeywordKind.KwFun,
    "fit" : KeywordKind.KwFit,
    "dis" : KeywordKind.KwDis,
    "giv" : KeywordKind.KwGiv,
    "mod" : KeywordKind.KwMod,
    "let": KeywordKind.KwLet,
    "ret": KeywordKind.KwRet,
    "wrt": KeywordKind.KwWrt
}

KIND_TO_STR = {
    **{ kind : text for text, kind in KEYWORD_MAP.items() },
    **{ kind : text for text, kind in SYMBOL_MAP.items() },
    EofKind.Eof: "<eof>",
    NameKind.VarName: "lowercase identifier",
    NameKind.EnumName: "uppercase identifier"
}

@dataclass
class Token:
    text: str
    kind: TokenKind
    location: Location

    def __repr__(self):
        return f"{self.kind}: \"{self.text}\""
