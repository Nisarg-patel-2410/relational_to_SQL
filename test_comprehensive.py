from converter import QueryProcessor

# Test cases
test_queries = [
    # Basic cross join
    ("(Students × Products)", "Basic cross join"),
    # Projection on cross join
    ("π Name,Price (Students × Products)", "Projection on cross join"),
    # Selection on cross join
    ("σ Price>100 (Students × Products)", "Selection on cross join"),
    # Multiple operations on cross join
    ("π Name,Price σ Price>100 (Students × Products)", "Selection then projection"),
]

for query, description in test_queries:
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"Input: {query}")
    print('='*60)
    
    try:
        processor = QueryProcessor(query)
        result = processor.process()
        print(f"✓ SQL Query: {result}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
