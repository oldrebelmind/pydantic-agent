#!/usr/bin/env python3
"""Clean test data from Neo4j"""

from neo4j import GraphDatabase

uri = "bolt://192.168.1.97:17687"
username = "neo4j"
password = "password123"

driver = GraphDatabase.driver(uri, auth=(username, password))

with driver.session() as session:
    # Delete test entities
    test_names = ['Alice', 'Alice Smith', 'Tom', 'TEST USER', 'Sarah', 'DEBUG TEST', 'FINAL TEST', 'Bob Jones', 'David Brown']

    for name in test_names:
        result = session.run(
            "MATCH (n) WHERE n.name = $name DETACH DELETE n RETURN count(n) as deleted",
            name=name
        )
        count = result.single()["deleted"]
        if count > 0:
            print(f"Deleted {count} nodes for {name}")

    # Delete edges about test people
    result = session.run(
        """
        MATCH ()-[r]-()
        WHERE r.fact CONTAINS 'Alice' OR r.fact CONTAINS 'Tom' OR r.fact CONTAINS 'TEST' OR r.fact CONTAINS 'Sarah'
        DELETE r
        RETURN count(r) as deleted
        """
    )
    count = result.single()["deleted"]
    print(f"Deleted {count} test edges")

driver.close()
print("Test data cleanup complete!")
