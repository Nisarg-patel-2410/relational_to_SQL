"""
Query cost estimator for relational algebra expression trees.

For every node it estimates the number of result tuples using the textbook
statistics model (Silberschatz et al., ch. 16; System R defaults):

    n(R)         number of tuples in R            (read from the database)
    V(A, R)      number of distinct values of A   (read from the database)

    σ A = c (R)        n(R) / V(A, R)
    σ A = B (R)        n(R) / max(V(A, R), V(B, R))
    σ A < c (R)        n(R) / 3                      (range, no histogram)
    σ c1 ∧ c2          n(R) · s1 · s2                (independence)
    σ c1 ∨ c2          n(R) · (1 − (1 − s1)(1 − s2))
    R × S              n(R) · n(S)
    R ⋈ S on A         n(R) · n(S) / max(V(A, R), V(A, S))
    π A (R)            min(n(R), V(A, R))            (duplicates removed)
    γ G (R)            min(n(R), Π V(g, R))
    R ∪ S ≤ n(R)+n(S)  R ∩ S ≤ min    R − S ≤ n(R)   R ÷ S ≈ n(R) / n(S)

Cost of a plan = number of tuples processed:
    table scan             n(R)
    σ, π, ρ                0   (pipelined: applied to tuples as they stream past)
    ⋈, ×, ∪, ∩, −, ÷, γ    tuples read from the inputs + tuples produced
so plans that shrink relations before joining them are cheaper.
"""

import math
import re
import sqlite3

import converter as c
from conditions import normalize, strip_outer_parens, split_keyword

DEFAULT_DISTINCT = 10       # V(A) when an attribute cannot be resolved
RANGE_SELECTIVITY = 1 / 3


class Stats:
    def __init__(self, rows: float, cols: list, distinct: dict):
        self.rows = max(rows, 0.0)
        self.cols = cols                    # output column names, in order
        self.distinct = {k: min(v, max(self.rows, 1)) for k, v in distinct.items()}

    def V(self, col: str) -> float:
        name = col.split(".")[-1].strip().strip('"').lower()
        return max(self.distinct.get(name, DEFAULT_DISTINCT), 1)

    def has(self, col: str) -> bool:
        return col.split(".")[-1].strip().strip('"').lower() in self.distinct


def _bare(col: str) -> str:
    return col.split(".")[-1].strip().strip('"')


def _fmt(x: float) -> str:
    if x >= 100 or x == int(x):
        return f"{x:,.0f}"
    return f"{x:.2f}".rstrip("0").rstrip(".")


_LITERAL = re.compile(r"^('.*'|\".*\"|-?\d+(\.\d+)?)$")
_ATTR = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)?$")


class CostEstimator:
    def __init__(self, db_name: str):
        self.db = db_name
        self._tables = {}
        self.info = {}          # id(node) -> {"rows", "cost", "formula"}

    # ── base statistics ──
    def _table(self, name: str) -> Stats:
        key = name.lower()
        if key not in self._tables:
            con = sqlite3.connect(self.db)
            try:
                cols = [r[1] for r in con.execute(f'PRAGMA table_info("{name}")')]
                if not cols:
                    raise ValueError(f"Unknown table '{name}'")
                n = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                distinct = {}
                for col in cols:
                    distinct[col.lower()] = con.execute(
                        f'SELECT COUNT(DISTINCT "{col}") FROM "{name}"').fetchone()[0]
            finally:
                con.close()
            self._tables[key] = Stats(n, cols, distinct)
        t = self._tables[key]
        return Stats(t.rows, list(t.cols), dict(t.distinct))

    # ── selectivity ──
    def selectivity(self, cond: str, st: Stats):
        """Return (selectivity, columns fixed to a single value)."""
        e = strip_outer_parens(normalize(cond))
        ors = split_keyword(e, "OR")
        if len(ors) > 1:
            keep = 1.0
            for p in ors:
                keep *= 1 - self.selectivity(p, st)[0]
            return 1 - keep, set()
        ands = split_keyword(e, "AND")
        if len(ands) > 1:
            s, fixed = 1.0, set()
            for p in ands:
                ps, pf = self.selectivity(p, st)
                s *= ps
                fixed |= pf
            return s, fixed
        if e.upper().startswith("NOT "):
            return 1 - self.selectivity(e[4:], st)[0], set()
        return self._atom(e, st)

    def _atom(self, e: str, st: Stats):
        u = e.upper()
        if re.search(r"\bIS\s+NOT\s+NULL\b", u):
            return 0.9, set()
        if re.search(r"\bIS\s+NULL\b", u):
            return 0.1, set()
        if re.search(r"\bNOT\s+LIKE\b", u):
            return 0.9, set()
        if re.search(r"\bLIKE\b", u):
            return 0.1, set()
        if re.search(r"\bBETWEEN\b", u):
            return 0.25, set()
        m = re.match(r"^(.+?)\s+(NOT\s+)?IN\s*\((.*)\)$", e, re.IGNORECASE)
        if m:
            k = len([x for x in m.group(3).split(",") if x.strip()])
            s = min(1.0, k / st.V(m.group(1)))
            return (1 - s if m.group(2) else s), set()
        m = re.match(r"^(.+?)\s*(<>|!=|>=|<=|==|=|<|>)\s*(.+)$", e)
        if not m:
            return 0.5, set()
        lhs, op, rhs = m.group(1).strip(), m.group(2), m.group(3).strip()
        lcol = bool(_ATTR.match(lhs)) and not _LITERAL.match(lhs)
        rcol = bool(_ATTR.match(rhs)) and not _LITERAL.match(rhs)
        if op in ("=", "=="):
            if lcol and rcol:
                return 1 / max(st.V(lhs), st.V(rhs)), set()
            col = lhs if lcol else rhs if rcol else None
            if col is None:
                return 0.5, set()
            return 1 / st.V(col), {_bare(col).lower()}
        if op in ("<>", "!="):
            col = lhs if lcol else rhs
            return 1 - 1 / st.V(col), set()
        return RANGE_SELECTIVITY, set()

    # ── tree walk ──
    def estimate(self, node) -> Stats:
        st, formula = self._estimate(node)
        kids = _children(node)
        child_cost = sum(self.info[id(ch)]["cost"] for ch in kids)
        if isinstance(node, c.TableNode):
            own = st.rows                                  # full scan
        elif isinstance(node, (c.SelectionNode, c.ProjectionNode, c.RenameNode)):
            own = 0.0                                      # pipelined, nothing stored
        else:                                              # reads inputs, builds output
            own = sum(self.info[id(ch)]["rows"] for ch in kids) + st.rows
        self.info[id(node)] = {
            "rows": st.rows,
            "own": own,
            "cost": own + child_cost,
            "formula": formula,
        }
        return st

    def _estimate(self, node):
        if isinstance(node, c.TableNode):
            st = self._table(node.name)
            return st, f"n({node.name}) = {_fmt(st.rows)}"

        if isinstance(node, c.SelectionNode):
            ch = self.estimate(node.child)
            s, fixed = self.selectivity(node.condition, ch)
            rows = ch.rows * s
            distinct = {k: (1 if k in fixed else min(v, rows)) for k, v in ch.distinct.items()}
            return Stats(rows, ch.cols, distinct), f"{_fmt(ch.rows)} × sel {_fmt(s)} = {_fmt(rows)}"

        if isinstance(node, c.ProjectionNode):
            ch = self.estimate(node.child)
            if node.columns == ["*"]:
                return ch, f"= {_fmt(ch.rows)}"
            cols = [_bare(x) for x in node.columns]
            prod = math.prod(ch.V(x) for x in cols)
            rows = min(ch.rows, prod)
            distinct = {x.lower(): ch.V(x) for x in cols}
            vs = " · ".join(f"V({x})" for x in cols)
            return Stats(rows, cols, distinct), f"min({_fmt(ch.rows)}, {vs}={_fmt(prod)}) = {_fmt(rows)}"

        if isinstance(node, c.RenameNode):
            ch = self.estimate(node.child)
            if not node.columns:
                return ch, "same as input"
            distinct = {new.lower(): ch.V(old) for old, new in zip(ch.cols, node.columns)}
            return Stats(ch.rows, list(node.columns), distinct), "same as input"

        if isinstance(node, c.GroupNode):
            ch = self.estimate(node.child)
            cols = [_bare(g) for g in node.group_cols] + [a for _, a in node.aggregates]
            if not node.group_cols:
                rows, f = 1.0, "one row (no grouping)"
            else:
                prod = math.prod(ch.V(g) for g in node.group_cols)
                rows = min(ch.rows, prod)
                f = f"min({_fmt(ch.rows)}, groups {_fmt(prod)}) = {_fmt(rows)}"
            distinct = {_bare(g).lower(): ch.V(g) for g in node.group_cols}
            distinct.update({a.lower(): rows for _, a in node.aggregates})
            return Stats(rows, cols, distinct), f

        L = self.estimate(node.left)
        R = self.estimate(node.right)
        merged = dict(R.distinct)
        for k, v in L.distinct.items():
            merged[k] = min(v, merged[k]) if k in merged else v

        if isinstance(node, c.CrossJoinNode):
            rows = L.rows * R.rows
            return Stats(rows, L.cols + R.cols, merged), f"{_fmt(L.rows)} × {_fmt(R.rows)} = {_fmt(rows)}"

        if isinstance(node, (c.NaturalJoinNode, c.OuterJoinNode, c.ThetaJoinNode)):
            if isinstance(node, c.ThetaJoinNode) or getattr(node, "condition", None):
                both = Stats(L.rows * R.rows, L.cols + R.cols,
                             {k: max(L.distinct.get(k, 0), R.distinct.get(k, 0))
                              for k in {**L.distinct, **R.distinct}})
                s, _ = self.selectivity(node.condition, both)
                rows = L.rows * R.rows * s
                f = f"{_fmt(L.rows)} × {_fmt(R.rows)} × sel {_fmt(s)} = {_fmt(rows)}"
                cols = L.cols + R.cols
            else:
                common = [x for x in L.cols if x.lower() in {y.lower() for y in R.cols}]
                denom = math.prod(max(L.V(a), R.V(a)) for a in common) if common else 1
                rows = L.rows * R.rows / denom
                on = ", ".join(common) if common else "nothing (acts as ×)"
                f = f"{_fmt(L.rows)} × {_fmt(R.rows)} / {_fmt(denom)} (on {on}) = {_fmt(rows)}"
                cols = L.cols + [y for y in R.cols if y.lower() not in {x.lower() for x in L.cols}]
            if isinstance(node, c.OuterJoinNode):
                keep = {"left": L.rows, "right": R.rows, "full": L.rows + R.rows}[node.kind]
                rows = max(rows, keep)
                f += f", ≥ {_fmt(keep)} kept rows"
            return Stats(rows, cols, merged), f

        if isinstance(node, c.UnionNode):
            rows = L.rows + R.rows
            return Stats(rows, L.cols, merged), f"≤ {_fmt(L.rows)} + {_fmt(R.rows)} = {_fmt(rows)}"
        if isinstance(node, c.IntersectNode):
            rows = min(L.rows, R.rows)
            return Stats(rows, L.cols, merged), f"≤ min({_fmt(L.rows)}, {_fmt(R.rows)}) = {_fmt(rows)}"
        if isinstance(node, c.MinusNode):
            return Stats(L.rows, L.cols, L.distinct), f"≤ {_fmt(L.rows)}"
        if isinstance(node, c.DivisionNode):
            right = {y.lower() for y in R.cols}
            keep = [x for x in L.cols if x.lower() not in right]
            cap = math.prod(L.V(x) for x in keep) if keep else 1
            rows = max(1.0, min(cap, L.rows / max(R.rows, 1)))
            distinct = {x.lower(): L.V(x) for x in keep}
            return Stats(rows, keep, distinct), f"≈ {_fmt(L.rows)} / {_fmt(R.rows)} = {_fmt(rows)}"

        raise ValueError(f"Cost: unsupported node {type(node).__name__}")


def _children(node):
    if hasattr(node, "left"):
        return [node.left, node.right]
    if getattr(node, "child", None) is not None:
        return [node.child]
    return []


def estimate(tree, db_name: str):
    """Returns (info, total_cost) where info maps id(node) to
    {"rows": estimated tuples, "cost": cumulative cost, "formula": text}."""
    est = CostEstimator(db_name)
    est.estimate(tree)
    return est.info, est.info[id(tree)]["cost"]
