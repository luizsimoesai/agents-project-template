"""Simple tools for the DeepAgent example."""

import ast
import operator
from datetime import UTC, datetime

from langchain_core.tools import tool

_SAFE_OPS: dict[type, object] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval_expr(node: ast.expr) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        op_fn = _SAFE_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op_fn(_eval_expr(node.left), _eval_expr(node.right))  # type: ignore[operator]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_expr(node.operand)
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


@tool
def get_current_time() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(tz=UTC).isoformat()


@tool
def calculator(expression: str) -> str:
    """Evaluate a safe arithmetic expression (e.g. '2 + 3 * 4') and return the result."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_expr(tree.body)
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


TOOLS = [get_current_time, calculator]
