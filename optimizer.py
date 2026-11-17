"""
Heuristic (rule-based) query optimizer for relational algebra trees.

Applies the standard equivalence rules (Silberschatz et al., §16.2;
Elmasri & Navathe, §19.1) to move selections as close to the base
relations as possible, turn selections over Cartesian products into joins,
and remove redundant projections. Every rewrite is recorded so the user can
see which law was applied where.

    R1  Cascade of σ           σ c1∧c2 (E)        ≡ σ c1 (σ c2 (E))
    R2  σ commutes with π      σ c (π L (E))      ≡ π L (σ c (E))        if c uses only L
    R3  Push σ below a join    σ c (E1 ⋈ E2)      ≡ σ c (E1) ⋈ E2        if c uses only E1
    R4  σ over × → ⋈θ          σ c (E1 × E2)      ≡ E1 ⋈c E2
    R5  Merge σ into ⋈θ        σ c (E1 ⋈θ E2)     ≡ E1 ⋈θ∧c E2
    R6  Push σ into ∪ ∩ −      σ c (E1 ∪ E2)      ≡ σ c (E1) ∪ σ c (E2)
                               σ c (E1 − E2)      ≡ σ c (E1) − E2
    R7  Push σ below γ         σ c (γ G (E))      ≡ γ G (σ c (E))        if c uses only G
    R8  Cascade of π           π L1 (π L2 (E))    ≡ π L1 (E)
    R9  Combine σ              σ c1 (σ c2 (E))    ≡ σ c1∧c2 (E)

Outer joins only let a selection through to their preserved side
(left side of ⟕, right side of ⟖, neither for ⟗), since filtering the
null-padded side would change the result.
"""

import copy
import sqlite3

import converter as c
from conditions import conjuncts, attr_refs, normalize, split_keyword, strip_outer_parens
from ra_printer import to_ra

RULES = {
    "R1": ("Cascade of σ", "σ c1∧c2 (E) ≡ σ c1 (σ c2 (E))"),
    "R2": ("σ commutes with π", "σ c (π L (E)) ≡ π L (σ c (E))"),
    "R3": ("Push σ below join", "σ c (E1 ⋈ E2) ≡ σ c (E1) ⋈ E2"),
    "R4": ("σ over × becomes ⋈θ", "σ c (E1 × E2) ≡ E1 ⋈c E2"),
    "R5": ("Merge σ into ⋈θ", "σ c (E1 ⋈θ E2) ≡ E1 ⋈θ∧c E2"),
    "R6": ("Push σ into set operation", "σ c (E1 ∪ E2) ≡ σ c (E1) ∪ σ c (E2)"),
    "R7": ("Push σ below γ", "σ c (γ G (E)) ≡ γ G (σ c (E))"),
    "R8": ("Cascade of π", "π L1 (π L2 (E)) ≡ π L1 (E)"),
    "R9": ("Combine σ", "σ c1 (σ c2 (E)) ≡ σ c1∧c2 (E)"),
}

_JOINS = (c.CrossJoinNode, c.NaturalJoinNode, c.ThetaJoinNode, c.OuterJoinNode)


def _bare(name: str) -> str:
    return name.split(".")[-1].strip().strip('"').lower()


def _short(node, limit: int = 40) -> str:
    text = to_ra(node)
    return text if len(text) <= limit else text[:limit - 1] + "…"


class Optimizer:
    def __init__(self, db_name: str):
        self.db = db_name
        self.steps = []
        self._cols = {}

    # ── schema helpers ──
    def columns(self, node) -> list:
        key = to_ra(node)
        if key not in self._cols:
            sql = c.SQLConverter(node, self.db).convert()
            con = sqlite3.connect(self.db)
            try:
                cur = con.execute(f"SELECT * FROM ({sql}) LIMIT 0")
                self._cols[key] = [d[0].lower() for d in cur.description]
            finally:
                con.close()
        return self._cols[key]

    def quals(self, node) -> set:
        if isinstance(node, c.TableNode):
            return {node.name.lower()}
        if isinstance(node, c.RenameNode):
            return {node.new_name.lower()}
        if isinstance(node, (c.ProjectionNode, c.SelectionNode)):
            return self.quals(node.child)
        if isinstance(node, _JOINS):
            return self.quals(node.left) | self.quals(node.right)
        return set()

    def _covers(self, refs, node) -> bool:
        cols = set(self.columns(node))
        quals = self.quals(node)
        return all(col.lower() in cols and (q is None or q.lower() in quals) for q, col in refs)

    def _log(self, rule: str, detail: str):
        name, law = RULES[rule]
        self.steps.append({"id": rule, "rule": name, "law": law, "detail": detail})

    # ── driver ──
    def optimize(self, tree):
        tree = copy.deepcopy(tree)
        tree = self._opt(tree)
        tree = self._combine(tree)
        return tree

    def _opt(self, node):
        if node is None:
            return None

        if isinstance(node, c.SelectionNode):
            conds = []
            while isinstance(node, c.SelectionNode):
                parts = conjuncts(node.condition)
                if len(parts) > 1:
                    self._log("R1", f"split σ {node.condition} into {len(parts)} separate selections")
                conds = parts + conds
                node = node.child
            base = self._opt(node)
            for cond in reversed(conds):          # innermost first
                base = self._place(cond, base)
            return base

        if isinstance(node, c.ProjectionNode):
            node.child = self._opt(node.child)
            while isinstance(node.child, c.ProjectionNode):
                self._log("R8", f"π {', '.join(node.child.columns)} is redundant under π {', '.join(node.columns)}")
                node.child = node.child.child
            return node

        if hasattr(node, "left"):
            node.left = self._opt(node.left)
            node.right = self._opt(node.right)
        elif getattr(node, "child", None) is not None:
            node.child = self._opt(node.child)
        return node

    def _place(self, cond: str, x):
        """Put σ cond on top of x, pushed down as far as the rules allow."""
        refs = attr_refs(cond)

        if isinstance(x, c.ProjectionNode):
            kept = {_bare(col) for col in x.columns}
            if "*" in kept or all(col.lower() in kept for _, col in refs):
                self._log("R2", f"σ {cond} moved below π {', '.join(x.columns)}")
                x.child = self._place(cond, x.child)
                return x

        elif isinstance(x, c.SelectionNode):
            x.child = self._place(cond, x.child)
            return x

        elif isinstance(x, _JOINS):
            in_left = self._covers(refs, x.left)
            in_right = self._covers(refs, x.right)
            kind = getattr(x, "kind", None)
            left_ok = kind in (None, "left")
            right_ok = kind in (None, "right")
            sym = _join_symbol(x)
            if in_left and left_ok:
                self._log("R3", f"σ {cond} pushed below {sym} into its left input {_short(x.left)}")
                x.left = self._place(cond, x.left)
                return x
            if in_right and right_ok:
                self._log("R3", f"σ {cond} pushed below {sym} into its right input {_short(x.right)}")
                x.right = self._place(cond, x.right)
                return x
            if isinstance(x, c.CrossJoinNode) and self._covers(refs, x):
                self._log("R4", f"σ {cond} over × turned into the join ⋈[{cond}]")
                return c.ThetaJoinNode(x.left, x.right, cond)
            if isinstance(x, c.ThetaJoinNode) and self._covers(refs, x):
                self._log("R5", f"σ {cond} merged into the join condition")
                x.condition = _and(x.condition, cond)
                return x

        elif isinstance(x, (c.UnionNode, c.IntersectNode)):
            lcols, rcols = self.columns(x.left), self.columns(x.right)
            if lcols == rcols and all(q is None and col.lower() in lcols for q, col in refs):
                sym = "∪" if isinstance(x, c.UnionNode) else "∩"
                self._log("R6", f"σ {cond} pushed into both inputs of {sym}")
                x.left = self._place(cond, x.left)
                x.right = self._place(cond, x.right)
                return x

        elif isinstance(x, c.MinusNode):
            if all(q is None and col.lower() in self.columns(x.left) for q, col in refs):
                self._log("R6", f"σ {cond} pushed into the left input of −")
                x.left = self._place(cond, x.left)
                return x

        elif isinstance(x, c.GroupNode):
            groups = {_bare(g) for g in x.group_cols}
            if refs and all(col.lower() in groups for _, col in refs):
                self._log("R7", f"σ {cond} only uses grouping attributes, applied before γ")
                x.child = self._place(cond, x.child)
                return x

        return c.SelectionNode(cond, x)

    def _combine(self, node):
        if node is None:
            return None
        if hasattr(node, "left"):
            node.left = self._combine(node.left)
            node.right = self._combine(node.right)
            return node
        if getattr(node, "child", None) is not None:
            node.child = self._combine(node.child)
        if isinstance(node, c.SelectionNode) and isinstance(node.child, c.SelectionNode):
            inner = node.child
            merged = _and(inner.condition, node.condition)
            self._log("R9", f"σ {node.condition} and σ {inner.condition} combined into one selection")
            return c.SelectionNode(merged, inner.child)
        return node


def _and(a: str, b: str) -> str:
    """a ∧ b, bracketing either side that contains a top-level OR."""
    def wrap(x):
        x = strip_outer_parens(x)
        return f"({x})" if len(split_keyword(normalize(x), "OR")) > 1 else x
    return f"{wrap(a)} ∧ {wrap(b)}"


def _join_symbol(x) -> str:
    if isinstance(x, c.CrossJoinNode):
        return "×"
    if isinstance(x, c.ThetaJoinNode):
        return "⋈θ"
    if isinstance(x, c.OuterJoinNode):
        return x.SYMBOLS[x.kind]
    return "⋈"


def optimize(tree, db_name: str):
    """Returns (optimized_tree, steps)."""
    opt = Optimizer(db_name)
    new_tree = opt.optimize(tree)
    return new_tree, opt.steps
