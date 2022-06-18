#!/usr/bin/env python3

"""
the uncommon expression language. this is like CEL but instead of using
protobufs it lets you use your own types kind of like userdata in lua.
"""

import ast


class ParserError(Exception):
    pass


def assert_source(exception, message, line, col):
    raise exception("Error at line %d, column %d: %s" % (line, col, message))


class Parser:

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

    def parse_literal(self):
        var = self.parse_identifier()
        if var is not None:
            return var
        return self.parse_value()

    def parse_subexpression(self):
        if self.char() != "(":
            return self.parse_literal()
        self.advance()
        expr = self.parse_expression()
        self.skip_all_whitespace()
        if self.char() != ")":
            self.assert_source(
                "subexpression ended unexpectedly, found %r" % self.char()
            )
        self.advance()
        self.skip_all_whitespace()
        return Subexpression(expr)

    def parse_exponentiation(self):
        return self.parse_operation(
            self.parse_subexpression,
            {
                OpExp: ["^"],
            },
        )

    def parse_val_negation(self):
        return self.parse_modifier(self.parse_exponentiation, {ModNeg: ["-"]})

    def parse_multiplication_division(self):
        return self.parse_operation(
            self.parse_val_negation,
            {
                OpMul: ["*"],
                OpDiv: ["/"],
            },
        )

    def parse_addition_subtraction(self):
        return self.parse_operation(
            self.parse_multiplication_division,
            {
                OpAdd: ["+"],
                OpSub: ["-"],
            },
        )

    def parse_comparison(self):
        return self.parse_operation(
            self.parse_addition_subtraction,
            {
                OpLess: ["<"],
                OpLessEqual: ["<="],
                OpEqual: ["=="],
                OpNotEqual: ["!=", "~=", "<>"],
                OpGreater: [">"],
                OpGreaterEqual: [">="],
            },
        )

    def parse_bool_negation(self):
        return self.parse_modifier(self.parse_comparison, {ModNot: ["!", "not"]})

    def parse_conjunction(self):
        return self.parse_operation(self.parse_bool_negation, {OpAnd: ["&&", "and"]})

    def parse_disjunction(self):
        return self.parse_operation(self.parse_conjunction, {OpOr: ["||", "or"]})

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

    def parse_expression(self):
        return self.parse_disjunction()


class Subexpression:
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return "(%r)" % self.expr

    def run(self, env):
        return self.expr.run(env)


class Operation:
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return "(%r) %s (%r)" % (self.lhs, self.op, self.rhs)

    def run(self, env):
        return (env.get(type(self)) or DEFAULT_ENV.get(type(self)))(
            self.lhs.run(env), self.rhs.run(env)
        )


class OpOr(Operation):
    op = "or"


class OpAnd(Operation):
    op = "and"


class OpAdd(Operation):
    op = "+"


class OpSub(Operation):
    op = "-"


class OpMul(Operation):
    op = "*"


class OpDiv(Operation):
    op = "/"


class OpLess(Operation):
    op = "<"


class OpLessEqual(Operation):
    op = "<="


class OpEqual(Operation):
    op = "=="


class OpNotEqual(Operation):
    op = "!="


class OpGreater(Operation):
    op = ">"


class OpGreaterEqual(Operation):
    op = ">="


class OpExp(Operation):
    op = "^"


class Modifier:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return "%r (%r)" % (self.op, self.val)

    def run(self, env):
        return (env.get(type(self)) or DEFAULT_ENV.get(type(self)))(self.val.run(env))


class ModNot(Modifier):
    op = "not"


class ModNeg(Modifier):
    op = "-"


DEFAULT_ENV = {
    OpOr: lambda a, b: a or b,
    OpAnd: lambda a, b: a and b,
    OpAdd: lambda a, b: a + b,
    OpSub: lambda a, b: a - b,
    OpMul: lambda a, b: a * b,
    OpDiv: lambda a, b: a / b,
    OpLess: lambda a, b: a < b,
    OpLessEqual: lambda a, b: a <= b,
    OpEqual: lambda a, b: a == b,
    OpNotEqual: lambda a, b: a != b,
    OpGreater: lambda a, b: a > b,
    OpGreaterEqual: lambda a, b: a >= b,
    OpExp: lambda a, b: a**b,
    ModNot: lambda x: not x,
    ModNeg: lambda x: -x,
}


class Ident:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def run(self, env):
        return env[self.name]


class Value:
    def __init__(self, val):
        self.val = val

    def __repr__(self):
        return repr(self.val)

    def run(self, env):
        return self.val


def run_tests():
    def check_result(input, env, expected):
        val = uel_eval(input, env)
        if val != expected:
            raise Exception(
                "input %r with env %r expected %r, got %r" % (input, env, expected, val)
            )

    check_result("1 + 2", {}, 3)
    check_result("1+2", {}, 3)
    check_result("1 - 2", {}, -1)
    check_result("1+2 * 3 / 4 * 5", {}, 1 + ((2 * 3) / 4) * 5)
    check_result("(1+2)*3/4*5", {}, (1 + 2) * 3 * 5 / 4)
    check_result(
        """
    1 # a one
    + 2 # add a two
  """,
        {},
        3,
    )
    check_result("1 < 2", {}, True)
    check_result("1 > 2", {}, False)
    check_result("1 <= 2", {}, True)
    check_result("1 >= 2", {}, False)
    check_result("2 <= 2", {}, True)
    check_result("2 >= 2", {}, True)
    check_result("2 == 2", {}, True)
    check_result("not (2 != 2)", {}, True)
    check_result("2 != 2", {}, False)
    check_result("2 != 1", {}, True)
    check_result("2 == 1", {}, False)
    check_result("1 + (10 / 2) ", {}, 6)
    check_result("1 + (10 / 2) > 3", {}, True)


def uel_eval(expression, env):
    return Parser(expression).parse().run(env)


if __name__ == "__main__":
    run_tests()
