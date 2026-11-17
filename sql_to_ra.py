"""
SQL → relational algebra translator (the reverse of converter.py).

Supported SQL (SQLite syntax):
    SELECT [DISTINCT] cols | * | AGG(x) [AS a]
    FROM t [AS a] | (subquery) AS a
         [, t2] [CROSS JOIN t2] [[INNER] JOIN t2 ON c] [NATURAL JOIN t2]
         [LEFT | RIGHT | FULL [OUTER] JOIN t2 ON c] [NATURAL LEFT JOIN t2] [JOIN t2 USING (a)]
    [WHERE c] [GROUP BY cols] [HAVING c]
    q1 UNION | INTERSECT | EXCEPT q2

Mapping:
    FROM a, b / CROSS JOIN       a × b
    JOIN ... ON c                a ⋈[c] b
    NATURAL JOIN                 a ⋈ b
    LEFT/RIGHT/FULL JOIN         ⟕ ⟖ ⟗
    t AS x / (subquery) AS x     ρ x (...)
    WHERE c                      σ c
    GROUP BY g + aggregates      γ g; AGG(x)→a
    HAVING c                     σ c on top of γ
    SELECT list                  π list   (ρ for column aliases)
    UNION / INTERSECT / EXCEPT   ∪ ∩ −

The result is built as an expression tree (same node classes as
converter.py) and printed with ra_printer.to_ra, so it can be run,
explained, costed and optimized like any typed expression.
"""

import re

import converter as c
from ra_printer import to_ra

_TOKEN = re.compile(r"""
    (?P<str>'(?:[^']|'')*')
  | (?P<qid>"[^"]*"|`[^`]*`|\[[^\]]*\])
  | (?P<num>\d+(?:\.\d+)?)
  | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><>|!=|>=|<=|==|\|\||[=<>*+\-/%])
  | (?P<punct>[(),.;])
  | (?P<ws>\s+)
  | (?P<bad>.)
""", re.VERBOSE)

CLAUSE_END = {"FROM", "WHERE", "GROUP", "HAVING", "ORDER", "LIMIT", "OFFSET",
              "UNION", "INTERSECT", "EXCEPT"}
JOIN_START = {"JOIN", "INNER", "CROSS", "NATURAL", "LEFT", "RIGHT", "FULL", "ON", "USING"}
SPACE_BEFORE_PAREN = {"IN", "AND", "OR", "NOT", "EXISTS", "ON", "BETWEEN", "LIKE", "IS",
                      "WHERE", "SELECT", "USING", "AS"}
RESERVED = CLAUSE_END | JOIN_START | {"SELECT", "AS", "AND", "OR", "NOT", "DISTINCT", "ALL",
                                      "OUTER", "BY", "IS", "NULL", "LIKE", "IN", "BETWEEN"}


class Tok:
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value
        self.upper = value.upper()

    def __repr__(self):
        return f"{self.kind}:{self.value}"


def tokenize(sql: str):
    toks = []
    for m in _TOKEN.finditer(sql):
        kind = m.lastgroup
        if kind == "ws":
            continue
        if kind == "bad":
            raise ValueError(f"Unexpected character '{m.group()}' in SQL")
        value = m.group()
        if kind == "qid":
            value = '"' + value[1:-1] + '"'
        toks.append(Tok(kind, value))
    toks.append(Tok("eof", ""))
    return toks


def text_of(toks, as_condition: bool = False) -> str:
    """Rebuild readable text from tokens (optionally with ∧ ∨ for AND/OR)."""
    out, prev = "", None
    for t in toks:
        v = t.value
        if as_condition and t.kind == "word" and t.upper in ("AND", "OR"):
            v = "∧" if t.upper == "AND" else "∨"
        no_space = (
            not out
            or v in (",", ")", ".")
            or (prev is not None and prev.value in ("(", "."))
            or (v == "(" and prev is not None and prev.kind == "word"
                and prev.upper not in SPACE_BEFORE_PAREN)
        )
        out += ("" if no_space else " ") + v
        prev = t
    return out


class SQLToRA:
    def __init__(self, sql: str):
        self.toks = tokenize(sql.strip())
        self.pos = 0
        self.warnings = []

    # ── token helpers ──
    def peek(self, k: int = 0) -> Tok:
        return self.toks[min(self.pos + k, len(self.toks) - 1)]

    def at(self, *words) -> bool:
        return self.peek().upper in words

    def take(self) -> Tok:
        t = self.peek()
        self.pos += 1
        return t

    def expect(self, word: str):
        if self.peek().upper != word:
            found = self.peek().value or "end of query"
            raise ValueError(f"Expected {word} but found '{found}'")
        return self.take()

    def _until(self, stops: set) -> list:
        """Tokens up to a stop word / ')' / ',' at depth 0 (stops may include ',')."""
        out, depth = [], 0
        while True:
            t = self.peek()
            if t.kind == "eof" or t.value == ";":
                break
            if depth == 0 and (t.value == ")" or t.upper in stops or t.value in stops):
                break
            if t.value == "(":
                depth += 1
            elif t.value == ")":
                depth -= 1
            out.append(self.take())
        return out

    # ── grammar ──
    def parse(self):
        node = self._compound()
        if self.at("ORDER", "LIMIT", "OFFSET"):
            self.warnings.append("ORDER BY / LIMIT have no relational algebra equivalent and were ignored.")
            while self.peek().kind != "eof" and self.peek().value != ";":
                self.take()
        if self.peek().value == ";":
            self.take()
        if self.peek().kind != "eof":
            raise ValueError(f"Unexpected '{self.peek().value}' after the end of the query")
        return node

    def _compound(self):
        node = self._core()
        while self.at("UNION", "INTERSECT", "EXCEPT"):
            op = self.take().upper
            if self.at("ALL"):
                self.take()
                self.warnings.append(f"{op} ALL keeps duplicates; relational algebra {op} is set-based.")
            right = self._core()
            node = {"UNION": c.UnionNode, "INTERSECT": c.IntersectNode,
                    "EXCEPT": c.MinusNode}[op](node, right)
        return node

    def _core(self):
        if self.peek().value == "(":
            self.take()
            node = self._compound()
            self.expect(")")
            return node

        self.expect("SELECT")
        distinct = False
        if self.at("DISTINCT"):
            self.take()
            distinct = True
        elif self.at("ALL"):
            self.take()

        items = self._select_list()
        self.expect("FROM")
        node = self._from()

        if self.at("WHERE"):
            self.take()
            toks = self._until(CLAUSE_END)
            self._no_subquery(toks, "WHERE")
            node = c.SelectionNode(text_of(toks, True), node)

        group_cols = []
        if self.at("GROUP"):
            self.take()
            self.expect("BY")
            group_cols = [text_of(t) for t in self._split_commas(self._until(CLAUSE_END - {"GROUP"}))]

        having = None
        if self.at("HAVING"):
            self.take()
            toks = self._until(CLAUSE_END)
            self._no_subquery(toks, "HAVING")
            having = toks

        return self._finish(node, items, group_cols, having, distinct)

    def _no_subquery(self, toks, clause):
        for i, t in enumerate(toks[:-1]):
            if t.value == "(" and toks[i + 1].upper == "SELECT":
                raise ValueError(f"Subqueries inside {clause} (IN / EXISTS / scalar) cannot be translated "
                                 f"directly; rewrite them as a join, e.g. ... JOIN (SELECT ...) AS x ON ...")

    @staticmethod
    def _split_commas(toks):
        parts, cur, depth = [], [], 0
        for t in toks:
            if t.value == "(":
                depth += 1
            elif t.value == ")":
                depth -= 1
            if t.value == "," and depth == 0:
                parts.append(cur)
                cur = []
            else:
                cur.append(t)
        if cur:
            parts.append(cur)
        return parts

    def _select_list(self):
        items = []
        for toks in self._split_commas(self._until({"FROM"})):
            alias = None
            if len(toks) >= 3 and toks[-2].upper == "AS":
                alias, toks = toks[-1].value.strip('"'), toks[:-2]
            elif (len(toks) >= 2 and toks[-1].kind in ("word", "qid") and toks[-1].upper not in RESERVED
                  and toks[-2].value != "." and toks[-2].kind in ("word", "qid", "punct")
                  and toks[-2].value != "("):
                alias, toks = toks[-1].value.strip('"'), toks[:-1]
            expr = text_of(toks)
            is_agg = (len(toks) >= 3 and toks[0].upper in c.AGG_FUNCS and toks[1].value == "("
                      and toks[-1].value == ")")
            items.append({"expr": expr, "alias": alias, "agg": is_agg, "toks": toks})
        if not items:
            raise ValueError("SELECT list is empty")
        return items

    def _from(self):
        node = self._from_item()
        while True:
            if self.peek().value == ",":
                self.take()
                node = c.CrossJoinNode(node, self._from_item())
                continue
            if self.at("CROSS"):
                self.take()
                self.expect("JOIN")
                node = c.CrossJoinNode(node, self._from_item())
                continue
            natural = False
            if self.at("NATURAL"):
                self.take()
                natural = True
            kind = None
            if self.at("LEFT", "RIGHT", "FULL"):
                kind = self.take().upper.lower()
                if self.at("OUTER"):
                    self.take()
            elif self.at("INNER"):
                self.take()
            if not self.at("JOIN"):
                if natural or kind:
                    raise ValueError("Expected JOIN")
                return node
            self.take()
            right = self._from_item()

            cond = None
            if self.at("ON"):
                self.take()
                toks = self._until(CLAUSE_END | JOIN_START | {","})
                cond = text_of(toks, True)
            elif self.at("USING"):
                self.take()
                self.expect("(")
                cols = text_of(self._until(set()))
                self.expect(")")
                self.warnings.append(f"JOIN ... USING ({cols}) was written as a natural join; this matches "
                                     f"only when {cols} are the only shared column names.")
                natural = True

            if kind:
                node = c.OuterJoinNode(node, right, kind, None if natural else cond)
            elif natural:
                node = c.NaturalJoinNode(node, right)
            elif cond:
                node = c.ThetaJoinNode(node, right, cond)
            else:
                node = c.CrossJoinNode(node, right)

    def _from_item(self):
        if self.peek().value == "(":
            self.take()
            sub = self._compound()
            self.expect(")")
            alias = self._alias()
            if not alias:
                raise ValueError("A subquery in FROM needs an alias, e.g. (SELECT ...) AS x")
            return c.RenameNode({"name": alias, "columns": []}, sub)
        t = self.take()
        if t.kind not in ("word", "qid") or t.upper in RESERVED:
            raise ValueError(f"Expected a table name but found '{t.value or 'end of query'}'")
        table = c.TableNode(t.value.strip('"'))
        alias = self._alias()
        if alias and alias.lower() != table.name.lower():
            return c.RenameNode({"name": alias, "columns": []}, table)
        return table

    def _alias(self):
        if self.at("AS"):
            self.take()
            return self.take().value.strip('"')
        t = self.peek()
        if t.kind in ("word", "qid") and t.upper not in RESERVED:
            return self.take().value.strip('"')
        return None

    # ── SELECT list → π / γ / ρ ──
    def _finish(self, node, items, group_cols, having, distinct):
        has_agg = any(i["agg"] for i in items)
        star = len(items) == 1 and items[0]["expr"] == "*"

        for i in items:
            if not i["agg"] and not re.fullmatch(r'[A-Za-z_"][\w"]*(\.[A-Za-z_"*][\w"]*)?|\*', i["expr"]):
                raise ValueError(f"SELECT expression '{i['expr']}' is not a plain column; relational algebra "
                                 f"projection only lists attributes (aggregates go through γ).")
            if not i["agg"] and any(t.upper in c.AGG_FUNCS for t in i["toks"]):
                raise ValueError(f"'{i['expr']}' mixes aggregates with other operations; not supported.")

        if has_agg or group_cols:
            aggs, out_names = [], []
            for i in items:
                if i["agg"]:
                    alias = i["alias"] or c.parse_group_spec(i["expr"])[1][0][1]
                    aggs.append((i["expr"], alias))
                    out_names.append(alias)
                else:
                    if i["expr"] == "*":
                        raise ValueError("SELECT * cannot be combined with GROUP BY")
                    out_names.append(i["alias"] or i["expr"].split(".")[-1])
            hidden = []
            if having:
                cond = text_of(having, True)
                for m in re.finditer(r"\b([A-Za-z_]+)\s*\(([^()]*)\)", cond):
                    if m.group(1).upper() not in c.AGG_FUNCS:
                        continue
                    expr = m.group(0)
                    known = next((a for e, a in aggs if _same(e, expr)), None)
                    if not known:
                        known = f"h{len(hidden) + 1}"
                        aggs.append((expr, known))
                        hidden.append(known)
                    cond = cond.replace(expr, known)
            node = c.GroupNode(group_cols, aggs, node)
            if having:
                node = c.SelectionNode(cond, node)
            # γ outputs: grouping columns, then aggregates. Reorder / drop / rename if SELECT differs.
            natural = [g.split(".")[-1] for g in group_cols] + [a for _, a in aggs if a not in hidden]
            cols = [i["expr"].split(".")[-1] if not i["agg"] else name
                    for i, name in zip(items, out_names)]
            renamed = any(i["alias"] and not i["agg"] for i in items)
            if renamed or hidden or [x.lower() for x in cols] != [x.lower() for x in natural]:
                node = c.ProjectionNode(cols, node)
            if renamed:
                node = c.RenameNode({"name": "Q", "columns": out_names}, node)
            return node

        if not star:
            node = c.ProjectionNode([i["expr"] for i in items], node)
            if not distinct:
                self.warnings.append("Relational algebra uses set semantics, so π removes duplicate rows "
                                     "(like SELECT DISTINCT).")
            if any(i["alias"] for i in items):
                names = [i["alias"] or i["expr"].split(".")[-1] for i in items]
                node = c.RenameNode({"name": "Q", "columns": names}, node)
        return node


def _same(a: str, b: str) -> bool:
    return re.sub(r"\s+", "", a).lower() == re.sub(r"\s+", "", b).lower()


def translate(sql: str):
    """Returns (expression_tree, relational_algebra_text, warnings)."""
    if not sql or not sql.strip():
        raise ValueError("SQL query is empty")
    t = SQLToRA(sql)
    tree = t.parse()
    return tree, to_ra(tree), t.warnings
