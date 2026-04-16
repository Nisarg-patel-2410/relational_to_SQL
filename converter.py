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
    UNION      = "∪"
    INTERSECT  = "∩"
    MINUS      = "−"
    DIVISION   = "÷"
    RENAME     = "ρ"
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
        "∪": TokenType.UNION,
        "∩": TokenType.INTERSECT,
        "−": TokenType.MINUS,
        "-": TokenType.MINUS,  # support regular hyphen for minus
        "÷": TokenType.DIVISION,
        "/": TokenType.DIVISION,
        "ρ": TokenType.RENAME,
    }

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
                self.tokens.append(Token(self.OPERATORS[char], char))
                self.pos += 1
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
        while self.pos < len(self.query) and self.query[self.pos] not in "()πσ×⋈⨝∪∩−-÷/ρ":
            self.pos += 1
        return self.query[start:self.pos].strip()

    def _looks_like_condition(self, value: str) -> bool:
        """Return True if value looks like a filter condition (comparison ops or AND/OR)."""
        upper = value.upper()
        return (
            any(op in value for op in "<>=!") or
            " AND " in upper or " OR " in upper
        )


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


# ── Parser ───────────────────────────────────────────────────────────────────

class ExpressionTreeBuilder:
    """Builds an expression tree from tokens"""
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def build(self) -> ExpressionNode:
        return self._parse_set_op()

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

        while self._current_token().type in (TokenType.CROSSJOIN, TokenType.NATURALJOIN, TokenType.DIVISION):
            tok = self._current_token()
            self.pos += 1
            right = self._parse_unary()
            if tok.type == TokenType.CROSSJOIN:
                left = CrossJoinNode(left, right)
            elif tok.type == TokenType.NATURALJOIN:
                left = NaturalJoinNode(left, right)
            elif tok.type == TokenType.DIVISION:
                left = DivisionNode(left, right)

        return left

    def _parse_unary(self) -> ExpressionNode:
        """Parse unary operations (higher precedence than joins)"""
        operations = []

        while self._current_token().type in (TokenType.PROJECT, TokenType.SELECT, TokenType.RENAME):
            token = self._current_token()
            self.pos += 1
            if token.type == TokenType.PROJECT:
                operations.append(('project', self._read_columns()))
            elif token.type == TokenType.SELECT:
                operations.append(('select', self._read_condition()))
            elif token.type == TokenType.RENAME:
                operations.append(('rename', self._read_rename()))

        node = self._parse_primary()

        # Apply unary operators from inside out
        for op_type, op_value in reversed(operations):
            if op_type == 'project':
                node = ProjectionNode(op_value, node)
            elif op_type == 'select':
                node = SelectionNode(op_value, node)
            elif op_type == 'rename':
                node = RenameNode(op_value, node)

        return node

    def _parse_primary(self) -> Optional[ExpressionNode]:
        token = self._current_token()

        if token.type == TokenType.LPAREN:
            self.pos += 1
            node = self._parse_set_op()
            if self._current_token().type == TokenType.RPAREN:
                self.pos += 1
            return node

        elif token.type == TokenType.IDENTIFIER:
            node = TableNode(token.value)
            self.pos += 1
            return node

        return None

    def _current_token(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "")

    def _read_columns(self) -> List[str]:
        if self._current_token().type == TokenType.IDENTIFIER:
            columns_str = self._current_token().value
            self.pos += 1
            return [col.strip() for col in columns_str.split(",")]
        return ["*"]

    def _read_condition(self) -> str:
        if self._current_token().type == TokenType.CONDITION:
            condition = self._current_token().value
            self.pos += 1
            return condition
        return ""

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
    """Converts expression tree to SQL query"""
    def __init__(self, tree: Optional[ExpressionNode], db_name: str = "database.db"):
        self.tree = tree
        self.columns = ["*"]
        self.condition = ""
        self.db_name = db_name

    def convert(self) -> str:
        if not self.tree:
            return ""

        # Set operations and Division are handled directly at the top level
        if isinstance(self.tree, (UnionNode, IntersectNode, MinusNode)):
            left_sql = SQLConverter(self.tree.left, self.db_name).convert()
            right_sql = SQLConverter(self.tree.right, self.db_name).convert()
            if isinstance(self.tree, UnionNode):
                return f"{left_sql} UNION {right_sql}"
            elif isinstance(self.tree, IntersectNode):
                return f"{left_sql} INTERSECT {right_sql}"
            elif isinstance(self.tree, MinusNode):
                return f"{left_sql} EXCEPT {right_sql}"

        if isinstance(self.tree, DivisionNode):
            return self._build_division(self.tree)

        # For normal queries (project, select, joins, rename)
        self._extract(self.tree)
        from_clause = self._build_from(self.tree)
        
        if not from_clause:
            raise ValueError("No table specified in query")
            
        columns_str = ", ".join(self.columns) if self.columns else "*"
        sql = f"SELECT {columns_str} FROM {from_clause}"
        
        if self.condition:
            sql += f" WHERE {self.condition}"
            
        return sql

    def _extract(self, node: ExpressionNode):
        """Extract projection columns and filter condition from the tree"""
        # Stop extraction at barriers that create derived tables or complete subqueries
        if isinstance(node, (UnionNode, IntersectNode, MinusNode, RenameNode, DivisionNode)):
            return

        if isinstance(node, ProjectionNode):
            self.columns = node.columns
            if node.child:
                self._extract(node.child)
        elif isinstance(node, SelectionNode):
            self.condition = node.condition
            if node.child:
                self._extract(node.child)
        elif isinstance(node, (CrossJoinNode, NaturalJoinNode)):
            self._extract(node.left)
            self._extract(node.right)

    def _build_from(self, node: Optional[ExpressionNode]) -> str:
        """Recursively build the FROM clause, including JOIN expressions"""
        if node is None:
            return ""
            
        if isinstance(node, TableNode):
            return node.name
            
        # Unary operations (if bypassed by _extract, they resolve to their child's FROM clause)
        if isinstance(node, (ProjectionNode, SelectionNode)):
            return self._build_from(node.child)

        # Operators inside a FROM clause must be wrapped in a subquery
        if isinstance(node, (UnionNode, IntersectNode, MinusNode, DivisionNode)):
            if isinstance(node, DivisionNode):
                sub_sql = self._build_division(node)
            else:
                sub_sql = SQLConverter(node, self.db_name).convert()
            return f"({sub_sql})"
            
        # Rename operator wraps its child and aliases it
        if isinstance(node, RenameNode):
            if isinstance(node.child, TableNode) and not node.columns:
                return f"{node.child.name} AS {node.new_name}"
            else:
                sub_sql = SQLConverter(node.child, self.db_name).convert()
                if not node.columns:
                    return f"({sub_sql}) AS {node.new_name}"
                else:
                    old_cols = self._get_columns(sub_sql)
                    if len(old_cols) != len(node.columns):
                        raise ValueError(f"Rename expects {len(old_cols)} columns, got {len(node.columns)}")
                    select_items = ", ".join(f"{old} AS {new}" for old, new in zip(old_cols, node.columns))
                    return f"(SELECT {select_items} FROM ({sub_sql})) AS {node.new_name}"

        # Joins
        if isinstance(node, CrossJoinNode):
            left  = self._build_from(node.left)
            right = self._build_from(node.right)
            return f"{left}, {right}"
            
        if isinstance(node, NaturalJoinNode):
            left  = self._build_from(node.left)
            right = self._build_from(node.right)
            return f"{left} NATURAL JOIN {right}"
            
        return ""

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

    def _build_division(self, node: ExpressionNode) -> str:
        left_sql = SQLConverter(node.left, self.db_name).convert()
        right_sql = SQLConverter(node.right, self.db_name).convert()
        
        left_cols = self._get_columns(left_sql)
        right_cols = self._get_columns(right_sql)
        
        shared_cols = [c for c in left_cols if c in right_cols]
        unshared_cols = [c for c in left_cols if c not in right_cols]
        
        if not shared_cols:
            raise ValueError("No common columns for division")
            
        if not unshared_cols:
            raise ValueError("Left relation must have columns not present in right relation")
            
        x_cols = ", ".join([f"L1.{c}" for c in unshared_cols])
        where_conds = " AND ".join([f"L1.{c} = L2.{c}" for c in unshared_cols])
        y_cols = ", ".join([f"R.{c}" for c in shared_cols])
        y_cols_L2 = ", ".join([f"L2.{c}" for c in shared_cols])
        
        sql = f"""SELECT DISTINCT {x_cols}
FROM ({left_sql}) AS L1
WHERE NOT EXISTS (
    SELECT {y_cols} FROM ({right_sql}) AS R
    EXCEPT
    SELECT {y_cols_L2} FROM ({left_sql}) AS L2 WHERE {where_conds}
)"""
        return sql


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
    except ValueError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")