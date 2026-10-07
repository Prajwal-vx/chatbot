import ast
import math
import operator

_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def calculate(expression: str) -> int | float:
    """Evaluate a restricted arithmetic expression without Python eval()."""
    if len(expression) > 100:
        raise ValueError("Expression is too long")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 50:
        raise ValueError("Expression is too complex")

    def visit(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 1e12:
                raise ValueError("Number is outside the supported range")
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent is outside the supported range")
            result = _BINARY[type(node.op)](left, right)
            if not math.isfinite(float(result)) or abs(result) > 1e15:
                raise ValueError("Result is outside the supported range")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](visit(node.operand))
        raise ValueError("Only basic arithmetic is supported")

    return visit(tree)
