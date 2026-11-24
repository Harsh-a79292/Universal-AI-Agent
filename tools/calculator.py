import ast
import operator
import math
from typing import Dict, Any

# Allowed operators and safe functions for calculator
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "pow": math.pow,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}

def _eval_node(node):
    if isinstance(node, ast.Constant): # number literal
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.Name): # constant like pi or e
        if node.id.lower() in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id.lower()]
        raise ValueError(f"Unknown variable: '{node.id}'")
    elif isinstance(node, ast.BinOp): # binary op e.g. a + b
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            if op_type == ast.Pow and (left > 10000 or right > 1000):
                raise ValueError("Calculation overflow prevention")
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported operator: {op_type.__name__}")
    elif isinstance(node, ast.UnaryOp): # unary op e.g. -x
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            operand = _eval_node(node.operand)
            return SAFE_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    elif isinstance(node, ast.Call): # function call e.g. sqrt(16)
        if isinstance(node.func, ast.Name) and node.func.id.lower() in SAFE_FUNCTIONS:
            func = SAFE_FUNCTIONS[node.func.id.lower()]
            args = [_eval_node(arg) for arg in node.args]
            return func(*args)
        raise ValueError(f"Function call not allowed: {ast.dump(node.func)}")
    else:
        raise ValueError(f"Expression type '{type(node).__name__}' is not allowed for safety.")

def calculate_expression(expression: str) -> Dict[str, Any]:
    """
    Safely evaluate a mathematical expression using AST parsing without eval() or exec().
    Supports +, -, *, /, //, %, **, sqrt, round, abs, log, pi, e, etc.
    """
    try:
        clean_expr = expression.strip().replace("^", "**")
        parsed = ast.parse(clean_expr, mode='eval')
        result = _eval_node(parsed.body)
        return {
            "success": True,
            "expression": expression,
            "result": result,
            "error": None
        }
    except ZeroDivisionError:
        return {
            "success": False,
            "expression": expression,
            "result": None,
            "error": "Division by zero is undefined."
        }
    except Exception as e:
        return {
            "success": False,
            "expression": expression,
            "result": None,
            "error": f"Invalid math expression: {str(e)}"
        }

