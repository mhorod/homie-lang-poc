from typing import *
from enum import Enum, auto
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class CursorState:
    index: int

class TokenCursor:
    def __init__(self, tokens, index=0):
        self.tokens = tokens
        self.index = index

    def has(self):
        return self.index < len(self.tokens)

    def peek(self):
        return self.tokens[self.index]

    def take(self):
        result = self.tokens[self.index]
        self.index += 1
        return result

    def save(self):
        return CursorState(self.index)
    
    def restore(self, state):
        self.index = state.index

class ResultStatus(Enum):
    OK = "OK"
    ERR = "ERR"
    BACKTRACKED = "BACKTRACKED"

class Maybe[T]:
    def __init__(self, value: T, empty: bool):
        self.value = value
        self.empty = empty

    def map(self, f):
        if self.empty:
            return Maybe.Nothing()
        else:
            return Maybe.Just(f(self.value))

    def filter(xs):
        return Maybe.Just([x.value for x in xs if not x.empty])


    def Nothing():
        return Maybe(None, True)
    
    def Just(value: T):
        return Maybe(value, False)

    def __eq__(self, other):
        return self.value == other.value and self.empty == other.empty


@dataclass
class Result[T]:
    status: ResultStatus
    parsed: Maybe[T]
    errors: list

    def Ok(parsed):
        return Result(ResultStatus.OK, parsed, [])

    def Backtracked():
        return Result(ResultStatus.BACKTRACKED, Maybe.Nothing(), [])

    def Error(error):
        return Result(ResultStatus.ERR, Maybe.Nothing(), [error])

class Parser[T](ABC):
    @abstractmethod
    def run(self, cursor, backtracking=False) -> Result[T]:
        pass

    def __or__(self, rhs):
        return Alternative(self, rhs)
    
    def __and__(self, mapper):
        return Mapped(self, mapper)

    def __add__(self, rhs):
        return Sequence(self, rhs)

    def __rshift__(self, rhs):
        return Commit(self, rhs)

class Mapped(Parser):
    def __init__(self, parser, mapper):
        self.parser = parser
        self.mapper = mapper

    def run(self, cursor, backtracking=False):
        parsed = self.parser.run(cursor, backtracking)
        if parsed.status == ResultStatus.OK:
            parsed.parsed = parsed.parsed.map(self.mapper)
        return parsed


class Repeat[T](Parser):
    def __init__(self, parser):
        self.parser = parser

    def run(self, cursor, backtracking=False) -> Result[List[T]]:
        result = []
        while True:
            if not cursor.has():
                break
            parsed = self.parser.run(cursor, True)
            if parsed.status == ResultStatus.OK:
                result.append(parsed.parsed)
            elif parsed.status == ResultStatus.BACKTRACKED:
                break
            else:
                return Result(ResultStatus.ERR, Maybe.Just(result), parsed.errors)

        return Result(ResultStatus.OK, Maybe.filter(result), [])


class Alternative[T, U](Parser[T | U]):
    def __init__(self, left: Parser[T], right: Parser[U]):
        self.left = left
        self.right = right

    def run(self, cursor, backtracking=False) -> Result[T | U]:
        cursor_state = cursor.save()
        result = self.left.run(cursor, backtracking=True)
        if result.status == ResultStatus.OK or result.status == ResultStatus.ERR:
            return result
        else:
            cursor.restore(cursor_state)
            return self.right.run(cursor, backtracking)

class Sequence[T](Parser[T]):
    def __init__(self, left: Parser[T], right: Parser[T]):
        self.left = left
        self.right = right

    def run(self, cursor, backtracking=False) -> Result[List[T]]:
        cursor_state = cursor.save()
        left = self.left.run(cursor, backtracking)
        if left.status != ResultStatus.OK:
            return left
        right = self.right.run(cursor, backtracking)
        if right.status == ResultStatus.BACKTRACKED:
            cursor.restore(cursor_state)
        return Result(right.status, 
                      Maybe.Just(
                      self.flatten(self.left, left.parsed) +
                      self.flatten(self.right, right.parsed)
                      )
         ,right.errors)

    def flatten(self, parser, parsed):
        if isinstance(parser, Sequence):
            if parsed.empty:
                return []
            else:
                return parsed.value
        elif parsed.empty:
            return []
        else:
            return [parsed.value]



class Commit[T](Parser[T]):
    def __init__(self, left: Parser[T], right: Parser[T]):
        self.left = left
        self.right = right

    def run(self, cursor, backtracking=False):
        left = self.left.run(cursor, backtracking)
        if left.status != ResultStatus.OK:
            return left
        right = self.right.run(cursor, False)
        return Result(right.status, 
                      Maybe.filter([left.parsed, right.parsed]),
                      right.errors)


class Drop[T](Parser[T]):
    def __init__(self, parser):
        self.parser = parser

    def run(self, cursor, backtracking=False) -> Result[T]:
        result = self.parser.run(cursor, backtracking)
        return Result(result.status, Maybe.Nothing(), result.errors)


class Optional[T](Parser):
    def __init__(self, parser, default):
        self.parser = parser
        self.default = default

    def run(self, cursor, backtracking=False) -> Result[List[T]]:
        result = self.parser.run(cursor, True)
        if result.status == ResultStatus.BACKTRACKED:
            result.status = ResultStatus.OK
            result.parsed = Maybe.Just(self.default)
        return result


class Interspersed(Parser):
    def __init__(self, parser, separator_parser):
        self.parser = parser
        self.separator_parser = separator_parser

    def run(self, cursor, backtracking=False):
        result = []
        while True:
            item = self.parser.run(cursor, backtracking)
            if item.status == ResultStatus.OK:
                result.append(item.parsed)
            elif item.status == ResultStatus.BACKTRACKED:
                if len(result) == 0:
                    return item
                else:
                    break
            else:
                return item
            backtracking = True
            separator = self.separator_parser.run(cursor, backtracking)
            if separator.status == ResultStatus.BACKTRACKED:
                break
        
        return Result.Ok(Maybe.filter(result))


class ExpectKind(Parser):
    def __init__(self, kind):
        self.kind = kind

    def run(self, cursor, backtracking=False):
        if cursor.has() and cursor.peek().kind == self.kind:
            return Result.Ok(Maybe.Just(cursor.take()))
        elif backtracking:
            return Result.Backtracked() 
        elif not cursor.has():
            return Result.Error(f"expected {self.kind}, found EOF")
        else:
            found_token = cursor.peek()
            line, column = found_token.location.line_and_column()
            return Result.Error(f"expected {self.kind}, found {found_token.kind} at line {line}, column {column}")


class ExpectExact(Parser):
    def __init__(self, value):
        self.value = value

    def run(self, cursor, backtracking=False):
        if cursor.has() and cursor.peek() == self.value:
            return Result.Ok(Maybe.Just(cursor.take()))
        elif backtracking:
            return Result.Backtracked() 
        elif not cursor.has():
            return Result.Error(f"expected {self.value}, found EOF")
        else:
            return Result.Error(f"expected {self.value}, found {cursor.peek()}")


class Recursive(Parser):
    def __init__(self, inner):
        self.inner = inner

    def run(self, cursor, backtracking=False):
        return self.inner(self).run(cursor, backtracking)


class Unreachable(Parser):
    def __init__(self, msg: str=""):
        self.msg = msg
    def run(self, cursor, backtracking):
        return Result.Error(f"This should be unreachable ({self.msg})")
    

class ExpectEof(Parser):
    def run(self, cursor, backtracking):
        if not cursor.has():
            return Result.Ok(Maybe.Nothing())
        elif backtracking:
            return Result.Backtracked()
        else:
            found_token = cursor.peek()
            line, column = found_token.location.line_and_column()
            return Result.Error(f"expected EOF, found {found_token} at line {line}, column {column}")

def exact(value):
    return ExpectExact(value)