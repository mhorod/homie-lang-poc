
from typing import *

from dataclasses import dataclass
from enum import Enum, auto

class Source:
    def __init__(self, name, text):
       self.name = name
       self.text = text
       self.line_beginnings = [0]
       for i, c in enumerate(text):
           if c == '\n':
               self.line_beginnings.append(i + 1)
           
    def get_line_and_column(self, index):
        line = 0
        while line + 1 < len(self.line_beginnings) and self.line_beginnings[line + 1] <= index:
           line += 1
        return line + 1, index - self.line_beginnings[line] + 1

@dataclass
class Location:
    source: Source
    begin: int
    end: int
    
    def line_and_column(self):
        return self.source.get_line_and_column(self.begin)

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