# Object-oriented version with tokenizer, expression tree, and SQL converter
# by: Nisarg Kanasagra, abdulla bohra, santhosh koshik lukka, and nikhil lodhi
# Improved OOP functionality for better maintainability and extensibility

from enum import Enum
from typing import List, Optional, Union


class TokenType(Enum):
    """Token types for relational algebra query"""
    PROJECT = "π"
    SELECT = "σ"
    CROSSJOIN = "×"
    NATURALJOIN = "⋈"
    LPAREN = "("
    RPAREN = ")"
    IDENTIFIER = "IDENTIFIER"
    CONDITION = "CONDITION"
    EOF = "EOF"


class Token:
    """Represents a single token in the query"""
    def __init__(self, type_: TokenType, value: str):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r})"


class Tokenizer:
    """Tokenizes relational algebra queries into tokens"""
    OPERATORS = {"π": TokenType.PROJECT, "?": TokenType.PROJECT, "σ": TokenType.SELECT, "×": TokenType.CROSSJOIN, "⋈": TokenType.NATURALJOIN}

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
                # Read identifier or condition
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
        while self.pos < len(self.query) and self.query[self.pos] not in "()" and self.query[self.pos] not in self.OPERATORS:
            self.pos += 1
        return self.query[start:self.pos].strip()


class ExpressionNode:
    """Base class for expression tree nodes"""
    def __repr__(self):
        return self.display()
    
    def display(self, indent: int = 0) -> str:
        """Display the expression tree in a readable format"""
        raise NotImplementedError("Subclasses must implement display()")


class TableNode(ExpressionNode):
    """Represents a table in the query"""
    def __init__(self, name: str):
        self.name = name
    
    def display(self, indent: int = 0) -> str:
        """Display the table node"""
        return f"{'  ' * indent}└─ Table: {self.name}"


class ProjectionNode(ExpressionNode):
    """Represents π (projection/SELECT columns) operation"""
    def __init__(self, columns: List[str], child: Optional[ExpressionNode] = None):
        self.columns = columns
        self.child = child
    
    def display(self, indent: int = 0) -> str:
        """Display the projection node"""
        result = f"{'  ' * indent}├─ π (Project): {', '.join(self.columns)}\n"
        if self.child:
            result += self.child.display(indent + 1)
        return result


class SelectionNode(ExpressionNode):
    """Represents σ (selection/WHERE clause) operation"""
    def __init__(self, condition: str, child: Optional[ExpressionNode] = None):
        self.condition = condition
        self.child = child
    
    def display(self, indent: int = 0) -> str:
        """Display the selection node"""
        result = f"{'  ' * indent}├─ σ (Select): {self.condition}\n"
        if self.child:
            result += self.child.display(indent + 1)
        return result


class CrossJoinNode(ExpressionNode):
    """Represents × (cross join/Cartesian product) operation"""
    def __init__(self, left: ExpressionNode, right: ExpressionNode):
        self.left = left
        self.right = right
    
    def display(self, indent: int = 0) -> str:
        """Display the cross join node"""
        result = f"{'  ' * indent}├─ × (Cross Join)\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


class NaturalJoinNode(ExpressionNode):
    """Represents ⋈ (natural join) operation"""
    def __init__(self, left: ExpressionNode, right: ExpressionNode):
        self.left = left
        self.right = right

    def display(self, indent: int = 0) -> str:
        result = f"{'  ' * indent}├─ ⋈ (Natural Join)\n"
        result += self.left.display(indent + 1)
        result += self.right.display(indent + 1)
        return result


class ExpressionTreeBuilder:
    """Builds an expression tree from tokens"""
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def build(self) -> ExpressionNode:
        """Build the expression tree from tokens"""
        return self._parse_crossjoin()

    def _parse_crossjoin(self) -> ExpressionNode:
        """Parse cross join operations (lowest precedence)"""
        left = self._parse_unary()
        
        while self._current_token().type in (TokenType.CROSSJOIN, TokenType.NATURALJOIN):
            token = self._current_token()
            self.pos += 1
            right = self._parse_unary()
            if token.type == TokenType.CROSSJOIN:
                left = CrossJoinNode(left, right)
            else:
                left = NaturalJoinNode(left, right)
        
        return left

    def _parse_unary(self) -> ExpressionNode:
        """Parse unary operations (higher precedence than cross join)"""
        operations = []
        
        # Collect all unary operations
        while self._current_token().type in (TokenType.PROJECT, TokenType.SELECT):
            token = self._current_token()
            self.pos += 1
            
            if token.type == TokenType.PROJECT:
                columns = self._read_columns()
                operations.append(('project', columns))
            elif token.type == TokenType.SELECT:
                condition = self._read_condition()
                operations.append(('select', condition))
        
        # Parse the primary expression
        node = self._parse_primary()
        
        # Apply unary operations in reverse order (from innermost to outermost)
        for op_type, op_value in reversed(operations):
            if op_type == 'project':
                node = ProjectionNode(op_value, node)
            elif op_type == 'select':
                node = SelectionNode(op_value, node)
        
        return node

    def _parse_primary(self) -> Optional[ExpressionNode]:
        """Parse primary expressions (tables and parenthesized expressions)"""
        token = self._current_token()

        if token.type == TokenType.LPAREN:
            self.pos += 1
            node = self._parse_crossjoin()  # Parse full expression inside parens
            if self._current_token().type == TokenType.RPAREN:
                self.pos += 1
            return node

        elif token.type == TokenType.IDENTIFIER:
            node = TableNode(token.value)
            self.pos += 1
            return node

        return None

    def _current_token(self) -> Token:
        """Get current token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "")

    def _read_columns(self) -> List[str]:
        """Read projection columns"""
        # print(self._current_token())
        if self._current_token().type == TokenType.IDENTIFIER:
            columns_str = self._current_token().value
            self.pos += 1
            return [col.strip() for col in columns_str.split(",")]
        return ["*"]

    def _read_condition(self) -> str:
        """Read selection condition"""
        if self._current_token().type == TokenType.CONDITION:
            condition = self._current_token().value
            self.pos += 1
            return condition
        return ""


class SQLConverter:
    """Converts expression tree to SQL query"""
    def __init__(self, tree: Optional[ExpressionNode]):
        self.tree = tree
        self.columns = ["*"]
        self.tables = []
        self.condition = ""

    def _build_from(self, node: Optional[ExpressionNode]) -> str:
        """Recursively build the FROM expression including joins"""
        if node is None:
            return ""

        if isinstance(node, TableNode):
            return node.name

        if isinstance(node, ProjectionNode) or isinstance(node, SelectionNode):
            if node.child:
                return self._build_from(node.child)
            return ""

        if isinstance(node, CrossJoinNode):
            left = self._build_from(node.left)
            right = self._build_from(node.right)
            return f"({left} CROSS JOIN {right})"

        if isinstance(node, NaturalJoinNode):
            left = self._build_from(node.left)
            right = self._build_from(node.right)
            return f"({left} NATURAL JOIN {right})"

        return ""

    def convert(self) -> str:
        """Convert expression tree to SQL query"""
        if self.tree:
            self._traverse(self.tree)
        from_expr = self._build_from(self.tree)
        return self._build_sql(from_expr)

    def _traverse(self, node: ExpressionNode):
        """Traverse the tree and extract SQL components"""
        if isinstance(node, TableNode):
            self.tables.append(node.name)

        elif isinstance(node, ProjectionNode):
            self.columns = node.columns
            if node.child:
                self._traverse(node.child)

        elif isinstance(node, SelectionNode):
            self.condition = node.condition
            if node.child:
                self._traverse(node.child)

        elif isinstance(node, CrossJoinNode):
            self._traverse(node.left)
            self._traverse(node.right)
        
        elif isinstance(node, NaturalJoinNode):
            self._traverse(node.left)
            self._traverse(node.right)

    def _build_sql(self, from_expr: str) -> str:
        """Build SQL query from extracted components and FROM expression"""
        if not from_expr:
            raise ValueError("No table specified in query")

        columns_str = ", ".join(self.columns) if self.columns else "*"
        sql = f"SELECT {columns_str} FROM {from_expr}"

        if self.condition:
            sql += f" WHERE {self.condition}"

        return sql


class QueryProcessor:
    """Main processor for converting relational algebra queries to SQL"""
    def __init__(self, query: str):
        self.query = query
        self.tokens = None
        self.tree = None
        self.sql = None

    def process(self) -> str:
        """Process query and return SQL"""
        # Step 1: Tokenize
        tokenizer = Tokenizer(self.query)
        self.tokens = tokenizer.tokenize()
        print(f"✓ Tokens: {[str(t) for t in self.tokens if t.type != TokenType.EOF]}\n")
        # print(f"Tokenization successful\n")

        # Step 2: Build expression tree
        builder = ExpressionTreeBuilder(self.tokens)
        self.tree = builder.build()
        print(f"✓ Expression Tree:\n{self.tree.display()}\n")

        # Step 3: Convert to SQL
        converter = SQLConverter(self.tree) 
        self.sql = converter.convert()
        return self.sql




def query_database(ra_query: str, database_name: str = "database.db") -> tuple[str, list]:
    """Convert a relational algebra expression to SQL, execute it, and return
    the generated SQL and result rows.

    This is the backend entrypoint for both CLI and web front ends.
    """
    # convert the expression
    processor = QueryProcessor(ra_query)
    sql = processor.process()
    # lazy-import to avoid circular imports during module load
    from sql_conector import execute
    import sqlite3
    try:
        rows = execute(sql, database_name=database_name)
    except sqlite3.OperationalError as err:
        # propagate with clearer message for front ends
        raise ValueError(f"database error: {err}")
    return sql, rows


if __name__ == "__main__":
    # simple command-line prompt if the module is executed directly
    try:
        query = input("Enter the query (e.g., π Brand σ Price<100 (Foods))\n> ")
        sql, rows = query_database(query)
        print(f"✓ SQL Query: {sql}")
        if rows:
            print("✓ Result rows:")
            for r in rows:
                print(r)
        else:
            print("✓ Query executed (no rows returned or non-SELECT)")
    except ValueError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")