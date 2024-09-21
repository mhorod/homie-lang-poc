from typing import *
from enum import Enum, auto
from dataclasses import dataclass
from abc import ABC, abstractmethod
from tokens import Token, KIND_TO_STR
from source import *
from error_reporting import *

class TokenCursor:
    def __init__(self, tokens, index=0):
        self.tokens = tokens
        self.index = index

    def has(self):
        return self.index < len(self.tokens)

    def peek(self):
        if not self.has():
            return self.eof()
        return self.tokens[self.index]
    
    def take(self):
        result = self.tokens[self.index]
        self.index += 1
        return result

    def save(self):
        return self.index

    def restore(self, index):
        self.index = index

    def prev(self):
        return self.tokens[self.index - 1]

    def eof(self):
        return Token("<eof>", None, self.eof_location())

    def eof_location(self):
        loc = self.tokens[-1].location
        return Location(loc.source, loc.end, loc.end + 1)

class ResultStatus(Enum):
    '''
    Result of parsing (running a parser on an input)
    Ok - Parsing was successful
    Err - Parsing failed with a fatal error
    Backtracked - Parsing failed and backtracked to starting position
    '''
    Ok = auto()
    Err = auto()
    Backtracked = auto() 

@dataclass
class Result[T]:
    status: ResultStatus
    parsed: T | None
    errors: List[Error]

    def Ok(parsed, errors=None):
        return Result(ResultStatus.Ok, parsed, errors or [])

    def Backtracked(errors=None):
        return Result(ResultStatus.Backtracked, None, errors or [])

    def Err(errors=None):
        return Result(ResultStatus.Err, None, errors or [])

    def map(self, mapper):
        if self.status != ResultStatus.Ok:
            return self
        else:
            return ResultStatus.Ok(mapper(self.parsed))
 

class Parser[T](ABC):
    @abstractmethod
    def run(self, cursor, backtracking=False) -> Result[T]:
        pass

    def __or__(self, rhs):
        return Alternative(self, rhs)
    
    def map(self, mapper):
        return Mapped(self, mapper)
    
    def replace(self, value):
        return Mapped(self, lambda _: value)

    def and_then(self, mapper):
        return AndThen(self, mapper)


class BuilderParser(Parser):
    class Commit:
        pass

    @dataclass
    class Drop:
        parser: Parser

    @dataclass
    class Parse:
        parser: Parser
        builder_method: callable

    def __init__(self, builder):
        self.builder = builder
        self.parts = []

    def commit(self):
        self.parts.append(BuilderParser.Commit())
        return self

    def then_drop(self, parser):
        self.parts.append(BuilderParser.Drop(parser))
        return self

    def then_parse(self, builder_method, parser):
        self.parts.append(BuilderParser.Parse(parser, builder_method))
        return self

    def run(self, cursor, backtracking):
        builder = self.builder()
        begin = cursor.peek().location
        for part in self.parts:
            if isinstance(part, BuilderParser.Commit):
                backtracking = False
            else:
                result = part.parser.run(cursor, backtracking)
                if result.status != ResultStatus.Ok:
                    return result
                elif isinstance(part, BuilderParser.Parse):
                    part.builder_method(builder, result.parsed)
        end = cursor.prev().location
        return Result.Ok(builder.build(Location.wrap(begin, end)))

    def __repr__(self):
        return f"BuilderParser({self.builder})"


class Mapped(Parser):
    def __init__(self, parser, mapper):
        self.parser = parser
        self.mapper = mapper

    def run(self, cursor, backtracking=False):
        result = self.parser.run(cursor, backtracking)
        if result.status == ResultStatus.Ok:
            result.parsed = self.mapper(result.parsed)
        return result

class AndThen(Parser):
    def __init__(self, parser, mapper):
        self.parser = parser
        self.mapper = mapper

    def run(self, cursor, backtracking=False):
        result = self.parser.run(cursor, backtracking)
        if result.status == ResultStatus.Ok:
            return self.mapper(result.parsed)
        return result



class Repeat[T](Parser):
    def __init__(self, parser, minimum=0):
        self.parser = parser
        self.minimum = minimum

    def run(self, cursor, backtracking=False) -> Result[List[T]]:
        cursor_state = cursor.save()
        result = []
        while True:
            if not cursor.has():
                break
            if len(result) >= self.minimum:
                backtracking = True
            parsed = self.parser.run(cursor, backtracking)
            if parsed.status == ResultStatus.Ok:
                result.append(parsed.parsed)
            elif parsed.status == ResultStatus.Backtracked:
                break
            else:
                return parsed
        
        if len(result) < self.minimum:
            cursor.restore(cursor_state)
            return Result.Backtracked()
        
        return Result.Ok(result)


class Alternative[T, U](Parser[T | U]):
    def __init__(self, left: Parser[T], right: Parser[U]):
        self.left = left
        self.right = right

    def run(self, cursor, backtracking=False) -> Result[T | U]:
        cursor_state = cursor.save()
        result = self.left.run(cursor, backtracking=True)
        if result.status == ResultStatus.Ok or result.status == ResultStatus.Err:
            return result
        else:
            cursor.restore(cursor_state)
            return self.right.run(cursor, backtracking)

class SequenceParser[T](Parser[T]):
    class ListBuilder:
        def __init__(self):
            self.list = []

        def append(self, item):
            self.list.append(item)

        def build(self, location):
            return self.list

    def __init__(self):
        self.builder = BuilderParser(SequenceParser.ListBuilder)

    def then_drop(self, parser):
        self.builder.then_drop(parser)
        return self

    def then_parse(self, parser):
        self.builder.then_parse(SequenceParser.ListBuilder.append, parser)
        return self

    def commit(self):
        self.builder.commit()
        return self

    def run(self, cursor, backtracking=False) -> Result[List[T]]:
        return self.builder.run(cursor, backtracking)

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

class OptionalParser[T](Parser):
    def __init__(self, parser, default):
        self.parser = parser
        self.default = default

    def run(self, cursor, backtracking=False) -> Result[List[T]]:
        result = self.parser.run(cursor, True)
        if result.status == ResultStatus.Backtracked:
            result.status = ResultStatus.Ok
            result.parsed = self.default
        return result


class Interspersed(Parser):
    def __init__(self, parser, separator_parser, minimum=0):
        self.parser = parser
        self.separator_parser = separator_parser
        self.minimum = minimum

    def run(self, cursor, backtracking=False):
        cursor_state = cursor.save()
        result = []
        while True:
            if len(result) >= self.minimum:
                backtracking = True

            item = self.parser.run(cursor, backtracking)
            if item.status == ResultStatus.Ok:
                result.append(item.parsed)
            elif item.status == ResultStatus.Backtracked:
                if len(result) < self.minimum:
                    cursor.restore(cursor_state)
                    return Result.Backtracked(item.errors)
                else:
                    break
            else:
                return item

            if len(result) >= self.minimum:
                backtracking = True

            separator = self.separator_parser.run(cursor, backtracking)
            if separator.status == ResultStatus.Backtracked:
                if len(result) < self.minimum:
                    cursor.restore(cursor_state)
                    return Result.Backtracked(item.errors)
                else:
                    break
            elif separator.status == ResultStatus.Err:
                return separator
        
        return Result.Ok(result)


class ExpectKind(Parser):
    def __init__(self, kind):
        self.kind = kind

    def run(self, cursor, backtracking=False):
        if cursor.has() and cursor.peek().kind == self.kind:
            return Result.Ok(cursor.take())
        elif backtracking:
            return Result.Backtracked() 
        else:
            found_token = cursor.peek()
            kind_name = KIND_TO_STR[self.kind]
            msg = Message(found_token.location, f"expected {kind_name}, found {found_token.text}")
            return Result.Err([Error(msg)])
    def __repr__(self):
        return f"Expect({self.kind})"


class Recursive(Parser):
    def __init__(self, inner):
        self.inner = inner

    def run(self, cursor, backtracking=False):
        return self.inner(self).run(cursor, backtracking)


class Unreachable(Parser):
    def __init__(self, msg: str=""):
        self.msg = msg
    def run(self, cursor, backtracking):
        found_token = cursor.peek()
        msg = Message(found_token.location, f"Parser has reached an unreachable state")
        return Result.Err([Error(msg)])
    
class Nothing(Parser):
    def run(self, cursor, backtracking):
        return Result.Ok(None)

class ExpectEof(Parser):
    def run(self, cursor, backtracking):
        if not cursor.has():
            return Result.Ok(None)
        elif backtracking:
            return Result.Backtracked()
        else:
            found_token = cursor.peek()
            msg = Message(found_token.location, f"Expected <eof>, found {found_token.text}")
            return Result.Err([Error(msg)])

class Fail(Parser):
    def __init__(self, expected):
        self.expected = expected

    def run(self, cursor, backtracking):
        if backtracking:
            return Result.Backtracked()
        found_token = cursor.peek()
        msg = Message(found_token.location, f"Expected {self.expected}, found {found_token.text}")
        return Result.Err([Error(msg)])

class Not(Parser):
    def __init__(self, parser):
        self.parser = parser

    def run(self, cursor, backtracking):
        cursor_state = cursor.save()
        result = self.parser.run(cursor, False)
        if result.status == ResultStatus.Ok:
            if backtracking:
                cursor.restore(cursor_state)
                return Result.Backtracked()
            else:
                found_token = cursor.peek()
                msg = Message(found_token.location, f"Unexpected token {found_token.text}")
                return Result.Err([Error(msg)])
        else:
            return Result.Ok(None)
        
class Supply(Parser):
    def __init__(self, supplier):
        self.supplier = supplier

    def run(self, cursor, backtracking):
        return Result.Ok(self.supplier())

