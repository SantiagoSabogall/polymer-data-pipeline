from dict import SEARCH_QUERIES

for level, queries in SEARCH_QUERIES.items():
    print("\n", level)
    for q in queries:
        print(" -", q)