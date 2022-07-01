#!/usr/bin/env python3

"""
this is a simplified parser that only does
variable <comparison> value
"""

import ast

from uel import OpAnd, OpLess, OpLessEqual, OpGreater, OpGreaterEqual
from uel import OpEqual, OpNotEqual, ModNeg, Ident, assert_source
from uel import Value, ParserError


class ConjunctionParser:

    IDENT_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789")
    DISALLOWED_STARTING_IDENT_CHARS = set("0123456789.")
    NUMBER_CHARS = set("0123456789_.")

    def __init__(self, io):
        if hasattr(io, "read"):
            self.source = io.read()
        else:
            self.source = io
        self.pos = 0
        self.line = 1
        self.col = 1
        self.current_char = self.source[:1]

    def advance(self, distance=1):
        for _ in range(distance):
            assert not self.eof()
            if self.current_char == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.pos += 1
            if self.pos >= len(self.source):
                self.current_char = None
            else:
                self.current_char = self.source[self.pos]

    def checkpoint(self):
        return (self.pos, self.col, self.line)

    def restore(self, checkpoint):
        self.pos, self.col, self.line = checkpoint
        if self.pos >= len(self.source):
            self.current_char = None
        else:
            self.current_char = self.source[self.pos]

    def source_ref(self, checkpoint):
        return checkpoint[2], checkpoint[1]

    def assert_source(self, message, line=None, col=None):
        if line is None:
            line = self.line
        if col is None:
            col = self.col
        assert_source(ParserError, message, line, col)

    def eof(self, lookahead=0):
        assert lookahead >= 0
        return self.pos + lookahead >= len(self.source)

    def char(self, lookahead=0, required=False):
        if self.pos + lookahead >= len(self.source) or self.pos + lookahead < 0:
            if not required:
                return None
            assert lookahead >= 0
            self.assert_source("end of input unexpected")
        return self.source[self.pos + lookahead]

    def string(self, width):
        return self.source[self.pos : self.pos + width]

    def skip_comment(self):
        if self.current_char != "#":
            return False
        self.advance()
        while True:
            if self.eof():
                return True
            self.advance()
            if self.current_char == "\n":
                return True

    def skip_whitespace(self):
        if self.eof():
            return False
        if self.skip_comment():
            return True
        if self.current_char in " \t\r\n":
            self.advance()
            return True
        return False

    def skip_all_whitespace(self):
        any_skipped = False
        while self.skip_whitespace():
            any_skipped = True
        return any_skipped

    def parse_identifier(self):
        if self.current_char in self.DISALLOWED_STARTING_IDENT_CHARS:
            return None
        chars = self.parse_chars(self.IDENT_CHARS)
        if chars is None:
            return None
        return Ident(chars)

    def parse_value(self):
        nums = self.parse_chars(self.NUMBER_CHARS)
        if nums is None:
            return None
        return Value(ast.literal_eval(nums))

    def parse_chars(self, allowed):
        if self.current_char not in allowed:
            return None
        chars = self.current_char
        self.advance()
        while self.current_char in allowed:
            chars += self.current_char
            self.advance()
        self.skip_all_whitespace()
        return chars

    def parse_val_negation(self):
        return self.parse_modifier(self.parse_value, {ModNeg: ["-"]})

    def parse_comparison(self):
        lhs = self.parse_identifier()
        if lhs is None:
            self.assert_source("identifier expected")
        cls, rhs = self.parse_op_and_rhs(
            self.parse_val_negation,
            {
                OpLess: ["<"],
                OpLessEqual: ["<="],
                OpEqual: ["=="],
                OpNotEqual: ["!=", "~=", "<>"],
                OpGreater: [">"],
                OpGreaterEqual: [">="],
            },
        )
        if cls is None:
            self.assert_source("comparison expected")
        return cls(lhs, rhs)

    def parse_conjunction(self):
        return self.parse_operation(self.parse_comparison, {OpAnd: ["&&", "and"]})

    def parse_operation(self, value_parse, op_map):
        val = value_parse()
        while True:
            if self.eof():
                return val
            cls, rhs = self.parse_op_and_rhs(value_parse, op_map)
            if cls is None:
                break
            val = cls(val, rhs)
        return val

    def parse_modifier(self, value_parse, mod_map):
        cls, val = self.parse_op_and_rhs(value_parse, mod_map)
        if cls is not None:
            return cls(val)
        return value_parse()

    def is_boundary(self, char1, char2):
        return char1 not in self.IDENT_CHARS or char2 not in self.IDENT_CHARS

    def parse_op_and_rhs(self, value_parse, op_map):
        checkpoint = self.checkpoint()
        for cls, operators in op_map.items():
            for op in operators:
                if self.string(len(op)).lower() == op and self.is_boundary(
                    self.char(len(op) - 1), self.char(len(op))
                ):
                    self.advance(len(op))
                    self.skip_all_whitespace()
                    rhs = value_parse()
                    if rhs is not None:
                        return cls, rhs
                    self.restore(checkpoint)
        return None, None

    def parse(self):
        self.skip_all_whitespace()
        val = self.parse_expression()
        if not self.eof():
            self.assert_source("unparsed input")
        return val

    def parseIdentOnly(self):
        self.skip_all_whitespace()
        val = self.parse_identifier()
        if not self.eof():
            self.assert_source("unparsed input")
        return val

    def parse_expression(self):
        return self.parse_conjunction()


def run_tests():
    def check_result(input, env, expected):
        val = conjunction_eval(input, env)
        if val != expected:
            raise Exception(
                "input %r with env %r expected %r, got %r" % (input, env, expected, val)
            )

    check_result("x < 2", {"x": 1}, True)
    check_result("x > 2", {"x": 3}, True)
    check_result("x > 2 and y < 1", {"x": 3, "y": 0}, True)
    check_result("x > 2 and y >= 1", {"x": 3, "y": 0}, False)


def conjunction_eval(expression, env):
    return ConjunctionParser(expression).parse().run(env)


def conjunction_parse(expression):
    return ConjunctionParser(expression).parse()


def identifier_parse(expression):
    return ConjunctionParser(expression).parseIdentOnly()


if __name__ == "__main__":
    run_tests()
