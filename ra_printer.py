"""
Turns an expression tree back into relational algebra text.

Used by the optimizer (to show the rewritten expression) and by the
SQL → relational algebra translator. The output can be fed straight back
into converter.QueryProcessor.
"""

import converter as c

_BINARY_SYMBOL = {
    c.CrossJoinNode: "×",
    c.NaturalJoinNode: "⋈",
    c.DivisionNode: "÷",
    c.UnionNode: "∪",
    c.IntersectNode: "∩",
    c.MinusNode: "−",
}
_JOIN_LEVEL = (c.CrossJoinNode, c.NaturalJoinNode, c.ThetaJoinNode,
               c.OuterJoinNode, c.DivisionNode)
_SET_LEVEL = (c.UnionNode, c.IntersectNode, c.MinusNode)


def _cond(cond: str) -> str:
    """Bracket form is used when the condition has parentheses that the
    plain 'σ cond (R)' form could confuse with the relation."""
    cond = " ".join(cond.split())
    return f"[{cond}]" if "(" in cond else cond


def _operand(node, parent, is_left: bool) -> str:
    text = to_ra(node)
    binary = isinstance(node, _JOIN_LEVEL + _SET_LEVEL)
    if not binary:
        return text
    same_level = (isinstance(parent, _JOIN_LEVEL) and isinstance(node, _JOIN_LEVEL)) or \
                 (isinstance(parent, _SET_LEVEL) and isinstance(node, _SET_LEVEL))
    if is_left and same_level:
        return text                      # operators are left-associative
    return f"({text})"


def to_ra(node) -> str:
    if node is None:
        return ""
    if isinstance(node, c.TableNode):
        return node.name
    if isinstance(node, c.ProjectionNode):
        return f"π {', '.join(node.columns)} ({to_ra(node.child)})"
    if isinstance(node, c.SelectionNode):
        cond = _cond(node.condition)
        sep = "" if cond.startswith("[") else " "
        return f"σ{sep}{cond} ({to_ra(node.child)})"
    if isinstance(node, c.RenameNode):
        cols = f"({', '.join(node.columns)})" if node.columns else ""
        return f"ρ {node.new_name}{cols} ({to_ra(node.child)})"
    if isinstance(node, c.GroupNode):
        return f"γ {node.spec()} ({to_ra(node.child)})"

    left = _operand(node.left, node, True)
    right = _operand(node.right, node, False)
    if isinstance(node, c.ThetaJoinNode):
        return f"{left} ⋈[{node.condition}] {right}"
    if isinstance(node, c.OuterJoinNode):
        sym = node.SYMBOLS[node.kind]
        cond = f"[{node.condition}]" if node.condition else ""
        return f"{left} {sym}{cond} {right}"
    return f"{left} {_BINARY_SYMBOL[type(node)]} {right}"
