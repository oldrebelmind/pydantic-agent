# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Pydantic AI agent with integrated long-term memory (Mem0), observability (Langfuse), and safety guardrails (Guardrails AI). The agent uses a locally-hosted Ollama LLM and runs in Docker containers.

## Architecture

### Core Components

1. **Pydantic AI Agent** (`agent/main.py`)
   - Main agent class: `PydanticAIAgent`
   - Uses OpenAI-compatible API to communicate with Ollama
   - Integrates all services (Mem0, Langfuse, Guardrails)
   - Runs async conversation loop

2. **Memory System** (Mem0 + Qdrant)
   - Mem0 provides the memory abstraction layer
   - Qdrant stores vectors for semantic search
   - Memories are user-specific (configurable via `MEM0_USER_ID`)
   - Automatically retrieves relevant context for each query

3. **Observability** (Langfuse)
   - Uses `@observe()` decorator on `process_message()` method
   - Tracks all LLM interactions, latency, and token usage
   - Optional - can be disabled via `LANGFUSE_ENABLED=false`

4. **Safety Guardrails** (Guardrails AI)
   - Validates both user input and agent responses
   - Currently configured with `ToxicLanguage` validator
   - Easy to add more validators from Guardrails Hub

5. **System Prompts** (`agent/prompts.py`)
   - Multiple pre-configured templates
   - Switchable via `AGENT_PROMPT_TEMPLATE` env var
   - All templates describe agent capabilities

### Service Dependencies

- **Ollama**: External, hosted at `ollama.brainiacs.technology:11434`
- **Qdrant**: In docker-compose, port 6333
- **Langfuse Server**: In docker-compose, port 3000
- **PostgreSQL**: Backend for Langfuse

## Development Commands

### Running the Agent

```bash
# Start all services
docker-compose up -d

# View agent logs
docker-compose logs -f agent

# Attach to agent for interactive chat
docker attach pydantic-agent

# Restart agent after code changes
docker-compose restart agent

# Rebuild after dependency changes
docker-compose up -d --build agent
```

### Local Development (without Docker)

```bash
cd agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ensure support services are running
docker-compose up -d qdrant langfuse-server langfuse-db

python main.py
```

### Testing Individual Components

```bash
# Test Ollama connection
curl http://ollama.brainiacs.technology:11434/api/tags

# Test Qdrant
curl http://localhost:6333/collections

# Access Langfuse UI
open http://localhost:3000
```

## Key Configuration

Configuration is managed via environment variables (`.env` file):

- **LLM**: Set `OLLAMA_MODEL` to change model (default: llama3.2)
- **Prompt**: Set `AGENT_PROMPT_TEMPLATE` to switch agent personality
- **Features**: Toggle `LANGFUSE_ENABLED` and `GUARDRAILS_ENABLED`

All config is loaded in `agent/config.py` via the `Config` class.

## Common Development Tasks

### Adding a New System Prompt Template

1. Add new prompt constant in `agent/prompts.py`
2. Add to `PROMPT_TEMPLATES` dictionary
3. Update `.env.example` with new option
4. Document in README.md

### Adding Custom Tools to the Agent

In `agent/main.py`, add tool methods to `PydanticAIAgent`:

```python
@self.agent.tool
async def tool_name(ctx: RunContext[str], arg: str) -> str:
    """Tool description for the LLM"""
    # Implementation
    return result
```

### Extending Guardrails Validators

In `_initialize_guardrails()` method:

```python
from guardrails.hub import SomeValidator

guard = Guard().use_many(
    ToxicLanguage(threshold=0.5),
    SomeValidator(config...),
)
```

### Modifying Memory Behavior

Memory configuration is in `_initialize_memory()`:
- Change vector store settings
- Adjust search limit (default: 3 memories)
- Modify metadata structure

### Adding Langfuse Tracing

Decorate any async function with `@observe()`:

```python
from langfuse.decorators import observe

@observe()
async def my_function():
    # Automatically traced
    pass
```

## Important Implementation Details

### Async/Await Pattern

- Main agent uses async/await throughout
- `agent.run()` is async and must be awaited
- Conversation loop is async: `run_conversation_loop()`

### Error Handling

- All integration initializations have try/except blocks
- If a service fails to initialize, it returns `None`
- Agent continues to function with degraded capabilities
- Errors are logged via Python logging

### Memory Context Injection

The agent automatically:
1. Searches memory for relevant context
2. Prepends context to user message
3. Sends combined message to LLM
4. Saves conversation turn to memory

### Ollama Integration

- Uses OpenAI-compatible endpoint (`/v1`)
- Requires dummy API key (set to "ollama")
- Base URL constructed from `OLLAMA_HOST`

## Docker Compose Services

- `agent`: Main Python application
- `qdrant`: Vector database (Mem0 backend)
- `langfuse-server`: Observability platform
- `langfuse-db`: PostgreSQL for Langfuse

All services connected via `agent-network` bridge network.

## Testing Notes

When making changes:
1. For Python code changes: `docker-compose restart agent`
2. For dependency changes: `docker-compose up -d --build agent`
3. For config changes: Update `.env` then restart
4. Always check logs: `docker-compose logs -f agent`

## Troubleshooting Development Issues

**Import errors**: Rebuild container after adding dependencies
**Qdrant connection refused**: Ensure Qdrant is running and healthy
**Langfuse 401 errors**: Verify API keys in `.env` match dashboard
**Ollama timeout**: Check `OLLAMA_HOST` and network connectivity
