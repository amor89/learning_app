"""Static rules evaluated on the syntax tree of submitted Python or PySpark code.

Each rule is a dict with a ``kind``, an ``id``, a ``message`` and kind-specific keys.
A rule returns ``True`` when the code satisfies it.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from typing import Any

Rule = dict[str, Any]
RuleFn = Callable[[ast.Module, str, Rule], bool]

MUTABLE_DEFAULT_NODES = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)


def dotted_name(node: ast.expr) -> str:
    """Return the dotted source name of a call target, such as ``F.col`` or ``df.count``.

    Args:
        node: The ``func`` node of an ``ast.Call``.

    Returns:
        The dotted name, or an empty string when the target is not a plain name chain.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else f"?.{node.attr}"
    if isinstance(node, ast.Call):
        return f"{dotted_name(node.func)}()"
    return ""


def call_matches(call_name: str, wanted: str) -> bool:
    """Match a call name against a rule target.

    A target with a dot must match the end of the dotted name (``F.broadcast``).
    A bare target matches the last segment (``count`` matches ``df.count``).

    Args:
        call_name: Dotted name from :func:`dotted_name`.
        wanted: Target name from the rule.

    Returns:
        True when the call matches the target.
    """
    if "." in wanted:
        return call_name == wanted or call_name.endswith(f".{wanted}")
    return call_name.rsplit(".", 1)[-1] == wanted


def iter_call_names(tree: ast.Module) -> list[str]:
    """List the dotted names of every call in the tree."""
    return [dotted_name(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]


def count_calls(tree: ast.Module, wanted: str) -> int:
    """Count calls whose name matches ``wanted``."""
    return sum(1 for name in iter_call_names(tree) if call_matches(name, wanted))


def find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    """Return the top-level or nested function definition with this name."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _requires_call(tree: ast.Module, _source: str, rule: Rule) -> bool:
    return count_calls(tree, rule["name"]) >= int(rule.get("min", 1))


def _forbids_call(tree: ast.Module, _source: str, rule: Rule) -> bool:
    return count_calls(tree, rule["name"]) == 0


def _max_calls(tree: ast.Module, _source: str, rule: Rule) -> bool:
    return count_calls(tree, rule["name"]) <= int(rule["max"])


def _requires_import(tree: ast.Module, _source: str, rule: Rule) -> bool:
    module = rule["module"]
    name = rule.get("name")
    alias = rule.get("alias")
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module and name:
            for imported in node.names:
                if imported.name == name and (alias is None or imported.asname == alias):
                    return True
        if isinstance(node, ast.Import) and not name:
            for imported in node.names:
                if imported.name == module and (alias is None or imported.asname == alias):
                    return True
    return False


def _forbids_import_from(tree: ast.Module, _source: str, rule: Rule) -> bool:
    banned = set(rule["names"])
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == rule["module"]:
            for imported in node.names:
                if imported.name == "*" or imported.name in banned:
                    return False
    return True


def _requires_function(tree: ast.Module, _source: str, rule: Rule) -> bool:
    func = find_function(tree, rule["name"])
    if func is None:
        return False
    if rule.get("typed"):
        params = [*func.args.posonlyargs, *func.args.args, *func.args.kwonlyargs]
        if any(p.annotation is None for p in params if p.arg not in {"self", "cls"}):
            return False
        if func.returns is None:
            return False
    return not (rule.get("docstring") and ast.get_docstring(func) is None)


def _forbids_decorator(tree: ast.Module, _source: str, rule: Rule) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for deco in node.decorator_list:
                target = deco.func if isinstance(deco, ast.Call) else deco
                if call_matches(dotted_name(target), rule["name"]):
                    return False
    return True


def _forbids_compare_to_bool(tree: ast.Module, _source: str, _rule: Rule) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op, right in zip(node.ops, node.comparators, strict=True):
                is_bool = isinstance(right, ast.Constant) and isinstance(right.value, bool)
                if is_bool and isinstance(op, ast.Eq | ast.NotEq):
                    return False
    return True


def _forbids_mutable_default(tree: ast.Module, _source: str, _rule: Rule) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            defaults = [*node.args.defaults, *(d for d in node.args.kw_defaults if d)]
            if any(isinstance(d, MUTABLE_DEFAULT_NODES) for d in defaults):
                return False
    return True


def _forbids_bare_truthiness(tree: ast.Module, _source: str, rule: Rule) -> bool:
    """Fail when a listed name is tested for truth without a comparison."""
    names = set(rule["names"])

    def bare_names(test: ast.expr) -> set[str]:
        if isinstance(test, ast.Name):
            return {test.id}
        if isinstance(test, ast.BoolOp):
            found: set[str] = set()
            for value in test.values:
                found |= bare_names(value)
            return found
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return bare_names(test.operand)
        return set()

    for node in ast.walk(tree):
        if isinstance(node, ast.If | ast.IfExp | ast.While) and bare_names(node.test) & names:
            return False
    return True


def _requires_pattern(_tree: ast.Module, source: str, rule: Rule) -> bool:
    return re.search(rule["pattern"], source, re.MULTILINE) is not None


def _forbids_pattern(_tree: ast.Module, source: str, rule: Rule) -> bool:
    return re.search(rule["pattern"], source, re.MULTILINE) is None


RULES: dict[str, RuleFn] = {
    "requires_call": _requires_call,
    "forbids_call": _forbids_call,
    "max_calls": _max_calls,
    "requires_import": _requires_import,
    "forbids_import_from": _forbids_import_from,
    "requires_function": _requires_function,
    "forbids_decorator": _forbids_decorator,
    "forbids_compare_to_bool": _forbids_compare_to_bool,
    "forbids_mutable_default": _forbids_mutable_default,
    "forbids_bare_truthiness": _forbids_bare_truthiness,
    "requires_pattern": _requires_pattern,
    "forbids_pattern": _forbids_pattern,
}


def evaluate_rule(tree: ast.Module, source: str, rule: Rule) -> bool:
    """Evaluate one rule.

    Args:
        tree: Parsed module.
        source: Original source text.
        rule: Rule definition.

    Returns:
        True when the code satisfies the rule.

    Raises:
        KeyError: If the rule kind is unknown.
    """
    return RULES[rule["kind"]](tree, source, rule)
