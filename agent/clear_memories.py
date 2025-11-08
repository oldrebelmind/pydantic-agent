#!/usr/bin/env python3
"""
Clear all memories from Milvus and Neo4j to start fresh
"""
from pymilvus import connections, utility
from neo4j import GraphDatabase
import os

print("=== Memory Cleanup Script ===\n")

# Milvus Configuration
MILVUS_HOST = os.getenv('MILVUS_HOST', 'localhost')
MILVUS_PORT = int(os.getenv('MILVUS_PORT', '19530'))

# Neo4j Configuration
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://192.168.1.97:7687')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')

print("1. Connecting to Milvus...")
try:
    connections.connect(
        alias="default",
        host=MILVUS_HOST,
        port=MILVUS_PORT
    )
    print(f"   ✓ Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")

    # List all collections
    collections = utility.list_collections()
    print(f"   Found {len(collections)} collection(s): {collections}")

    # Drop each collection
    for collection_name in collections:
        print(f"   Dropping collection: {collection_name}...")
        utility.drop_collection(collection_name)
        print(f"   ✓ Dropped {collection_name}")

    print("   ✓ All Milvus collections cleared\n")

except Exception as e:
    print(f"   ✗ Error with Milvus: {e}\n")

print("2. Connecting to Neo4j...")
try:
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )

    with driver.session() as session:
        # Count nodes before deletion
        result = session.run("MATCH (n) RETURN count(n) as count")
        count_before = result.single()["count"]
        print(f"   Found {count_before} node(s) in Neo4j")

        # Delete all nodes and relationships
        print("   Deleting all nodes and relationships...")
        session.run("MATCH (n) DETACH DELETE n")

        # Verify deletion
        result = session.run("MATCH (n) RETURN count(n) as count")
        count_after = result.single()["count"]
        print(f"   ✓ Deleted {count_before} nodes (remaining: {count_after})")

    driver.close()
    print("   ✓ Neo4j graph cleared\n")

except Exception as e:
    print(f"   ✗ Error with Neo4j: {e}\n")

print("=== Cleanup Complete ===")
print("\nYou can now start fresh with user_id: Brian McCleskey")
print("The agent will have no memories and you can retrain it.")
