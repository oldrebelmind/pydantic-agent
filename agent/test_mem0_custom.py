#!/usr/bin/env python3
"""Test mem0 with custom prompts to find the issue"""

from mem0 import Memory
import json

CUSTOM_FACT_EXTRACTION_PROMPT = """You extract facts from the user line only. Extract ALL specific details separately.

IMPORTANT:
- Extract location details with full specificity (city, neighborhood, area, side of town)
- Break down compound statements into separate facts

OUTPUT FORMAT:
Return your response as valid JSON with the following structure:
{"facts": ["fact1", "fact2", ...]}

Format:
user: <user message>
assistant: <ignore this>

Extract facts from the user line only. Output must be valid JSON.
"""

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
    "custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT,
}

print("=" * 80)
print("Testing mem0 with CUSTOM prompts...")
print("=" * 80)

try:
    memory = Memory.from_config(mem0_config)
    print("✓ Memory initialized with custom prompt")

    # Test simple fact extraction
    test_messages = [
        {"role": "user", "content": "My name is Brian McCleskey and I live in Indianapolis on the north side"},
        {"role": "assistant", "content": "Nice to meet you!"}
    ]

    print("\nTesting fact extraction...")
    print(f"User message: {test_messages[0]['content']}")

    result = memory.add(
        messages=test_messages,
        user_id="test_brian_custom",
        infer=True
    )

    print(f"\n✓ Add completed")
    print(f"Result: {json.dumps(result, indent=2, default=str)}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
