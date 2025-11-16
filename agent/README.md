# Pydantic AI Agent with Hybrid Memory System

A conversational AI agent powered by Pydantic AI with an advanced hybrid memory architecture combining vector-based semantic search (mem0/pgvector) and temporal knowledge graphs (Graphiti/Neo4j).

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Memory System](#memory-system)
- [Memory Correction System](#memory-correction-system)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Known Issues & Workarounds](#known-issues--workarounds)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Features

### Core Capabilities
- **Conversational AI**: Natural language interactions powered by Ollama or OpenAI models
- **Hybrid Memory**: Best-of-both-worlds memory combining vector search and knowledge graphs
- **Automatic Memory Management**: Intelligent fact extraction from conversations
- **Memory Correction**: Advanced system for handling contradictions and updates
- **Temporal Awareness**: Track how information changes over time
- **Observability**: Integrated Langfuse support for monitoring and debugging

### Advanced Memory Features
- **Context-Aware Corrections**: Automatically infers context from previous messages
- **Contradiction Detection**: Identifies when users correct or negate previous information
- **Intelligent Fact Invalidation**: Marks outdated facts without deleting history
- **Duplicate Prevention**: Avoids creating redundant memories
- **Company Context Injection**: Enhances corrections with missing context

## Architecture

### Hybrid Memory System

```
┌─────────────────────────────────────────────────┐
│           Pydantic AI Agent (main.py)           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│      HybridMemoryManager (hybrid_memory.py)     │
│                                                  │
│  ┌──────────────────┐  ┌─────────────────────┐ │
│  │   mem0 (Vector)  │  │  Graphiti (Graph)   │ │
│  │                  │  │                     │ │
│  │  • Semantic      │  │  • Temporal facts   │ │
│  │    search        │  │  • Relationships    │ │
│  │  • Fast lookup   │  │  • Entity tracking  │ │
│  │  • pgvector      │  │  • Neo4j            │ │
│  └──────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
  ┌────────────┐            ┌──────────────┐
  │ PostgreSQL │            │    Neo4j     │
  │  +pgvector │            │   Graph DB   │
  └────────────┘            └──────────────┘
```

### Component Breakdown

#### 1. **mem0 (Vector Memory)**
- **Purpose**: Fast semantic search for recent context
- **Storage**: PostgreSQL with pgvector extension
- **Embedding**: Ollama `nomic-embed-text:latest` (768 dimensions)
- **LLM**: OpenAI GPT-4o-mini for fact extraction
- **Use Case**: Quick retrieval of relevant memories for conversation context

#### 2. **Graphiti (Knowledge Graph)**
- **Purpose**: Temporal knowledge representation with relationships
- **Storage**: Neo4j graph database
- **LLM**: OpenAI GPT-4o for entity extraction and relationship building
- **Embedding**: OpenAI `text-embedding-3-small`
- **Use Case**: Track how facts change over time, understand entity relationships

#### 3. **ContradictionHandler** (New)
- **Purpose**: Detect and handle memory corrections
- **Features**:
  - Detects negation patterns ("That's not correct", "I don't work at...")
  - Extracts topic keywords for targeted deletion
  - Invalidates contradicting facts in Graphiti
  - Context-aware message enhancement

## Quick Start

### Prerequisites

```bash
# Required services
- Docker & Docker Compose
- PostgreSQL with pgvector extension
- Neo4j database
- Ollama (for local LLM) OR OpenAI API key
```

### Installation

1. **Clone the repository**
```bash
cd /path/to/agent
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start services**
```bash
docker-compose up -d postgres-memory neo4j-memory
```

4. **Install dependencies**
```bash
pip install -r requirements.txt
```

5. **Run the agent**
```bash
# Via Docker
docker-compose up pydantic-api

# Or locally
python main.py
```

### Docker Deployment

```bash
# Build and run
docker-compose up --build

# API will be available at http://localhost:8000
```

## Memory System

### How Hybrid Memory Works

When you have a conversation:

1. **User Message** → Agent processes and responds
2. **Memory Storage**:
   - **mem0**: Extracts facts using custom prompts → Stores in pgvector
   - **Graphiti**: Creates episode → Extracts entities → Builds knowledge graph
3. **Search**: When answering questions, searches BOTH systems and combines results
4. **Context Building**: Creates unified context from vector + graph results

### Example Flow

```
You: "I work at Tesla as a senior engineer"
Agent: "Got it."

Memory Storage:
  mem0 → ["Works at Tesla", "Position: senior engineer"]
  Graphiti → Entity(User) -[WORKS_AT]-> Entity(Tesla)
               Entity(User) -[HAS_ROLE]-> "senior engineer"

You: "What's my job?"
Agent searches:
  mem0 → Finds "Works at Tesla", "Position: senior engineer"
  Graphiti → Finds relationships User->Tesla, User->senior engineer

Combined Context:
  - Works at Tesla
  - Position: senior engineer
  - User works at Tesla
  - User has the role of senior engineer

Agent: "You're a senior engineer at Tesla."
```

### Memory Correction

The system automatically handles corrections:

```
You: "I work at Tesla"
Agent: "Got it."

You: "That's not correct. I work at SpaceX"
Agent: "Got it."

Behind the scenes:
1. Detects correction pattern: "That's not correct"
2. Deletes mem0 memory: "Works at Tesla"
3. Invalidates Graphiti fact: User->Tesla (sets invalid_at timestamp)
4. Stores new fact: "Works at SpaceX"
5. Creates new Graphiti fact: User->SpaceX (with valid_at timestamp)
```

## Memory Correction System

### Problem Statement

**mem0 Bug**: When users correct information, mem0's fact extraction includes old memory as context, causing it to extract the old value instead of the new one.

**Example of the bug**:
```
You: "I work at Tesla"
mem0 stores: "Works at Tesla" ✓

You: "That's not correct. I work at SpaceX"
mem0 sees: Old memory: "Works at Tesla" + New message: "I work at SpaceX"
mem0 extracts: "Works at Tesla" ✗ (uses old value!)
```

### Solution: Multi-Layer Workaround

We implemented a comprehensive workaround with 4 key components:

#### 1. **Contradiction Detection** (`contradiction_handler.py`)

Detects correction patterns in user messages:

```python
NEGATION_PATTERNS = [
    r"(?:do not|don't|does not|doesn't|did not|didn't)\s+(.+)",
    r"(?:no longer|not anymore)\s+(.+)",
    r"(?:that's|that is)\s+(?:incorrect|wrong|not true|not correct|not right)",
    r"(?:actually|correction)[:,]?\s+(.+)",
    r"(?:my|the)\s+(?:role|position|job|title)\s+(?:at|with|for)\s+(.+)",
    # ... more patterns
]
```

#### 2. **Pre-emptive Memory Deletion** (`hybrid_memory.py:176-235`)

Before adding corrections, deletes conflicting mem0 memories:

```python
# Detect correction
if negation:
    # Extract keywords from correction
    keywords = extract_topic_keywords(negation)

    # Add context from previous user message
    if self._last_user_message:
        keywords += extract_topic_keywords(self._last_user_message)

    # Search and delete conflicting memories
    search_query = " ".join(keywords)
    memories = mem0.search(query=search_query, user_id=user_id)

    # Delete memories that match ALL keywords
    for memory in memories:
        if all(keyword in memory.lower() for keyword in keywords):
            mem0.delete(memory_id)
```

#### 3. **Context-Aware Message Enhancement** (`hybrid_memory.py:245-299`)

Injects missing context (like company names) into correction messages:

```python
# User asks: "What is my role at Mirazon?"
# User corrects: "That's not correct. My role is a consulting services systems engineer"

# Enhancement detects missing company context
# Enhances to: "That's not correct. My role at Mirazon is a consulting services systems engineer"

# mem0 now extracts: "Role at Mirazon: consulting services systems engineer" ✓
```

**How it works**:
1. Stores last user message in `self._last_user_message`
2. When correction detected, extracts company name from last message
3. Uses regex with `re.IGNORECASE` to inject company into correction
4. Sends enhanced message to mem0 for fact extraction

#### 4. **Graphiti Fact Invalidation** (`contradiction_handler.py:126-234`)

Marks outdated Graphiti facts as invalid (preserves history):

```python
# Search for contradicting facts
related_facts = graphiti.search(query=keywords)

for fact in related_facts:
    # Skip recently created facts (within 10 seconds)
    if fact.created_at > (now - 10 seconds):
        continue

    # Invalidate by setting invalid_at timestamp
    set_invalid_at(fact, timestamp=now)
```

### Correction Flow Example

```
Step 1: Initial Fact
You: "My role at Mirazon is systems engineer"
  mem0: "Role at Mirazon: systems engineer"
  Graphiti: User -[HAS_ROLE_AT]-> Mirazon ("systems engineer")

Step 2: User Corrects
You: "What is my role at Mirazon?"
Agent: "You are a systems engineer at Mirazon."
You: "That's not correct. My role is a consulting services systems engineer"

Step 3: Correction Processing
1. Detection: Pattern matches "That's not correct"
2. Context Extraction:
   - From correction: ["role", "engineer", "consulting", "services"]
   - From last message: ["mirazon"]
   - Combined: ["role", "engineer", "consulting", "services", "mirazon"]

3. Memory Deletion:
   - Search mem0 for ALL keywords
   - Delete: "Role at Mirazon: systems engineer" ✓

4. Message Enhancement:
   - Original: "My role is a consulting services systems engineer"
   - Enhanced: "My role at Mirazon is a consulting services systems engineer"

5. New Storage:
   mem0: "Role at Mirazon: consulting services systems engineer" ✓
   Graphiti: User -[HAS_ROLE_AT]-> Mirazon ("consulting services systems engineer") ✓

6. Invalidation:
   Graphiti: Old fact marked with invalid_at=<timestamp>

Step 4: Verification
You: "What is my role at Mirazon?"
Agent: "You are a consulting services systems engineer at Mirazon." ✓
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Ollama Configuration (for local LLM)
OLLAMA_HOST=http://192.168.1.97:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=120

# PostgreSQL Configuration (for mem0/pgvector)
POSTGRES_HOST=postgres-memory
POSTGRES_PORT=5432
POSTGRES_DB=agent_memory
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here

# Neo4j Configuration (for Graphiti)
NEO4J_URI=bolt://192.168.1.97:17687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
NEO4J_DATABASE=neo4j

# OpenAI Configuration (for Graphiti entity extraction and mem0)
OPENAI_GRAPH_API_KEY=sk-...your-key-here

# mem0 Configuration
MEM0_USER_ID=default_user
MEM0_AGENT_ID=pydantic_agent

# Langfuse Configuration (Optional - for observability)
LANGFUSE_ENABLED=true
LANGFUSE_BASE_URL=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...

# Agent Configuration
AGENT_NAME=Pydantic AI Agent
AGENT_MAX_TOKENS=2048
AGENT_TEMPERATURE=0.7
LOG_LEVEL=INFO
```

### Docker Compose Services

```yaml
services:
  postgres-memory:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_password
      POSTGRES_DB: agent_memory
    volumes:
      - postgres_data:/var/lib/postgresql/data

  neo4j-memory:
    image: neo4j:5.14.0
    ports:
      - "7474:7474"  # Web UI
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: neo4j/your_password
    volumes:
      - neo4j_data:/data

  pydantic-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres-memory
      - NEO4J_URI=bolt://neo4j-memory:7687
    depends_on:
      - postgres-memory
      - neo4j-memory
```

## API Reference

### FastAPI Endpoints

#### POST `/chat`

Send a message to the agent.

**Request**:
```json
{
  "message": "What is my role at Tesla?",
  "user_id": "brian_mccleskey"
}
```

**Response** (Streaming):
```
Server-Sent Events (SSE) stream:
data: {"type": "token", "content": "Your"}
data: {"type": "token", "content": " role"}
data: {"type": "token", "content": " at"}
data: {"type": "token", "content": " Tesla"}
...
data: {"type": "done"}
```

#### GET `/health`

Check API health status.

**Response**:
```json
{
  "status": "healthy",
  "memory_initialized": true,
  "timestamp": "2025-11-15T22:00:00Z"
}
```

### Python API

```python
from hybrid_memory import HybridMemoryManager

# Initialize
manager = HybridMemoryManager(
    mem0_config={...},
    neo4j_uri="bolt://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password",
    openai_api_key="sk-..."
)
await manager.initialize()

# Add conversation
await manager.add(
    messages=[
        {"role": "user", "content": "I work at Tesla"},
        {"role": "assistant", "content": "Got it."}
    ],
    user_id="user123"
)

# Search memory
results = await manager.search(
    query="Where do I work?",
    user_id="user123",
    limit=5
)

print(results['combined_context'])
# Output:
# [Previous Context]:
# - Works at Tesla
# - User works at Tesla as an engineer
```

## Known Issues & Workarounds

### 1. mem0 Correction Bug

**Issue**: mem0's fact extraction includes old memory as context, extracting old values during corrections.

**Status**: ✅ **WORKAROUND IMPLEMENTED**
- Pre-emptive deletion of conflicting memories
- Context-aware message enhancement
- See [Memory Correction System](#memory-correction-system)

**Tracking**: This is a known mem0 library issue. Workaround is stable and tested.

### 2. Graphiti Automatic Contradiction Detection

**Issue**: Graphiti's built-in contradiction detection doesn't work reliably.

**Status**: ✅ **REPLACED**
- Custom `ContradictionHandler` with regex-based pattern matching
- Manual fact invalidation with timestamps
- More reliable than automatic detection

### 3. Missing Company Context in Corrections

**Issue**: When users say "My role is X" after asking "What is my role at Company", mem0 doesn't capture the company name.

**Status**: ✅ **FIXED**
- Context enhancement injects company names from previous messages
- Stores last user message for context
- Uses `re.IGNORECASE` for reliable pattern matching

### 4. Over-Broad Keyword Matching

**Issue**: Early versions deleted too many memories (e.g., deleting both Mirazon and Brainiacs roles).

**Status**: ✅ **FIXED**
- Changed from ANY keyword match to ALL keywords match
- Combines context from previous messages
- More precise targeting of memories to delete

## Troubleshooting

### Agent doesn't remember corrections

**Symptoms**: After correcting information, agent still uses old value.

**Diagnosis**:
```bash
# Check if memory was actually updated
docker exec pydantic-api python -c "
from hybrid_memory import HybridMemoryManager
import asyncio

async def check():
    mgr = HybridMemoryManager(...)
    await mgr.initialize()
    result = await mgr.search('what is my role', user_id='your_user_id')
    print(result['combined_context'])

asyncio.run(check())
"
```

**Solution**:
1. Check logs for "Enhanced correction message" - should show context injection
2. Check logs for "Deleted N conflicting mem0 memories" - should be > 0
3. Verify pattern matches your phrasing in `contradiction_handler.py`

### Memory search returns no results

**Symptoms**: Agent says "I don't have that information"

**Causes**:
1. **Different user_id**: mem0 and Graphiti are user-scoped
2. **Invalid facts only**: Graphiti facts marked invalid won't appear
3. **Embedding mismatch**: Query doesn't semantically match stored facts

**Solution**:
```bash
# Check all memories for user
docker exec pydantic-api python -c "
from mem0 import Memory
mem = Memory.from_config({...})
all_mem = mem.get_all(user_id='your_user_id')
for m in all_mem['results']:
    print(m['memory'])
"
```

### Graphiti facts are all invalid

**Symptoms**: Search shows "Skipping INVALID graph fact" in logs.

**Cause**: Facts were invalidated during corrections but new facts weren't created.

**Solution**:
1. Check if mem0 extracted the fact: Look for "mem0 saved N memories" > 0
2. Check Graphiti episode creation: Look for "Completed add_episode"
3. If mem0 saved but Graphiti didn't create entities, check OpenAI API key

### Docker container crashes on startup

**Symptoms**: `pydantic-api` container exits immediately.

**Diagnosis**:
```bash
docker logs pydantic-api
```

**Common causes**:
1. **Missing environment variables**: Check `.env` file
2. **Database connection failed**: Ensure postgres-memory and neo4j-memory are running
3. **Port conflicts**: Check if port 8000 is already in use

**Solution**:
```bash
# Rebuild with fresh containers
docker-compose down -v
docker-compose up --build
```

## Development

### Project Structure

```
agent/
├── main.py                    # Main application entry point
├── api.py                     # FastAPI server
├── hybrid_memory.py           # Hybrid memory manager (mem0 + Graphiti)
├── contradiction_handler.py   # Correction detection and fact invalidation
├── config.py                  # Configuration management
├── prompts.py                 # System and custom prompts
├── utils.py                   # Utility functions
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker build instructions
├── docker-compose.yml         # Multi-service orchestration
└── README.md                  # This file
```

### Key Files

#### `hybrid_memory.py`
- `HybridMemoryManager`: Coordinates mem0 and Graphiti
- `add()`: Stores conversations in both systems
- `search()`: Queries both systems and combines results
- Context enhancement logic (lines 245-299)
- Pre-emptive deletion logic (lines 176-235)

#### `contradiction_handler.py`
- `detect_negation()`: Pattern matching for corrections
- `extract_topic_keywords()`: Extracts keywords for targeted search
- `invalidate_contradicting_facts()`: Marks Graphiti facts as invalid

#### `main.py`
- Custom fact extraction prompts for mem0
- Agent initialization and conversation loop
- Langfuse integration for observability

### Adding New Correction Patterns

Edit `contradiction_handler.py`:

```python
NEGATION_PATTERNS = [
    # ... existing patterns ...
    r"your_new_pattern_here",  # Add description
]
```

### Testing

```bash
# Run with verbose logging
LOG_LEVEL=DEBUG python main.py

# Test memory correction
python -c "
from contradiction_handler import ContradictionHandler

handler = ContradictionHandler(graphiti=None)
negation = handler.detect_negation('That is not correct. I work at SpaceX')
print(f'Detected negation: {negation}')

keywords = handler.extract_topic_keywords(negation)
print(f'Keywords: {keywords}')
"
```

### Monitoring

Use Langfuse for observability:

1. **Set up Langfuse**:
```bash
docker run -d -p 3000:3000 langfuse/langfuse
```

2. **Configure** in `.env`:
```bash
LANGFUSE_ENABLED=true
LANGFUSE_BASE_URL=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
```

3. **View traces** at `http://localhost:3000`
   - See all agent interactions
   - Track memory add/search operations
   - Debug correction handling

## Contributing

When contributing memory correction improvements:

1. **Test extensively** with various correction phrasings
2. **Add new patterns** to `NEGATION_PATTERNS` with comments
3. **Update logs** to show what's happening (aids debugging)
4. **Document** new workarounds in this README
5. **Preserve history** - use invalidation, not deletion

## License

[Your License Here]

## Support

For issues and questions:
- Check [Troubleshooting](#troubleshooting) section
- Review logs: `docker logs pydantic-api`
- File an issue with:
  - Correction input that failed
  - Relevant logs showing pattern matching
  - Expected vs actual behavior

---

**Last Updated**: November 15, 2025
**Version**: 1.0.0
**Contributors**: [Your Name/Team]
