#!/usr/bin/env python3
"""Test mem0 fact extraction to debug the 'facts' key error"""

import sys
sys.path.append('/mnt/d/agent/agent')

from mem0 import Memory
import config

# Test with default mem0 prompts first
mem0_config_default = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": config.OLLAMA_MODEL,
            "ollama_base_url": config.OLLAMA_HOST,
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "dbname": config.POSTGRES_DB,
            "user": config.POSTGRES_USER,
            "password": config.POSTGRES_PASSWORD,
            "host": config.POSTGRES_HOST,
            "port": config.POSTGRES_PORT,
            "embedding_model_dims": 768,
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            "ollama_base_url": config.OLLAMA_HOST,
            "embedding_dims": 768,
        }
    },
}

print("=" * 80)
print("Testing mem0 with DEFAULT prompts...")
print("=" * 80)

try:
    memory_default = Memory.from_config(mem0_config_default)
    print("✓ Memory initialized with default prompts")

    # Test simple fact extraction
    test_messages = [
        {"role": "user", "content": "My name is Brian McCleskey and I live in Indianapolis"},
        {"role": "assistant", "content": "Nice to meet you!"}
    ]

    print("\nTesting fact extraction...")
    result = memory_default.add(
        messages=test_messages,
        user_id="test_user",
        infer=True
    )

    print(f"\n✓ Success! Result: {result}")
    print(f"  - Number of facts extracted: {len(result.get('results', []))}")
    for i, fact in enumerate(result.get('results', []), 1):
        print(f"  - Fact {i}: {fact}")

except Exception as e:
    print(f"\n✗ Error with default prompts: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Testing mem0 with CUSTOM prompts...")
print("=" * 80)

# Now test with custom prompts
CUSTOM_FACT_EXTRACTION_PROMPT = """You extract facts from the user line only. Extract ALL specific details separately.

IMPORTANT:
- Extract location details with full specificity (city, neighborhood, area, side of town)
- Break down compound statements into separate facts
- Preserve exact details like addresses, neighborhoods, districts
- Extract preferences, habits, and contextual information

OUTPUT FORMAT:
Return your response as valid JSON with the following structure:
{"facts": ["fact1", "fact2", ...]}

Format:
user: <user message>
assistant: <ignore this>

Extract facts from the user line only. Output must be valid JSON.
"""

mem0_config_custom = mem0_config_default.copy()
mem0_config_custom["custom_fact_extraction_prompt"] = CUSTOM_FACT_EXTRACTION_PROMPT

try:
    memory_custom = Memory.from_config(mem0_config_custom)
    print("✓ Memory initialized with custom prompts")

    print("\nTesting fact extraction...")
    result = memory_custom.add(
        messages=test_messages,
        user_id="test_user_2",
        infer=True
    )

    print(f"\n✓ Success! Result: {result}")
    print(f"  - Number of facts extracted: {len(result.get('results', []))}")
    for i, fact in enumerate(result.get('results', []), 1):
        print(f"  - Fact {i}: {fact}")

except Exception as e:
    print(f"\n✗ Error with custom prompts: {e}")
    import traceback
    traceback.print_exc()
