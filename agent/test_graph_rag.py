#!/usr/bin/env python3
"""
Comprehensive Graph RAG Testing Suite

Tests the hybrid memory system's graph capabilities:
1. Multi-entity relationship queries
2. Temporal knowledge retrieval
3. Complex inference across multiple hops
4. Vector + graph result combination
"""

import asyncio
import json
import logging
from datetime import datetime
from hybrid_memory import HybridMemoryManager
from main import CUSTOM_FACT_EXTRACTION_PROMPT, CUSTOM_UPDATE_MEMORY_PROMPT

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
import os
OPENAI_API_KEY = os.environ.get("OPENAI_GRAPH_API_KEY", "")

# mem0 config with OpenAI
mem0_config = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",
            "temperature": 0.1,
            "max_tokens": 4000,
            "api_key": OPENAI_API_KEY,
            "openai_base_url": "https://api.openai.com/v1",
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "dbname": "agent_memory",
            "user": "postgres",
            "password": "postgres",
            "host": "postgres-memory",
            "port": 5432,
            "embedding_model_dims": 768,
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            "ollama_base_url": "http://192.168.1.97:11434",
            "embedding_dims": 768,
        }
    },
    "custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT,
    "custom_update_memory_prompt": CUSTOM_UPDATE_MEMORY_PROMPT,
}


async def test_multi_entity_relationships():
    """Test queries that require traversing multiple entity relationships."""
    print("\n" + "=" * 80)
    print("TEST 1: Multi-Entity Relationship Queries")
    print("=" * 80)

    manager = HybridMemoryManager(
        mem0_config=mem0_config,
        neo4j_uri="bolt://192.168.1.97:17687",
        neo4j_username="neo4j",
        neo4j_password="password123",
        openai_api_key=OPENAI_API_KEY
    )

    await manager.initialize()

    try:
        # Add complex relational information
        user_id = "brian_graph_test"

        conversations = [
            # Conversation 1: Work relationships
            {
                "messages": [
                    {"role": "user", "content": "I work at Brainiacs, which specializes in AI agent development"},
                    {"role": "assistant", "content": "That sounds like an exciting field!"}
                ],
                "description": "Work and company specialization"
            },
            # Conversation 2: Project details
            {
                "messages": [
                    {"role": "user", "content": "My current project uses Pydantic AI with a hybrid memory system combining mem0 and Graphiti"},
                    {"role": "assistant", "content": "That's a sophisticated architecture!"}
                ],
                "description": "Project tech stack"
            },
            # Conversation 3: Location context
            {
                "messages": [
                    {"role": "user", "content": "Brainiacs office is downtown Indianapolis, while I live on the north side"},
                    {"role": "assistant", "content": "Interesting geographic split!"}
                ],
                "description": "Geographic relationships"
            },
            # Conversation 4: Team structure
            {
                "messages": [
                    {"role": "user", "content": "I collaborate with Sarah on the memory architecture and Tom on the frontend"},
                    {"role": "assistant", "content": "Great to have specialized team members!"}
                ],
                "description": "Team relationships"
            }
        ]

        # Add all conversations
        for i, conv in enumerate(conversations):
            print(f"\nAdding conversation {i+1}: {conv['description']}")
            result = await manager.add(
                messages=conv["messages"],
                user_id=user_id,
                agent_id="graph_rag_agent"
            )
            print(f"✓ Added to mem0: {len(result.get('mem0', {}).get('results', []))} memories")
            await asyncio.sleep(1)  # Give graph time to process

        # Test complex queries requiring multi-hop traversal
        test_queries = [
            "What does the company I work for specialize in?",
            "What technologies am I using in my current project?",
            "Where is my office located relative to where I live?",
            "Who do I work with on different parts of the project?"
        ]

        for query in test_queries:
            print(f"\n{'─' * 80}")
            print(f"Query: {query}")
            print(f"{'─' * 80}")

            results = await manager.search(
                query=query,
                user_id=user_id,
                limit=5
            )

            print(f"\n📊 Results Summary:")
            print(f"  Vector results: {len(results['vector_results'])}")
            print(f"  Graph results: {len(results['graph_results'])}")

            print(f"\n📝 Combined Context:")
            print(results['combined_context'] if results['combined_context'] else "  (no context)")

            await asyncio.sleep(1)

    finally:
        await manager.close()


async def test_temporal_queries():
    """Test queries that leverage Graphiti's temporal awareness."""
    print("\n" + "=" * 80)
    print("TEST 2: Temporal Knowledge Retrieval")
    print("=" * 80)

    manager = HybridMemoryManager(
        mem0_config=mem0_config,
        neo4j_uri="bolt://192.168.1.97:17687",
        neo4j_username="neo4j",
        neo4j_password="password123",
        openai_api_key=OPENAI_API_KEY
    )

    await manager.initialize()

    try:
        user_id = "brian_temporal_test"

        # Add time-sequenced information
        conversations = [
            {
                "messages": [
                    {"role": "user", "content": "I started learning about graph databases last month"},
                    {"role": "assistant", "content": "Great timing for your current project!"}
                ],
                "description": "Learning timeline"
            },
            {
                "messages": [
                    {"role": "user", "content": "This week I integrated Graphiti into the memory system"},
                    {"role": "assistant", "content": "Impressive progress!"}
                ],
                "description": "Recent integration work"
            },
            {
                "messages": [
                    {"role": "user", "content": "Before that, I was using just vector search with mem0"},
                    {"role": "assistant", "content": "The hybrid approach should be more powerful!"}
                ],
                "description": "Previous architecture"
            }
        ]

        for i, conv in enumerate(conversations):
            print(f"\nAdding temporal conversation {i+1}: {conv['description']}")
            await manager.add(
                messages=conv["messages"],
                user_id=user_id,
                agent_id="graph_rag_agent"
            )
            await asyncio.sleep(2)  # Add delay between conversations to create temporal separation

        # Test temporal queries
        temporal_queries = [
            "What was my previous memory architecture?",
            "What did I recently integrate?",
            "When did I start learning about graphs?"
        ]

        for query in temporal_queries:
            print(f"\n{'─' * 80}")
            print(f"Query: {query}")
            print(f"{'─' * 80}")

            results = await manager.search(
                query=query,
                user_id=user_id,
                limit=5
            )

            print(f"\n📊 Results Summary:")
            print(f"  Vector results: {len(results['vector_results'])}")
            print(f"  Graph results: {len(results['graph_results'])}")

            print(f"\n📝 Combined Context:")
            print(results['combined_context'] if results['combined_context'] else "  (no context)")

    finally:
        await manager.close()


async def test_multi_hop_inference():
    """Test queries requiring inference across multiple graph hops."""
    print("\n" + "=" * 80)
    print("TEST 3: Multi-Hop Inference")
    print("=" * 80)

    manager = HybridMemoryManager(
        mem0_config=mem0_config,
        neo4j_uri="bolt://192.168.1.97:17687",
        neo4j_username="neo4j",
        neo4j_password="password123",
        openai_api_key=OPENAI_API_KEY
    )

    await manager.initialize()

    try:
        user_id = "brian_inference_test"

        # Create a chain of related facts
        conversations = [
            {
                "messages": [
                    {"role": "user", "content": "My favorite programming language is Python"},
                    {"role": "assistant", "content": "Python is excellent for AI work!"}
                ],
                "description": "Language preference"
            },
            {
                "messages": [
                    {"role": "user", "content": "I use Python for building AI agents with Pydantic AI"},
                    {"role": "assistant", "content": "Pydantic AI is a great framework!"}
                ],
                "description": "Framework choice"
            },
            {
                "messages": [
                    {"role": "user", "content": "The AI agents I build help automate customer support workflows"},
                    {"role": "assistant", "content": "That's a valuable application!"}
                ],
                "description": "Application domain"
            },
            {
                "messages": [
                    {"role": "user", "content": "Customer support automation is my main focus at Brainiacs"},
                    {"role": "assistant", "content": "Sounds like you're aligned with company goals!"}
                ],
                "description": "Company focus"
            }
        ]

        for i, conv in enumerate(conversations):
            print(f"\nAdding inference chain conversation {i+1}: {conv['description']}")
            await manager.add(
                messages=conv["messages"],
                user_id=user_id,
                agent_id="graph_rag_agent"
            )
            await asyncio.sleep(1)

        # Queries requiring multi-hop reasoning
        inference_queries = [
            "What do I build at work?",  # Requires: company → work → agents → application
            "What language do I use for my main work focus?",  # Requires: work focus → agents → framework → language
            "How does my technology choice relate to my job?"  # Requires multiple hops
        ]

        for query in inference_queries:
            print(f"\n{'─' * 80}")
            print(f"Query: {query}")
            print(f"{'─' * 80}")

            results = await manager.search(
                query=query,
                user_id=user_id,
                limit=8  # More results for complex queries
            )

            print(f"\n📊 Results Summary:")
            print(f"  Vector results: {len(results['vector_results'])}")
            print(f"  Graph results: {len(results['graph_results'])}")

            print(f"\n📝 Combined Context:")
            print(results['combined_context'] if results['combined_context'] else "  (no context)")

            # Show individual graph results for debugging
            if results['graph_results']:
                print(f"\n🔗 Graph Relationships Found:")
                for i, edge in enumerate(results['graph_results'][:5]):
                    if hasattr(edge, 'fact'):
                        print(f"  {i+1}. {edge.fact}")

    finally:
        await manager.close()


async def test_hybrid_combination():
    """Test that vector and graph results are effectively combined."""
    print("\n" + "=" * 80)
    print("TEST 4: Vector + Graph Result Combination")
    print("=" * 80)

    manager = HybridMemoryManager(
        mem0_config=mem0_config,
        neo4j_uri="bolt://192.168.1.97:17687",
        neo4j_username="neo4j",
        neo4j_password="password123",
        openai_api_key=OPENAI_API_KEY
    )

    await manager.initialize()

    try:
        user_id = "brian_hybrid_test"

        # Add diverse information
        conversations = [
            {
                "messages": [
                    {"role": "user", "content": "I'm passionate about open source software and contribute to several projects"},
                    {"role": "assistant", "content": "That's great for the community!"}
                ],
                "description": "Open source passion"
            },
            {
                "messages": [
                    {"role": "user", "content": "On weekends I enjoy hiking in the Indiana state parks"},
                    {"role": "assistant", "content": "Good balance with tech work!"}
                ],
                "description": "Weekend hobbies"
            },
            {
                "messages": [
                    {"role": "user", "content": "I'm currently reading about graph theory and its applications in knowledge representation"},
                    {"role": "assistant", "content": "Very relevant to your current project!"}
                ],
                "description": "Current interests"
            }
        ]

        for i, conv in enumerate(conversations):
            print(f"\nAdding hybrid test conversation {i+1}: {conv['description']}")
            await manager.add(
                messages=conv["messages"],
                user_id=user_id,
                agent_id="graph_rag_agent"
            )
            await asyncio.sleep(1)

        # Queries that should leverage both vector and graph
        hybrid_queries = [
            "What am I interested in?",  # Should get: open source, graph theory, hiking
            "What do I do in my free time?",  # Should leverage both systems
            "Tell me about my learning and hobbies"  # Complex multi-topic query
        ]

        for query in hybrid_queries:
            print(f"\n{'─' * 80}")
            print(f"Query: {query}")
            print(f"{'─' * 80}")

            results = await manager.search(
                query=query,
                user_id=user_id,
                limit=5
            )

            print(f"\n📊 Results Summary:")
            print(f"  Vector results: {len(results['vector_results'])}")
            print(f"  Graph results: {len(results['graph_results'])}")

            # Analyze source of each context item
            if results['combined_context']:
                print(f"\n📝 Combined Context:")
                print(results['combined_context'])

                # Count context sources
                context_lines = results['combined_context'].split('\n')
                facts = [line for line in context_lines if line.startswith('- ')]
                print(f"\n🔍 Analysis:")
                print(f"  Total facts in context: {len(facts)}")
                print(f"  Vector source count: {len(results['vector_results'])}")
                print(f"  Graph source count: {len(results['graph_results'])}")

                if len(results['vector_results']) > 0 and len(results['graph_results']) > 0:
                    print(f"  ✓ Successfully combining both vector and graph results!")

    finally:
        await manager.close()


async def main():
    """Run all graph RAG tests."""
    print("\n" + "=" * 80)
    print("GRAPH RAG COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")

    try:
        # Run all tests
        await test_multi_entity_relationships()
        await test_temporal_queries()
        await test_multi_hop_inference()
        await test_hybrid_combination()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED")
        print("=" * 80)
        print(f"Finished at: {datetime.now().isoformat()}")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
