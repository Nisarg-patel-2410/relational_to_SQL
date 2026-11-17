"""
Plain-English explanation of a relational algebra query.

Works on the expression tree (AST) built by converter.ExpressionTreeBuilder,
so the explanation always matches the SQL that was generated from the same tree.

Usage:
    from explainer import explain
    text = explain(processor.tree)
"""

import re
import converter as c

# Order matters: longer operators first so ">=" is not read as ">" + "=".
_OPS = [
    (r">=", " is at least "),
    (r"<=", " is at most "),
    (r"!=|<>", " is not "),
    (r"=", " is "),
    (r">", " is greater than "),
    (r"<", " is less than "),
    (r"∧|\bAND\b", " and "),
    (r"∨|\bOR\b", " or "),
    (r"¬|\bNOT\b", " not "),
]
_OP_RE = re.compile("|".join(f"({p})" for p, _ in _OPS), re.IGNORECASE)
# Split on quoted strings so operators inside literals ('a=b') are left alone.
_QUOTED_RE = re.compile(r"('[^']*'|\"[^\"]*\")")


def condition_to_english(cond: str) -> str:
    """age>=20 ∧ dept='CS'  ->  age is at least 20 and dept is 'CS'"""
    parts = _QUOTED_RE.split(cond)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # quoted literal
            out.append(part)
            continue
        out.append(_OP_RE.sub(lambda m: _OPS[m.lastindex - 1][1], part))
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _list(items) -> str:
    items = [i.strip() for i in items if i.strip()]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


_AGG_WORDS = {"COUNT": "number of", "SUM": "total", "AVG": "average",
              "MIN": "smallest", "MAX": "largest", "TOTAL": "total",
              "GROUP_CONCAT": "list of"}


def _agg_english(expr: str) -> str:
    m = re.match(r"^\s*([A-Za-z_]+)\s*\((.*)\)\s*$", expr)
    if not m:
        return expr
    func, arg = m.group(1).upper(), m.group(2).strip()
    if func == "COUNT" and arg == "*":
        return "number of rows"
    distinct = arg.upper().startswith("DISTINCT ")
    if distinct:
        arg = arg[9:].strip()
    word = _AGG_WORDS.get(func, func.lower())
    return f"{word} {'distinct ' if distinct else ''}{arg}" + (" values" if func == "COUNT" else "")


def _phrase(node) -> str:
    """Return a noun phrase describing what this node produces."""
    if isinstance(node, c.TableNode):
        return node.name

    if isinstance(node, c.ProjectionNode):
        return f"the {_list(node.columns)} of {_phrase(node.child)}"

    if isinstance(node, c.SelectionNode):
        conds = []
        while isinstance(node, c.SelectionNode):      # σ a (σ b (R)) -> R where b and a
            conds.insert(0, condition_to_english(node.condition))
            node = node.child
        return f"{_phrase(node)} where {' and '.join(conds)}"

    if isinstance(node, c.RenameNode):
        cols = f" with columns {_list(node.columns)}" if node.columns else ""
        return f"{_sub(node.child)} renamed to {node.new_name}{cols}"

    if isinstance(node, c.GroupNode):
        aggs = [f"{_agg_english(x)} (as {a})" for x, a in node.aggregates]
        if node.group_cols:
            return (f"the {_list(node.group_cols + aggs)} for each "
                    f"{_list(node.group_cols)} group of {_sub(node.child)}")
        return f"the {_list(aggs)} over {_sub(node.child)}"

    L = _sub(getattr(node, "left", None))
    R = _sub(getattr(node, "right", None))

    if isinstance(node, c.CrossJoinNode):
        return f"every pairing of a row from {L} with a row from {R}"
    if isinstance(node, c.ThetaJoinNode):
        return f"{L} joined with {R} where {condition_to_english(node.condition)}"
    if isinstance(node, c.OuterJoinNode):
        how = (f"where {condition_to_english(node.condition)}" if node.condition
               else "on their matching common columns")
        keep = {"left": f"every row of {L}", "right": f"every row of {R}",
                "full": "every row of both sides"}[node.kind]
        return (f"{L} {node.kind}-outer-joined with {R} {how}, keeping {keep} "
                f"even without a match (missing values are empty)")
    if isinstance(node, c.NaturalJoinNode):
        return f"{L} combined with {R} on their matching common columns"
    if isinstance(node, c.DivisionNode):
        return f"the values in {L} that are paired with every row of {R}"
    if isinstance(node, c.UnionNode):
        return f"everything in {L} or in {R}, without duplicates"
    if isinstance(node, c.IntersectNode):
        return f"everything that is in both {L} and {R}"
    if isinstance(node, c.MinusNode):
        return f"everything in {L} that is not in {R}"

    return "the result"


def _sub(node) -> str:
    """Phrase for an operand; bracket compound ones so the sentence stays unambiguous."""
    if node is None:
        return "the result"
    text = _phrase(node)
    return text if isinstance(node, (c.TableNode, c.ProjectionNode)) else f"({text})"


def explain(tree) -> str:
    """Full English sentence for an expression tree."""
    if isinstance(tree, c.TableNode):
        return f"Show all rows of {tree.name}."
    return "Show " + _phrase(tree) + "."
