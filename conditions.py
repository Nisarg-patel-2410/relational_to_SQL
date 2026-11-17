"""
Helpers for working with selection / join conditions as text:
normalising symbols, splitting on AND / OR at the top level, and finding
which attributes a condition refers to. Shared by the optimizer and the
cost estimator.
"""

import re

KEYWORDS = {"AND", "OR", "NOT", "IS", "NULL", "LIKE", "IN", "BETWEEN",
            "TRUE", "FALSE", "DISTINCT", "ESCAPE", "GLOB"}

_SYMBOLS = (("∧", " AND "), ("∨", " OR "), ("¬", " NOT "),
            ("≠", "<>"), ("≥", ">="), ("≤", "<="))


def normalize(cond: str) -> str:
    for a, b in _SYMBOLS:
        cond = cond.replace(a, b)
    return " ".join(cond.split())


def strip_outer_parens(expr: str) -> str:
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        depth, quote = 0, None
        for i, ch in enumerate(expr):
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(expr) - 1:
                    return expr          # first group closes early: not a wrapper
        expr = expr[1:-1].strip()
    return expr


def split_keyword(expr: str, kw: str) -> list:
    """Split expr on keyword kw (AND / OR) outside parentheses and quotes.
    'a BETWEEN 1 AND 5' is not split."""
    parts, depth, quote, start, i = [], 0, None, 0, 0
    upper = expr.upper()
    n, k = len(expr), len(kw)
    while i < n:
        ch = expr[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif (depth == 0 and upper.startswith(kw, i)
              and (i == 0 or not (expr[i - 1].isalnum() or expr[i - 1] == "_"))
              and (i + k >= n or not (expr[i + k].isalnum() or expr[i + k] == "_"))):
            piece = expr[start:i]
            last_between = [m.end() for m in re.finditer(r"\bBETWEEN\b", piece.upper())]
            if kw == "AND" and last_between and \
                    not re.search(r"\bAND\b", piece.upper()[last_between[-1]:]):
                i += k                       # this AND belongs to BETWEEN
                continue
            parts.append(piece.strip())
            start = i + k
            i += k
            continue
        i += 1
    parts.append(expr[start:].strip())
    return [p for p in parts if p]


def conjuncts(cond: str) -> list:
    """'a=1 ∧ (b=2 ∨ c=3)'  ->  ['a=1', '(b=2 OR c=3)']"""
    return split_keyword(strip_outer_parens(normalize(cond)), "AND")


_STRINGS = re.compile(r"'(?:[^']|'')*'|\"[^\"]*\"")
_REF = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\b|\b([A-Za-z_]\w*)\b(\s*\()?")


def attr_refs(cond: str) -> list:
    """Attributes used in a condition, as (qualifier or None, column) pairs.
    Literals, numbers, keywords and function names are ignored."""
    text = _STRINGS.sub(" ", normalize(cond))
    refs = []
    for m in _REF.finditer(text):
        if m.group(1):
            refs.append((m.group(1), m.group(2)))
        elif m.group(3):
            word = m.group(3)
            if m.group(4) or word.upper() in KEYWORDS:
                continue          # function call or keyword
            refs.append((None, word))
    return refs
