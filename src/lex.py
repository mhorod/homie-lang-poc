from typing import *

from dataclasses import dataclass
from enum import Enum, auto
import string

from tokens import *

class RawTokenKind(Enum):
    Alphanumeric = auto()
    Symbolic = auto()
    Whitespace = auto()
    Comment = auto()
    StringLiteral = auto()

@dataclass
class RawToken:
    text: str
    kind: RawTokenKind
    location: Location

    

class TextCursor:
    def __init__(self, source):
        self.source = source
        self.index = 0
        self.eaten_index = 0

    def peek(self, n=1) -> str | None:
        if self.index + n <= len(self.source.text): 
            return self.source.text[self.index:self.index+n]

    def advance(self, n=1):
        self.index += n

    def eaten(self):
        result = self.source.text[self.eaten_index:self.index]
        location = Location(self.source, self.eaten_index, self.index)
        self.eaten_index = self.index
        return result, location
        
    def has(self, n=1):
        return self.index + n <= len(self.source.text)
        

def lex(source: Source) -> List[Token]:
    cursor = TextCursor(source)
    tokens = []
    while cursor.has():
        raw_token = lex_raw_token(cursor)
        tokens += cook_token(raw_token)

    tokens.append(Token("<eof>", EofKind.Eof, source.eof()))
    return tokens


def cook_token(token: RawToken) -> List[TokenKind]:
    if token.text in SYMBOL_MAP:
        return [Token(token.text, SYMBOL_MAP[token.text], token.location)]
    elif token.kind == RawTokenKind.Whitespace or token.kind == RawTokenKind.Comment:
        return []
    elif token.kind == RawTokenKind.Alphanumeric:
        if token.text in KEYWORD_MAP:
            return [Token(token.text, KEYWORD_MAP[token.text], token.location)]
        if token.text.isdigit():
            return [Token(token.text, NumberKind.Integer, token.location)]
        elif token.text[0] in string.ascii_uppercase:
            return [Token(token.text, NameKind.EnumName, token.location)]
        else:
            return [Token(token.text, NameKind.VarName, token.location)]
    elif token.kind == RawTokenKind.Symbolic:
        result = []
        for i, symbol in enumerate(token.text):
            location = Location(token.location.source, token.location.begin + i, token.location.begin + i + 1)
            result.append(Token(symbol, SYMBOL_MAP.get(symbol, ErrorKind.Error), location))
        return result
    elif token.kind == RawTokenKind.StringLiteral:
        if len(token.text) >= 2 and token.text[-1] == '"':
            return [Token(token.text, StringKind.String, token.location)]
        else:
            print("Unterminated string: ", token.text)
    else:
        print("Unexpected: ", token)

def lex_raw_token(cursor: TextCursor):
    if is_space(cursor):
        text, location = lex_space(cursor)
        return RawToken(text, RawTokenKind.Whitespace, location)
    elif is_inline_comment(cursor):
        text, location = lex_inline_comment(cursor)
        return RawToken(text, RawTokenKind.Comment, location)
    elif is_multiline_comment(cursor):
        text, location = lex_multiline_comment(cursor)
        return RawToken(text, RawTokenKind.Comment, location)
    elif is_alnum(cursor):
        text, location = lex_alnum(cursor)
        return RawToken(text, RawTokenKind.Alphanumeric, location)
    elif is_symbolic(cursor):
        text, location = lex_symbolic(cursor)
        return RawToken(text, RawTokenKind.Symbolic, location)
    elif is_delim(cursor):
        text, location = lex_delim(cursor)
        return RawToken(text, RawTokenKind.Symbolic, location)
    elif is_quote(cursor):
        text, location = lex_string_literal(cursor)
        return RawToken(text, RawTokenKind.StringLiteral, location)
    else:
        print("unexpected: ", cursor.peek())
        

def is_space(cursor: TextCursor):
    return cursor.peek() in string.whitespace

def is_alnum(cursor: TextCursor):
    return cursor.peek().isalnum() or cursor.peek() == "_"

DELIMS = "[](){}"
SYMBOLS = ".,:;?!<=>+-/*%^|&"
def is_symbolic(cursor: TextCursor):
    return cursor.peek() in SYMBOLS

def is_delim(cursor: TextCursor):
    return cursor.peek() in DELIMS

def is_quote(cursor: TextCursor):
    return cursor.peek() == "\""

def is_inline_comment(cursor: TextCursor):
    return cursor.peek(2) == "//"

def is_multiline_comment(cursor: TextCursor):
    return cursor.peek(2) == "/*"

def lex_space(cursor: TextCursor):
    while cursor.has() and is_space(cursor):
        cursor.advance()
    return cursor.eaten()

def lex_alnum(cursor: TextCursor):
    while cursor.has() and is_alnum(cursor):
        cursor.advance()
    return cursor.eaten()

def lex_symbolic(cursor: TextCursor):
    while cursor.has() and is_symbolic(cursor):
        cursor.advance()
    return cursor.eaten()

def lex_delim(cursor: TextCursor):
    cursor.advance()
    return cursor.eaten()

def lex_string_literal(cursor: TextCursor):
    cursor.advance()
    while cursor.has() and not is_quote(cursor):
        cursor.advance()
    if cursor.has():
        cursor.advance()
    return cursor.eaten()

def lex_inline_comment(cursor: TextCursor):
    while cursor.has() and cursor.peek() != "\n":
        cursor.advance()
    if cursor.has():
        cursor.advance()
    return cursor.eaten()
        

def lex_multiline_comment(cursor: TextCursor):
    open_comments = 0
    while cursor.has():
        if cursor.peek(2) == "/*":
            open_comments += 1
            cursor.advance(2)
        elif cursor.peek(2) == "*/":
            cursor.advance(2)
            open_comments -= 1
        else:
            cursor.advance(1)
        
        if open_comments == 0:
            break
    return cursor.eaten()