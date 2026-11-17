# Object-oriented version with tokenizer, expression tree, and SQL converter
# by: Nisarg Kanasagra, abdulla bohra, santhosh koshik lukka, and nikhil lodhi
# Improved OOP functionality for better maintainability and extensibility

from enum import Enum
from typing import List, Optional


class TokenType(Enum):
    """Token types for relational algebra query"""
    PROJECT    = "π"
    SELECT     = "σ"
    CROSSJOIN  = "×"
    NATURALJOIN = "⋈"
    LEFTJOIN   = "⟕"
    RIGHTJOIN  = "⟖"
    FULLJOIN   = "⟗"
    UNION      = "∪"
    INTERSECT  = "∩"
    MINUS      = "−"
    DIVISION   = "÷"
    RENAME     = "ρ"
    GROUP      = "γ"
    LPAREN     = "("
    RPAREN     = ")"
    IDENTIFIER = "IDENTIFIER"
    CONDITION  = "CONDITION"
    EOF        = "EOF"


class Token:
    """Represents a single token in the query"""
    def __init__(self, type_: TokenType, value: str):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r})"


class Tokenizer:
    """Tokenizes relational algebra queries into tokens"""
    OPERATORS = {
        "π": TokenType.PROJECT,
        "σ": TokenType.SELECT,
        "×": TokenType.CROSSJOIN,
        "⋈": TokenType.NATURALJOIN,
        "⨝": TokenType.NATURALJOIN,
        "⟕": TokenType.LEFTJOIN,
        "⟖": TokenType.RIGHTJOIN,
        "⟗": TokenType.FULLJOIN,
        "∪": TokenType.UNION,
        "∩": TokenType.INTERSECT,
        "−": TokenType.MINUS,
        "-": TokenType.MINUS,  # support regular hyphen for minus
        "÷": TokenType.DIVISION,
        "/": TokenType.DIVISION,
        "ρ": TokenType.RENAME,
        "γ": TokenType.GROUP,
    }

    JOIN_OPS = {TokenType.NATURALJOIN, TokenType.LEFTJOIN,
                TokenType.RIGHTJOIN, TokenType.FULLJOIN}
    # Characters that end a selection condition (hyphen and slash are allowed inside)
    CONDITION_STOP = "πσ×⋈⨝∪∩÷ργ⟕⟖⟗"
    # text before '(' that means the parentheses belong to the condition
    _CALL_BEFORE = __import__("re").compile(
        r"(\bIN|\b(?:LOWER|UPPER|LENGTH|ABS|ROUND|SUBSTR|SUBSTRING|COALESCE|IFNULL|NULLIF|TRIM|"
        r"LTRIM|RTRIM|REPLACE|INSTR|DATE|TIME|DATETIME|STRFTIME|JULIANDAY|CAST|TYPEOF))\s*$",
        __import__("re").IGNORECASE)

    def __init__(self, query: str):
        self.query = query.strip()
        self.pos = 0
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        """Break the query string into tokens"""
        while self.pos < len(self.query):
            char = self.query[self.pos]

            if char == "(":
                self.tokens.append(Token(TokenType.LPAREN, "("))
                self.pos += 1
            elif char == ")":
                self.tokens.append(Token(TokenType.RPAREN, ")"))
                self.pos += 1
            elif char in self.OPERATORS:
                ttype = self.OPERATORS[char]
                self.tokens.append(Token(ttype, char))
                self.pos += 1
                # σ and joins may carry a condition: σ cond (R), R ⋈[cond] S
                if ttype == TokenType.SELECT:
                    cond = self._scan_condition()
                elif ttype in self.JOIN_OPS:
                    cond = self._scan_bracket()
                else:
                    cond = None
                if cond is not None:
                    self.tokens.append(Token(TokenType.CONDITION, cond))
                if ttype == TokenType.GROUP:
                    spec = self._scan_group_spec()
                    if spec:
                        self.tokens.append(Token(TokenType.IDENTIFIER, spec))
            elif char.isspace():
                self.pos += 1
            else:
                token_value = self._read_token()
                if self._looks_like_condition(token_value):
                    self.tokens.append(Token(TokenType.CONDITION, token_value))
                else:
                    self.tokens.append(Token(TokenType.IDENTIFIER, token_value))

        self.tokens.append(Token(TokenType.EOF, ""))
        return self.tokens

    def _read_token(self) -> str:
        """Read a complete token (identifier or condition)"""
        start = self.pos
        while self.pos < len(self.query) and self.query[self.pos] not in "()πσ×⋈⨝⟕⟖⟗∪∩−-÷/ργ":
            self.pos += 1
        return self.query[start:self.pos].strip()

    def _looks_like_condition(self, value: str) -> bool:
        """Return True if value looks like a filter condition (comparison ops or AND/OR)."""
        upper = value.upper()
        return (
            any(op in value for op in "<>=!≠≥≤") or
            " AND " in upper or " OR " in upper or
            any(f" {kw} " in f" {upper} " for kw in ("IS", "LIKE", "IN", "BETWEEN")) or
            "∧" in value or "∨" in value   # ∧ = AND, ∨ = OR
        )


    # ── condition scanning ──
    def _skip_spaces(self):
        while self.pos < len(self.query) and self.query[self.pos].isspace():
            self.pos += 1

    def _match(self, i: int, open_ch: str, close_ch: str) -> int:
        """Index of the bracket closing the one at i (quotes are skipped)."""
        depth, quote = 0, None
        for j in range(i, len(self.query)):
            ch = self.query[j]
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
            elif ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return j
        raise ValueError(f"Unbalanced '{open_ch}' at position {i + 1}")

    def _scan_bracket(self) -> Optional[str]:
        """Read an explicit condition: [cond], {cond}, _{cond} or _[cond]."""
        start = self.pos
        self._skip_spaces()
        if self.pos < len(self.query) and self.query[self.pos] == "_":
            self.pos += 1
        if self.pos < len(self.query) and self.query[self.pos] in "[{":
            open_ch = self.query[self.pos]
            close_ch = "]" if open_ch == "[" else "}"
            end = self._match(self.pos, open_ch, close_ch)
            text = self.query[self.pos + 1:end].strip()
            self.pos = end + 1
            return text
        self.pos = start
        return None

    def _scan_group_spec(self) -> Optional[str]:
        """Read the γ specification, e.g.  dept_id; COUNT(*)→n, AVG(cgpa)→avg
        Parentheses directly after an aggregate name belong to the spec."""
        bracket = self._scan_bracket()
        if bracket is not None:
            return bracket
        import re
        self._skip_spaces()
        start = i = self.pos
        quote = None
        while i < len(self.query):
            ch = self.query[i]
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
            elif ch == "(":
                m = re.search(r"([A-Za-z_]+)\s*$", self.query[start:i])
                if m and m.group(1).upper() in AGG_FUNCS:
                    i = self._match(i, "(", ")") + 1
                    continue
                break
            elif ch == ")" or ch in self.CONDITION_STOP:
                break
            i += 1
        self.pos = i
        return self.query[start:i].strip() or None

    def _is_condition_group(self, text: str) -> bool:
        return (not any(ch in text for ch in self.CONDITION_STOP)
                and self._looks_like_condition(text))

    def _scan_condition(self) -> Optional[str]:
        """Read a selection condition after σ. Parenthesised groups that are
        themselves conditions, e.g. σ (a>1 ∨ b=2) ∧ c=3 (R), stay part of it."""
        bracket = self._scan_bracket()
        if bracket is not None:
            return bracket
        self._skip_spaces()
        start = i = self.pos
        quote = None
        while i < len(self.query):
            ch = self.query[i]
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "'\"":
                quote = ch
            elif ch == "(":
                end = self._match(i, "(", ")")
                # keep: (a=1 ∨ b=2) groups, IN (1, 2) lists and function calls like LOWER(name)
                if (self._is_condition_group(self.query[i + 1:end])
                        or self._CALL_BEFORE.search(self.query[start:i])):
                    i = end + 1
                    continue
                break
            elif ch == ")" or ch in self.CONDITION_STOP:
                break
            i += 1
        text = self.query[start:i].strip()
        if not self._looks_like_condition(text):
            return None          # let normal tokenizing handle it
        self.pos = i
        return text


# ── AST Nodes ────────────────────────────────────────────────────────────────

class ExpressionNode:
    """Base class for expression tree nodes"""
    def __repr__(self):
        return self.display()

    def display(self, indent: int = 0) -> str:
        raise NotImplementedError("Subclasses must implement display()")


class TableNode(ExpressionNode):
    def __init__(self, name: str):
        self.name = name

    def display(self, indent: int = 0) -> str:
        return f"{'  ' * indent}└─ Table: {self.name}"


class ProjectionNode(ExpressionNode):
    def __init__(self, columns: List[str], child: Optional[ExpressionNode] = None):
        self.columns = columns
        self.child = child

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ π (Project): {', '.join(self.columns)}\n"
        if self.child:
            result += self.child.display(indent + 1)
        return result


class SelectionNode(ExpressionNode):
    def __init__(self, condition: str, child: Optional[ExpressionNode] = None):
        self.condition = condition
        self.child = child

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ σ (Select): {self.condition}\n"
        if self.child:
            result += self.child.display(indent + 1)
        return result


class CrossJoinNode(ExpressionNode):
    def __init__(self, left: ExpressionNode, right: ExpressionNode):
        self.left = left
        self.right = right

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ × (Cross Join)\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


class NaturalJoinNode(ExpressionNode):
    def __init__(self, left: ExpressionNode, right: ExpressionNode):
        self.left = left
        self.right = right

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ ⋈ (Natural Join)\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


class DivisionNode(ExpressionNode):
    def __init__(self, left: ExpressionNode, right: ExpressionNode):
        self.left = left
        self.right = right

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ ÷ (Division)\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


class UnionNode(ExpressionNode):
    def __init__(self, left: ExpressionNode, right: ExpressionNode):
        self.left = left
        self.right = right

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ ∪ (Union)\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result

class IntersectNode(ExpressionNode):
    def __init__(self, left: ExpressionNode, right: ExpressionNode):
        self.left = left
        self.right = right

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ ∩ (Intersect)\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


class MinusNode(ExpressionNode):
    def __init__(self, left: ExpressionNode, right: ExpressionNode):
        self.left = left
        self.right = right

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ − (Minus/Except)\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


class RenameNode(ExpressionNode):
    def __init__(self, rename_data: dict, child: Optional[ExpressionNode] = None):
        self.new_name = rename_data.get("name") or "alias"
        self.columns = rename_data.get("columns", [])
        self.child = child

    def display(self, indent: int = 0) -> str:
        cols = f"({', '.join(self.columns)})" if self.columns else ""
        result = f"{'  ' * indent}├─ ρ (Rename): {self.new_name}{cols}\n"
        if self.child:
            result += self.child.display(indent + 1)
        return result


class ThetaJoinNode(ExpressionNode):
    """R ⋈[condition] S  →  R JOIN S ON condition"""
    def __init__(self, left: ExpressionNode, right: ExpressionNode, condition: str):
        self.left = left
        self.right = right
        self.condition = condition

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ ⋈ (Theta Join): {self.condition}\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


class OuterJoinNode(ExpressionNode):
    """R ⟕ S, R ⟖ S, R ⟗ S (natural), or with [condition]."""
    SYMBOLS = {"left": "⟕", "right": "⟖", "full": "⟗"}

    def __init__(self, left: ExpressionNode, right: ExpressionNode, kind: str,
                 condition: Optional[str] = None):
        self.left = left
        self.right = right
        self.kind = kind            # 'left' | 'right' | 'full'
        self.condition = condition

    def display(self, indent: int = 0) -> str:
        cond = f": {self.condition}" if self.condition else ""
        result = (f"{'  ' * indent}├─ {self.SYMBOLS[self.kind]} "
                  f"({self.kind.title()} Outer Join){cond}\n")
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


_NAME = __import__("re").compile(r'[A-Za-z_][A-Za-z0-9_$]*|"[^"]+"')
_COLUMN = __import__("re").compile(
    r'(?:(?:[A-Za-z_][A-Za-z0-9_$]*|"[^"]+")\.)?(?:[A-Za-z_][A-Za-z0-9_$]*|"[^"]+"|\*)')

AGG_FUNCS = {"COUNT", "SUM", "AVG", "MIN", "MAX", "TOTAL", "GROUP_CONCAT"}


def split_top(text: str, sep: str = ",") -> List[str]:
    """Split on sep outside parentheses and quotes."""
    parts, depth, quote, cur = [], 0, None, ""
    for ch in text:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == sep and depth == 0:
            parts.append(cur.strip())
            cur = ""
            continue
        cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def parse_group_spec(spec: str):
    """'dept_id; COUNT(*)→n, AVG(cgpa)'  ->  (['dept_id'], [('COUNT(*)','n'), ('AVG(cgpa)','avg_cgpa')])
    Without ';', items containing '(' are aggregates and the rest are grouping columns."""
    import re
    group, aggs = [], []
    if ";" in spec:
        g, a = spec.split(";", 1)
        group = split_top(g)
        agg_items = split_top(a)
    else:
        agg_items = []
        for item in split_top(spec):
            (agg_items if "(" in item else group).append(item)
    for item in agg_items:
        m = re.match(r"^(.*?)\s*(?:→|->|\bAS\b)\s*([A-Za-z_]\w*)$", item, re.IGNORECASE)
        expr, alias = (m.group(1).strip(), m.group(2)) if m else (item.strip(), None)
        fm = re.match(r"^([A-Za-z_]+)\s*\((.*)\)$", expr)
        if not fm or fm.group(1).upper() not in AGG_FUNCS:
            raise ValueError(f"γ: '{expr}' is not an aggregate (use COUNT, SUM, AVG, MIN or MAX)")
        if not alias:
            arg = re.sub(r"\W+", "_", fm.group(2).replace("*", "all")).strip("_").lower()
            alias = f"{fm.group(1).lower()}_{arg or 'all'}"
        aggs.append((expr, alias))
    return [g for g in group if g], aggs


class GroupNode(ExpressionNode):
    """γ group_cols; AGG(x)→alias, ... (R)   →   SELECT ... GROUP BY ..."""
    def __init__(self, group_cols: List[str], aggregates: List[tuple],
                 child: Optional[ExpressionNode] = None):
        self.group_cols = group_cols
        self.aggregates = aggregates
        self.child = child

    def spec(self) -> str:
        aggs = ", ".join(f"{e}→{a}" for e, a in self.aggregates)
        return f"{', '.join(self.group_cols)}; {aggs}" if self.group_cols else aggs

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ γ (Group): {self.spec()}\n"
        if self.child:
            result += self.child.display(indent + 1)
        return result


# ── Parser ───────────────────────────────────────────────────────────────────

class ExpressionTreeBuilder:
    """Builds an expression tree from tokens"""
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def build(self) -> ExpressionNode:
        node = self._parse_set_op()
        tok = self._current_token()
        if tok.type != TokenType.EOF:
            raise ValueError(f"Unexpected '{tok.value}' in query")
        return node

    def _parse_set_op(self) -> ExpressionNode:
        """Parse union/intersect/minus operations (lowest precedence)"""
        left = self._parse_join()

        while self._current_token().type in (TokenType.UNION, TokenType.INTERSECT, TokenType.MINUS):
            tok = self._current_token()
            self.pos += 1
            right = self._parse_join()
            if tok.type == TokenType.UNION:
                left = UnionNode(left, right)
            elif tok.type == TokenType.INTERSECT:
                left = IntersectNode(left, right)
            elif tok.type == TokenType.MINUS:
                left = MinusNode(left, right)

        return left

    def _parse_join(self) -> ExpressionNode:
        """Parse cross/natural join/division operations"""
        left = self._parse_unary()

        outer = {TokenType.LEFTJOIN: "left", TokenType.RIGHTJOIN: "right",
                 TokenType.FULLJOIN: "full"}
        while self._current_token().type in (TokenType.CROSSJOIN, TokenType.NATURALJOIN,
                                             TokenType.DIVISION, *outer):
            tok = self._current_token()
            self.pos += 1
            cond = None
            if self._current_token().type == TokenType.CONDITION:
                cond = self._current_token().value
                self.pos += 1
            right = self._parse_unary()
            if tok.type == TokenType.CROSSJOIN:
                left = CrossJoinNode(left, right)
            elif tok.type == TokenType.NATURALJOIN:
                left = ThetaJoinNode(left, right, cond) if cond else NaturalJoinNode(left, right)
            elif tok.type in outer:
                left = OuterJoinNode(left, right, outer[tok.type], cond)
            elif tok.type == TokenType.DIVISION:
                left = DivisionNode(left, right)

        return left

    def _parse_unary(self) -> ExpressionNode:
        """Parse unary operations (higher precedence than joins)"""
        operations = []

        while self._current_token().type in (TokenType.PROJECT, TokenType.SELECT,
                                             TokenType.RENAME, TokenType.GROUP):
            token = self._current_token()
            self.pos += 1
            if token.type == TokenType.PROJECT:
                operations.append(('project', self._read_columns()))
            elif token.type == TokenType.SELECT:
                operations.append(('select', self._read_condition()))
            elif token.type == TokenType.RENAME:
                operations.append(('rename', self._read_rename()))
            elif token.type == TokenType.GROUP:
                if self._current_token().type != TokenType.IDENTIFIER:
                    raise ValueError("γ needs grouping columns and/or aggregates, e.g. γ dept_id; COUNT(*)→n (students)")
                operations.append(('group', parse_group_spec(self._current_token().value)))
                self.pos += 1

        node = self._parse_primary()

        # Apply unary operators from inside out
        for op_type, op_value in reversed(operations):
            if op_type == 'project':
                node = ProjectionNode(op_value, node)
            elif op_type == 'select':
                node = SelectionNode(op_value, node)
            elif op_type == 'rename':
                node = RenameNode(op_value, node)
            elif op_type == 'group':
                node = GroupNode(op_value[0], op_value[1], node)

        return node

    def _parse_primary(self) -> Optional[ExpressionNode]:
        token = self._current_token()

        if token.type == TokenType.LPAREN:
            self.pos += 1
            node = self._parse_set_op()
            if self._current_token().type != TokenType.RPAREN:
                raise ValueError("Missing ')' in query")
            self.pos += 1
            return node

        elif token.type == TokenType.IDENTIFIER:
            if not _NAME.fullmatch(token.value):
                raise ValueError(f"'{token.value}' is not a valid table name")
            node = TableNode(token.value)
            self.pos += 1
            return node

        if token.type == TokenType.EOF:
            raise ValueError("Query ended early: expected a table name or '('")
        raise ValueError(f"Expected a table name or '(' but found '{token.value}'")

    def _current_token(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "")

    def _read_columns(self) -> List[str]:
        tok = self._current_token()
        if tok.type != TokenType.IDENTIFIER:
            raise ValueError("π needs a list of columns, e.g. π name, email (professor)")
        self.pos += 1
        cols = [col.strip() for col in tok.value.split(",")]
        for col in cols:
            if not _COLUMN.fullmatch(col):
                raise ValueError(f"'{col}' is not a valid column name in π {tok.value}")
        return cols

    def _read_condition(self) -> str:
        if self._current_token().type == TokenType.CONDITION:
            condition = self._current_token().value
            self.pos += 1
            return condition
        raise ValueError("σ needs a condition, e.g. σ age > 20 (students)")

    def _read_rename(self) -> dict:
        """
        Parses rename notation after ρ:
          ρ NewName (table)           -> rename table only
          ρ NewName(c1,c2,...) (table) -> rename table + columns
          ρ (c1,c2,...) (table)        -> rename columns only, keep table alias as 'alias'
        """
        result = {"name": "alias", "columns": []}

        if self._current_token().type == TokenType.IDENTIFIER:
            # Consume the new table/alias name
            result["name"] = self._current_token().value
            self.pos += 1

            # Now self.pos points at the next token.
            # If it's a LPAREN, peek inside to see if it's columns list:
            # pos   -> LPAREN
            # pos+1 -> IDENTIFIER (comma-separated column names)
            # pos+2 -> RPAREN
            # pos+3 -> the actual subquery's LPAREN (must exist)
            if (self._current_token().type == TokenType.LPAREN and
                    self.pos + 2 < len(self.tokens) and
                    self.tokens[self.pos + 1].type == TokenType.IDENTIFIER and
                    self.tokens[self.pos + 2].type == TokenType.RPAREN and
                    self.pos + 3 < len(self.tokens) and
                    self.tokens[self.pos + 3].type == TokenType.LPAREN):
                self.pos += 1                          # consume LPAREN
                cols_str = self._current_token().value # IDENTIFIER = "c1,c2,..."
                self.pos += 1                          # consume IDENTIFIER
                self.pos += 1                          # consume RPAREN
                result["columns"] = [c.strip() for c in cols_str.split(",")]

        elif self._current_token().type == TokenType.LPAREN:
            # No alias name — pattern is ρ (c1,c2,...) (table)
            # pos   -> LPAREN
            # pos+1 -> IDENTIFIER
            # pos+2 -> RPAREN
            # pos+3 -> the actual subquery's LPAREN
            if (self.pos + 2 < len(self.tokens) and
                    self.tokens[self.pos + 1].type == TokenType.IDENTIFIER and
                    self.tokens[self.pos + 2].type == TokenType.RPAREN and
                    self.pos + 3 < len(self.tokens) and
                    self.tokens[self.pos + 3].type == TokenType.LPAREN):
                self.pos += 1                          # consume LPAREN
                cols_str = self._current_token().value
                self.pos += 1                          # consume IDENTIFIER
                self.pos += 1                          # consume RPAREN
                result["columns"] = [c.strip() for c in cols_str.split(",")]

        return result


# ── SQL Converter ─────────────────────────────────────────────────────────────

class SQLConverter:
    """Converts an expression tree to SQL.

    Every node is translated on its own and nested as a subquery where needed,
    so projections/selections inside joins, chains of joins, and set operations
    on derived relations all keep their meaning. Simple queries still flatten
    to a single SELECT ... FROM ... WHERE.
    """
    JOINS = (CrossJoinNode, NaturalJoinNode, ThetaJoinNode, OuterJoinNode)
    SET_OPS = (UnionNode, IntersectNode, MinusNode)

    def __init__(self, tree: Optional[ExpressionNode], db_name: str = "database.db"):
        self.tree = tree
        self.db_name = db_name
        self._n = 0

    def convert(self) -> str:
        if not self.tree:
            return ""
        return self._query(self.tree)

    # ── helpers ──
    @staticmethod
    def _cond(cond: str) -> str:
        for a, b in (("∧", " AND "), ("∨", " OR "), ("¬", " NOT "),
                     ("≠", "<>"), ("≥", ">="), ("≤", "<=")):
            cond = cond.replace(a, b)
        return " ".join(cond.split())

    def _where(self, conds: List[str]) -> str:
        conds = [self._cond(c) for c in conds if c and c.strip()]
        if not conds:
            return ""
        if len(conds) == 1:
            return f" WHERE {conds[0]}"
        return " WHERE " + " AND ".join(f"({c})" for c in conds)

    def _fresh(self) -> str:
        self._n += 1
        return f"t{self._n}"

    @staticmethod
    def _base_name(node) -> Optional[str]:
        """Name to alias a derived relation by, so qualified columns like
        Owners.OID keep working after π/σ on Owners."""
        while isinstance(node, (ProjectionNode, SelectionNode)):
            node = node.child
        if isinstance(node, TableNode):
            return node.name
        if isinstance(node, RenameNode):
            return node.new_name
        return None

    # ── full queries ──
    def _query(self, node) -> str:
        if node is None:
            raise ValueError("Missing relation: expected a table name or a parenthesised expression")

        if isinstance(node, self.SET_OPS):
            kw = {UnionNode: "UNION", IntersectNode: "INTERSECT", MinusNode: "EXCEPT"}[type(node)]
            left = self._query(node.left)
            right = self._query(node.right)
            if isinstance(node.right, self.SET_OPS):
                right = f"SELECT * FROM ({right})"
            return f"{left} {kw} {right}"

        if isinstance(node, DivisionNode):
            return self._division(node)

        if isinstance(node, ProjectionNode):
            src, conds = self._source(node.child, set())
            cols = ", ".join(node.columns) if node.columns else "*"
            return f"SELECT DISTINCT {cols} FROM {src}{self._where(conds)}"

        if isinstance(node, GroupNode):
            src, conds = self._source(node.child, set())
            gcols = ", ".join(node.group_cols)
            if not node.aggregates:
                return f"SELECT DISTINCT {gcols} FROM {src}{self._where(conds)}"
            items = node.group_cols + [f"{e} AS {a}" for e, a in node.aggregates]
            sql = f"SELECT {', '.join(items)} FROM {src}{self._where(conds)}"
            return sql + (f" GROUP BY {gcols}" if gcols else "")

        src, conds = self._source(node, set())
        return f"SELECT * FROM {src}{self._where(conds)}"

    # ── FROM clause pieces ──
    def _source(self, node, used: set):
        """Return (from_clause, where_conditions) for node."""
        if node is None:
            raise ValueError("Missing relation: expected a table name or a parenthesised expression")

        if isinstance(node, SelectionNode):
            src, conds = self._source(node.child, used)
            return src, conds + [node.condition]

        if isinstance(node, self.JOINS):
            if isinstance(node.left, self.JOINS):
                left, _ = self._source(node.left, used)   # chain joins left-to-right
            else:
                left = self._item(node.left, used)
            right = self._item(node.right, used)

            if isinstance(node, CrossJoinNode):
                return f"{left} CROSS JOIN {right}", []
            if isinstance(node, NaturalJoinNode):
                return f"{left} NATURAL JOIN {right}", []
            if isinstance(node, ThetaJoinNode):
                return f"{left} JOIN {right} ON {self._cond(node.condition)}", []
            kw = node.kind.upper()
            if node.condition:
                return f"{left} {kw} JOIN {right} ON {self._cond(node.condition)}", []
            return f"{left} NATURAL {kw} JOIN {right}", []

        return self._item(node, used), []

    def _item(self, node, used: set) -> str:
        """A single FROM item: a table, an aliased table, or an aliased subquery."""
        if node is None:
            raise ValueError("Missing relation: expected a table name or a parenthesised expression")

        if isinstance(node, TableNode):
            used.add(node.name.lower())
            return node.name

        if isinstance(node, RenameNode):
            alias = node.new_name
            used.add(alias.lower())
            if isinstance(node.child, TableNode) and not node.columns:
                return f"{node.child.name} AS {alias}"
            sub_sql = self._query(node.child)
            if not node.columns:
                return f"({sub_sql}) AS {alias}"
            old_cols = self._get_columns(sub_sql)
            if len(old_cols) != len(node.columns):
                raise ValueError(f"Rename expects {len(old_cols)} columns, got {len(node.columns)}")
            items = ", ".join(f'"{o}" AS {n}' for o, n in zip(old_cols, node.columns))
            return f"(SELECT {items} FROM ({sub_sql})) AS {alias}"

        base = self._base_name(node)
        alias = base if base and base.lower() not in used else self._fresh()
        used.add(alias.lower())
        return f"({self._query(node)}) AS {alias}"

    def _get_columns(self, sql: str) -> List[str]:
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_name)
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM ({sql}) LIMIT 0")
            cols = [desc[0] for desc in cur.description]
            conn.close()
            return cols
        except Exception as e:
            raise ValueError(f"Error extracting schema from DB '{self.db_name}': {e}")

    def _division(self, node: ExpressionNode) -> str:
        left_sql = self._query(node.left)
        right_sql = self._query(node.right)

        left_cols = self._get_columns(left_sql)
        right_cols = self._get_columns(right_sql)
        right_lower = [c.lower() for c in right_cols]

        shared = [c for c in left_cols if c.lower() in right_lower]
        unshared = [c for c in left_cols if c.lower() not in right_lower]

        if not shared:
            raise ValueError("No common columns for division")
        if not unshared:
            raise ValueError("Left relation must have columns not present in right relation")
        if len(shared) != len(right_cols):
            raise ValueError("Division: every column of the right relation must also be in the left relation")

        q = lambda alias, cols: ", ".join(f'{alias}."{c}"' for c in cols)
        match = " AND ".join(f'L2."{c}" = L1."{c}"' for c in unshared)

        return f"""SELECT DISTINCT {q('L1', unshared)}
FROM ({left_sql}) AS L1
WHERE NOT EXISTS (
    SELECT {q('R', shared)} FROM ({right_sql}) AS R
    EXCEPT
    SELECT {q('L2', shared)} FROM ({left_sql}) AS L2 WHERE {match}
)"""


# ── QueryProcessor ────────────────────────────────────────────────────────────

class QueryProcessor:
    """Main processor for converting relational algebra queries to SQL"""
    def __init__(self, query: str, db_name: str = "database.db"):
        self.query = query
        self.db_name = db_name
        self.tokens = None
        self.tree = None
        self.sql = None

    def process(self) -> str:
        import re
        if re.match(r"^\s*\(?\s*SELECT\b", self.query, re.IGNORECASE):
            raise ValueError("This looks like SQL, not relational algebra. Use the 'SQL → Relational "
                             "Algebra' panel (or sql_to_ra.translate) to convert it, or write it "
                             "with π, σ, ⋈ ...")
        tokenizer = Tokenizer(self.query)
        self.tokens = tokenizer.tokenize()
        print(f"✓ Tokens: {[str(t) for t in self.tokens if t.type != TokenType.EOF]}\n")

        builder = ExpressionTreeBuilder(self.tokens)
        self.tree = builder.build()
        print(f"✓ Expression Tree:\n{self.tree.display()}\n")

        conv = SQLConverter(self.tree, self.db_name)
        self.sql = conv.convert()
        return self.sql


def query_database(ra_query: str, database_name: str = "database.db") -> tuple[str, list]:
    """Convert a relational algebra expression to SQL, execute it, and return
    the generated SQL and result rows.
    """
    processor = QueryProcessor(ra_query, database_name)
    sql = processor.process()
    from sql_conector import execute
    import sqlite3
    try:
        rows = execute(sql, database_name=database_name)
    except sqlite3.OperationalError as err:
        raise ValueError(f"database error: {err}")
    return sql, rows


if __name__ == "__main__":
    try:
        q = input("Enter the query (e.g., π name (students) ∪ π name (professor))\n> ")
        processor = QueryProcessor(q)
        sql = processor.process()
        print(f"✓ SQL Query: {sql}")
        from explainer import explain
        print(f"✓ In English: {explain(processor.tree)}")
    except ValueError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")