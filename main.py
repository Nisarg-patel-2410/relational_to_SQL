import converter
import sql_conector


if __name__ == "__main__":
    query = input("Enter relational algebra query: ")
    processor = converter.QueryProcessor(query)
    result = processor.process()
    print(f"Generated SQL Query: {result}")
    
    # execute it in the sql server
    print(sql_conector.execute(result))
    