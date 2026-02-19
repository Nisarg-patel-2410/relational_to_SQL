import converter
import sql_conector


if __name__ == "__main__":
    print("Relational Algebra to SQL Converter")
    print("="*50)
    print("Examples:")
    print("  π Brand σ Price<100 (Foods)")
    print("  (Students × Products)")
    print("  π Name,Price (Students × Products)")
    print("  σ Age>20 (Students × Department)")
    print("="*50)
    
    query = input("\nEnter relational algebra query: ")
    processor = converter.QueryProcessor(query)
    result = processor.process()
    print(f"\nGenerated SQL Query: {result}")
    
    # Execute it in the SQL server
    try:
        result_data = sql_conector.execute(result)
        if result_data:
            print(f"\nQuery Results:")
            for row in result_data:
                print(row)
        else:
            print("\nQuery executed successfully")
    except Exception as e:
        print(f"Database error: {e}")
    