#!/usr/bin/env python3
"""
Verify Neo4j Graph Relationships after mem0ai[graph] Installation
"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Neo4j connection
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://192.168.1.97:17687')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password123')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')

print(f"Connecting to Neo4j at {NEO4J_URI}...")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    with driver.session(database=NEO4J_DATABASE) as session:
        # Count all nodes
        result = session.run("MATCH (n) RETURN count(n) as node_count")
        node_count = result.single()['node_count']
        print(f"\n=== Total Nodes: {node_count} ===\n")

        # Get all nodes with their labels
        result = session.run("MATCH (n) RETURN labels(n) as labels, n LIMIT 20")
        print("=== All Nodes ===")
        for record in result:
            print(f"Labels: {record['labels']}, Node: {dict(record['n'])}")

        # Count all relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
        rel_count = result.single()['rel_count']
        print(f"\n=== Total Relationships: {rel_count} ===\n")

        # Get all relationships with details
        result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN labels(a) as from_labels, a.name as from_name,
                   type(r) as rel_type,
                   labels(b) as to_labels, b.name as to_name
            LIMIT 50
        """)
        print("=== All Relationships ===")
        for record in result:
            print(f"{record['from_labels']} '{record['from_name']}' --[{record['rel_type']}]--> {record['to_labels']} '{record['to_name']}'")

        # Check for recent kayaking-related relationships
        print("\n=== Kayaking-Related Entities ===")
        result = session.run("""
            MATCH (n)
            WHERE n.name CONTAINS 'kayaking' OR n.name CONTAINS 'florida'
               OR n.name CONTAINS 'captiva' OR n.name CONTAINS 'sanibel'
            RETURN labels(n) as labels, n
        """)
        for record in result:
            print(f"Labels: {record['labels']}, Node: {dict(record['n'])}")

        print("\n=== Kayaking Relationships ===")
        result = session.run("""
            MATCH (a)-[r]->(b)
            WHERE a.name CONTAINS 'kayaking' OR b.name CONTAINS 'kayaking'
               OR a.name CONTAINS 'florida' OR b.name CONTAINS 'florida'
               OR a.name CONTAINS 'captiva' OR b.name CONTAINS 'captiva'
            RETURN a.name as from, type(r) as rel, b.name as to
        """)
        for record in result:
            print(f"{record['from']} --[{record['rel']}]--> {record['to']}")

    driver.close()
    print("\n✅ GraphRAG verification complete!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
