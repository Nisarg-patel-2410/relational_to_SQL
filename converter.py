# Object-oriented version with tokenizer, expression tree, and SQL converter
# by: Nisarg Kanasagra
# Improved OOP functionality for better maintainability and extensibility

from enum import Enum
from typing import List, Optional, Union


class TokenType(Enum):
    """Token types for relational algebra query"""
    PROJECT = "π"
    SELECT = "σ"
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
    OPERATORS = {"π": TokenType.PROJECT, "σ": TokenType.SELECT}

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
        while self.pos < len(self.query) and self.query[self.pos] not in "()πσ":
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


class ExpressionTreeBuilder:
    """Builds an expression tree from tokens"""
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def build(self) -> ExpressionNode:
        """Build the expression tree from tokens"""
        return self._parse_expression()

    def _current_token(self) -> Token:
        """Get current token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "")

    def _parse_expression(self) -> Optional[ExpressionNode]:
        """Parse operations and their operands"""
        node = None

        while self.pos < len(self.tokens):
            token = self._current_token()

            if token.type == TokenType.EOF:
                break

            elif token.type == TokenType.PROJECT:
                self.pos += 1
                columns = self._read_columns()
                # print(columns)
                node = ProjectionNode(columns, node)

            elif token.type == TokenType.SELECT:
                self.pos += 1
                condition = self._read_condition()
                node = SelectionNode(condition, node)

            elif token.type == TokenType.LPAREN:
                self.pos += 1
                inner_node = self._parse_expression()
                
                # Attach the inner node to the current tree
                if node is None:
                    node = inner_node
                else:
                    self._set_leaf_child(node, inner_node)
                
                if self._current_token().type == TokenType.RPAREN:
                    self.pos += 1

            elif token.type == TokenType.IDENTIFIER:
                node = TableNode(token.value)
                self.pos += 1

            elif token.type == TokenType.RPAREN:
                break

            else:
                self.pos += 1

        return node
    
    def _set_leaf_child(self, node: ExpressionNode, child: ExpressionNode):
        """Find the leaf node (one with child=None) and set its child"""
        if isinstance(node, TableNode):
            return
        if node.child is None:
            node.child = child
        else:
            self._set_leaf_child(node.child, child)

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
        self.table = ""
        self.condition = ""

    def convert(self) -> str:
        """Convert expression tree to SQL query"""
        if self.tree:
            self._traverse(self.tree)
        return self._build_sql()

    def _traverse(self, node: ExpressionNode):
        """Traverse the tree and extract SQL components"""
        if isinstance(node, TableNode):
            self.table = node.name

        elif isinstance(node, ProjectionNode):
            self.columns = node.columns
            if node.child:
                self._traverse(node.child)

        elif isinstance(node, SelectionNode):
            self.condition = node.condition
            if node.child:
                self._traverse(node.child)

    def _build_sql(self) -> str:
        """Build SQL query from extracted components"""
        if not self.table:
            raise ValueError("No table specified in query")

        columns_str = ", ".join(self.columns) if self.columns else "*"
        sql = f"SELECT {columns_str} FROM {self.table}"

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


if __name__ == "__main__":
    try:
        query = input("Enter the query (e.g., π Brand σ Price<100 (Foods))\n> ")
        processor = QueryProcessor(query)
        result = processor.process()
        print(f"✓ SQL Query: {result}")
    except ValueError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")