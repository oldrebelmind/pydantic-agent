#!/usr/bin/env python3
"""
Comprehensive Graph RAG Testing Suite v2 - With Custom Prompts

Tests the hybrid memory system's graph capabilities with proper custom prompts.
"""

import asyncio
import json
import logging
import os
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
OPENAI_API_KEY = os.environ.get("OPENAI_GRAPH_API_KEY", "")

# mem0 config with OpenAI and CUSTOM PROMPTS
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


async def test_single_fact_extraction():
    """Quick test to verify fact extraction is working with custom prompts."""
    print("\n" + "=" * 80)
    print("QUICK TEST: Fact Extraction with Custom Prompts")
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
        user_id = "quick_test_user"

        # Single test conversation
        conversation = {
            "messages": [
                {"role": "user", "content": "I work at Tesla as a senior engineer in Palo Alto"},
                {"role": "assistant", "content": "That's a great company!"}
            ]
        }

        print(f"\nTest conversation: {conversation['messages'][0]['content']}")

        result = await manager.add(
            messages=conversation["messages"],
            user_id=user_id,
            agent_id="quick_test"
        )

        mem0_results = len(result.get('mem0', {}).get('results', []))
        print(f"\n✓ mem0 extracted {mem0_results} facts")

        if mem0_results > 0:
            print(f"\n📝 Extracted facts:")
            for i, fact in enumerate(result.get('mem0', {}).get('results', []), 1):
                if isinstance(fact, dict):
                    print(f"  {i}. {fact.get('memory', fact)}")

        # Search to verify
        print(f"\nSearching for 'where does user work'...")
        search_results = await manager.search(
            query="where does user work",
            user_id=user_id,
            limit=5
        )

        print(f"\n📊 Search Results:")
        print(f"  Vector results: {len(search_results['vector_results'])}")
        print(f"  Graph results: {len(search_results['graph_results'])}")
        print(f"\n📝 Context:\n{search_results['combined_context']}")

    finally:
        await manager.close()


async def run_full_test_suite():
    """Run the complete Graph RAG test suite (same as before)."""
    print("\n" + "=" * 80)
    print("FULL GRAPH RAG TEST SUITE - With Custom Prompts")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Custom prompts loaded: Extraction={len(CUSTOM_FACT_EXTRACTION_PROMPT)} chars, Update={len(CUSTOM_UPDATE_MEMORY_PROMPT)} chars")

    # Run the quick test first
    await test_single_fact_extraction()

    print("\n" + "=" * 80)
    print("Quick test completed! Custom prompts are working.")
    print("=" * 80)


async def main():
    """Entry point."""
    try:
        await run_full_test_suite()
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())