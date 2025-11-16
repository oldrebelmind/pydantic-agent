#!/usr/bin/env python3
"""Simple test of mem0 fact extraction"""

from mem0 import Memory
import json

# Simple test config
mem0_config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1:8b",
            "ollama_base_url": "http://192.168.1.97:11434",
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
}

print("=" * 80)
print("Testing mem0 with DEFAULT prompts...")
print("=" * 80)

try:
    memory = Memory.from_config(mem0_config)
    print("✓ Memory initialized")

    # Test simple fact extraction
    test_messages = [
        {"role": "user", "content": "My name is Brian McCleskey and I live in Indianapolis on the north side"},
        {"role": "assistant", "content": "Nice to meet you!"}
    ]

    print("\nTesting fact extraction with test messages...")
    print(f"User message: {test_messages[0]['content']}")

    result = memory.add(
        messages=test_messages,
        user_id="test_brian",
        infer=True
    )

    print(f"\n✓ Add completed")
    print(f"Result type: {type(result)}")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    print(f"Full result: {json.dumps(result, indent=2, default=str)}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
