from converter import QueryProcessor

# Test query with cross join
query = "π Name,Price (Students × Products)"
print(f"Input: {query}\n")

processor = QueryProcessor(query)
result = processor.process()
print(f"✓ SQL Query: {result}\n")

# Test another cross join with selection
query2 = "σ Price>100 (Students × Products)"
print(f"\nInput: {query2}\n")

processor2 = QueryProcessor(query2)
result2 = processor2.process()
print(f"✓ SQL Query: {result2}")
