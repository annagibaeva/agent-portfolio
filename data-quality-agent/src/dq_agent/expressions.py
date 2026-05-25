from __future__ import annotations

import ast
import operator
from typing import Any

import pandas as pd


class ExpressionError(ValueError):
    pass


COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
}


def evaluate_expression(dataframe: pd.DataFrame, expression: str) -> pd.Series:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"Invalid expression syntax: {expression}") from exc
    result = _eval_node(tree.body, dataframe)
    if isinstance(result, pd.Series):
        return result.fillna(False).astype(bool)
    return pd.Series([bool(result)] * len(dataframe), index=dataframe.index)


def _eval_node(node: ast.AST, dataframe: pd.DataFrame) -> Any:
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(value, dataframe) for value in node.values]
        result = values[0]
        for value in values[1:]:
            if isinstance(node.op, ast.And):
                result = result & value
            elif isinstance(node.op, ast.Or):
                result = result | value
            else:
                raise ExpressionError("Unsupported boolean operator.")
        return result

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, dataframe)
        comparisons = []
        for op_node, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, dataframe)
            op = COMPARE_OPS.get(type(op_node))
            if op is None:
                raise ExpressionError("Unsupported comparison operator.")
            comparisons.append(op(left, right))
            left = right
        result = comparisons[0]
        for comparison in comparisons[1:]:
            result = result & comparison
        return result

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return ~_eval_node(node.operand, dataframe)

    if isinstance(node, ast.Name):
        if node.id == "null":
            return None
        if node.id not in dataframe.columns:
            raise ExpressionError(f"Unknown column in expression: {node.id}")
        return dataframe[node.id]

    if isinstance(node, ast.Constant):
        return node.value

    raise ExpressionError(f"Unsupported expression element: {type(node).__name__}")
