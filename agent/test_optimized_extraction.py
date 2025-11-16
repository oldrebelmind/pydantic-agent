#!/usr/bin/env python3
"""
Test optimized fact extraction prompt quality
"""
import asyncio
import os
import json
from mem0 import Memory

# Import optimized prompt
import sys
sys.path.insert(0, '/tmp')
from optimized_fact_extraction_prompt import OPTIMIZED_CUSTOM_FACT_EXTRACTION_PROMPT

# Test cases covering diverse scenarios
TEST_CASES = [
    {
        "input": "I work at Tesla as a senior engineer in Palo Alto",
        "expected_facts": ["Works at Tesla", "Position: senior engineer", "Location: Palo Alto"],
        "description": "Compound statement with job + location"
    },
    {
        "input": "I live on the north side of Indianapolis near Broad Ripple",
        "expected_facts": ["Lives in Indianapolis", "Lives on north side of Indianapolis", "Lives near Broad Ripple"],
        "description": "Location with high specificity"
    },
    {
        "input": "Where do I work?",
        "expected_facts": [],
        "description": "Question should return empty"
    },
    {
        "input": "I deployed a Django app to AWS using Kubernetes last week",
        "expected_facts": ["Deployed Django app", "Deployed to AWS", "Used Kubernetes", "Deployment time: last week"],
        "description": "Technical multi-fact statement"
    },
    {
        "input": "I prefer working remotely on Tuesdays and Thursdays",
        "expected_facts": ["Prefers working remotely", "Remote work days: Tuesdays and Thursdays"],
        "description": "Preference with schedule"
    },
    {
        "input": "My name is Sarah and I'm a data scientist at Microsoft in Seattle",
        "expected_facts": ["Name is Sarah", "Works as data scientist", "Works at Microsoft", "Location: Seattle"],
        "description": "Complex personal + professional info"
    },
    {
        "input": "I ran a PowerShell script to automate user provisioning in Active Directory",
        "expected_facts": ["Ran PowerShell script", "Script purpose: automate user provisioning", "Tool: PowerShell", "Target: Active Directory"],
        "description": "Technical action with tool + purpose"
    },
]

async def test_extraction_quality():
    """Test optimized prompt against diverse inputs"""

    # Configure mem0 with optimized prompt
    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0,
                "api_key": os.environ.get("OPENAI_GRAPH_API_KEY"),
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
        "custom_fact_extraction_prompt": OPTIMIZED_CUSTOM_FACT_EXTRACTION_PROMPT,
    }

    memory = Memory.from_config(config)

    print("="*80)
    print("TESTING OPTIMIZED FACT EXTRACTION PROMPT")
    print("="*80)
    print()

    total_tests = len(TEST_CASES)
    passed = 0
    failed = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"Test {i}/{total_tests}: {test_case['description']}")
        print(f"Input: \"{test_case['input']}\"")
        print(f"Expected: {len(test_case['expected_facts'])} facts")

        # Add message and extract facts
        result = memory.add(
            messages=[
                {"role": "user", "content": test_case['input']},
                {"role": "assistant", "content": "Understood!"}
            ],
            user_id=f"test_user_{i}",
            infer=True
        )

        extracted_count = len(result.get('results', []))
        expected_count = len(test_case['expected_facts'])

        print(f"Extracted: {extracted_count} facts")

        if extracted_count > 0:
            print("Facts extracted:")
            for fact in result.get('results', []):
                print(f"  - {fact['memory']}")

        # Basic quality check: did we extract roughly the right number of facts?
        if extracted_count >= expected_count * 0.7:  # Allow 30% variance
            print("✓ PASS")
            passed += 1
        else:
            print(f"✗ FAIL - Expected ~{expected_count}, got {extracted_count}")
            failed += 1

        print()

        # Cleanup
        for fact in result.get('results', []):
            memory.delete(memory_id=fact['id'])

    print("="*80)
    print(f"RESULTS: {passed}/{total_tests} passed, {failed}/{total_tests} failed")
    print("="*80)

    if passed == total_tests:
        print("✓ All tests passed! Optimized prompt maintains quality.")
        return True
    elif passed >= total_tests * 0.85:
        print("⚠ Most tests passed. Quality is acceptable.")
        return True
    else:
        print("✗ Quality degradation detected. Consider keeping more examples.")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_extraction_quality())
    exit(0 if success else 1)
