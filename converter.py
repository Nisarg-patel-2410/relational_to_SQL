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
        "∪": TokenType.UNION,
        "∩": TokenType.INTERSECT,
        "−": TokenType.MINUS,
        "-": TokenType.MINUS,  # support regular hyphen for minus
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
                if any(op in token_value for op in "<>=!"):
                    self.tokens.append(Token(TokenType.CONDITION, token_value))
                else:
                    self.tokens.append(Token(TokenType.IDENTIFIER, token_value))

        self.tokens.append(Token(TokenType.EOF, ""))
        return self.tokens

    def _read_token(self) -> str:
        """Read a complete token (identifier or condition)"""
        start = self.pos
        while self.pos < len(self.query) and self.query[self.pos] not in "()πσ×⋈∪∩−-ρ":
            self.pos += 1
        return self.query[start:self.pos].strip()


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
    def __init__(self, new_name: str, child: Optional[ExpressionNode] = None):
        self.new_name = new_name
        self.child = child

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ ρ (Rename): {self.new_name}\n"
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
        """Parse cross / natural join operations"""
        left = self._parse_unary()

        while self._current_token().type in (TokenType.CROSSJOIN, TokenType.NATURALJOIN):
            tok = self._current_token()
            self.pos += 1
            right = self._parse_unary()
            if tok.type == TokenType.CROSSJOIN:
                left = CrossJoinNode(left, right)
            else:
                left = NaturalJoinNode(left, right)

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

    def _read_rename(self) -> str:
        if self._current_token().type == TokenType.IDENTIFIER:
            val = self._current_token().value
            self.pos += 1
            return val
        return "alias"


# ── SQL Converter ─────────────────────────────────────────────────────────────

class SQLConverter:
    """Converts expression tree to SQL query"""
    def __init__(self, tree: Optional[ExpressionNode]):
        self.tree = tree
        self.columns = ["*"]
        self.condition = ""

    def convert(self) -> str:
        if not self.tree:
            return ""

        # Set operations are handled directly at the top level to combine full subqueries.
        if isinstance(self.tree, (UnionNode, IntersectNode, MinusNode)):
            left_sql = SQLConverter(self.tree.left).convert()
            right_sql = SQLConverter(self.tree.right).convert()
            if isinstance(self.tree, UnionNode):
                return f"{left_sql} UNION {right_sql}"
            elif isinstance(self.tree, IntersectNode):
                return f"{left_sql} INTERSECT {right_sql}"
            elif isinstance(self.tree, MinusNode):
                return f"{left_sql} EXCEPT {right_sql}"

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
        if isinstance(node, (UnionNode, IntersectNode, MinusNode, RenameNode)):
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

        # Set operators inside a FROM clause must be wrapped in a subquery
        if isinstance(node, (UnionNode, IntersectNode, MinusNode)):
            sub_sql = SQLConverter(node).convert()
            return f"({sub_sql})"
            
        # Rename operator wraps its child and aliases it
        if isinstance(node, RenameNode):
            if isinstance(node.child, TableNode):
                return f"{node.child.name} AS {node.new_name}"
            else:
                sub_sql = SQLConverter(node.child).convert()
                return f"({sub_sql}) AS {node.new_name}"

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


# ── QueryProcessor ────────────────────────────────────────────────────────────

class QueryProcessor:
    """Main processor for converting relational algebra queries to SQL"""
    def __init__(self, query: str):
        self.query = query
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

        conv = SQLConverter(self.tree)
        self.sql = conv.convert()
        return self.sql


def query_database(ra_query: str, database_name: str = "database.db") -> tuple[str, list]:
    """Convert a relational algebra expression to SQL, execute it, and return
    the generated SQL and result rows.
    """
    processor = QueryProcessor(ra_query)
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