# AI Agent with Hybrid Memory and Location Context

A production-ready conversational AI agent featuring **hybrid long-term memory** (mem0 + Graphiti), advanced Graph RAG capabilities, streaming responses, and automatic location/timezone detection.

## Features

### Core Capabilities
- **🧠 Hybrid Memory System** - Combines mem0 (vector) + Graphiti (knowledge graph) for comprehensive memory
- **🔗 Graph RAG** - Multi-entity relationships, temporal queries, and multi-hop inference
- **🔄 Hybrid LLM Architecture** - Ollama llama3.1:8b for chat + OpenAI GPT-4o-mini for structured extraction
- **🌍 IP Geolocation** - Automatic location and timezone detection via ipgeolocation.io
- **⚡ Streaming Responses** - Real-time chat with Server-Sent Events (SSE)
- **🎯 Custom Memory Prompts** - 500+ examples for detailed, granular fact extraction
- **🛡️ Anti-Hallucination** - Strict rules prevent fabrication of information not in memory
- **💬 Modern Chat Interface** - Next.js frontend with real-time streaming and message history
- **🐳 Docker Compose** - Complete multi-service orchestration
- **📊 Observability** - Langfuse integration for LLM tracing and analytics

### Technical Stack
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI (Python), Pydantic AI for agent framework
- **Memory (Hybrid)**:
  - **mem0** - Vector storage with PostgreSQL (pgvector) + Ollama embeddings (nomic-embed-text)
  - **Graphiti** - Knowledge graph with Neo4j + OpenAI embeddings (text-embedding-3-small)
- **LLMs**:
  - Ollama llama3.1:8b (conversational responses)
  - OpenAI GPT-4o-mini (fact/entity extraction, graph reasoning)
- **Streaming**: Server-Sent Events (SSE) for real-time responses
- **Observability**: Langfuse for LLM tracing, token usage, and performance monitoring

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                        │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │ChatInterface │ → │  Streaming   │ → │   Geolocation   │  │
│  │  Component   │   │  SSE Client  │   │   Detection     │  │
│  └──────────────┘   └──────────────┘   └─────────────────┘  │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP/SSE
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │   Streaming  │ → │  Pydantic AI │ → │Hybrid Memory    │  │
│  │   Endpoint   │   │    Agent     │   │  Manager        │  │
│  └──────────────┘   └──────────────┘   └────────┬────────┘  │
└─────────────────────────────────────────────────┼───────────┘
                                                   │
                  ┌────────────────────────────────┼────────────────┐
                  │                                │                │
                  ▼                                ▼                ▼
         ┌────────────────┐              ┌──────────────────┐  ┌──────────────┐
         │   PostgreSQL   │              │      Neo4j       │  │   Langfuse   │
         │   (pgvector)   │              │  (Graphiti)      │  │ (Tracing)    │
         │  Vector Store  │              │  Knowledge Graph │  └──────────────┘
         └────────┬───────┘              └──────────┬───────┘
                  │                                 │
                  │ embeddings                      │ embeddings + LLM
                  ▼                                 ▼
         ┌────────────────┐              ┌──────────────────┐
         │     Ollama     │              │     OpenAI       │
         │  llama3.1:8b   │              │   GPT-4o-mini    │
         │ nomic-embed    │              │ text-embed-3-sm  │
         └────────────────┘              └──────────────────┘

         mem0 (Vector)                   Graphiti (Graph)
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              HYBRID MEMORY SYSTEM
```

## Hybrid Memory System

### Architecture Overview
The agent uses a **hybrid dual-memory architecture** combining the strengths of both vector and graph-based storage:

#### mem0 (Vector Memory)
- **Storage**: PostgreSQL with pgvector extension
- **Embeddings**: Ollama nomic-embed-text (768 dimensions)
- **LLM**: OpenAI GPT-4o-mini for fact extraction
- **Purpose**: Semantic search, fuzzy matching, general recall
- **Custom Prompts**: 500+ examples for granular fact extraction

#### Graphiti (Knowledge Graph)
- **Storage**: Neo4j graph database
- **Embeddings**: OpenAI text-embedding-3-small
- **LLM**: OpenAI GPT-4o for entity/relationship extraction
- **Purpose**: Entity relationships, temporal reasoning, multi-hop queries
- **Capabilities**:
  - Entity extraction and deduplication
  - Relationship mapping
  - Temporal awareness
  - Community detection
  - Multi-hop traversal

### Graph RAG Capabilities

The hybrid system enables advanced **Graph RAG** (Retrieval-Augmented Generation) queries:

1. **Multi-Entity Relationship Queries**
   - "What does the company I work for specialize in?"
   - Traverses: User → Company → Specialization

2. **Temporal Knowledge Retrieval**
   - "What was my previous setup before X?"
   - Leverages Graphiti's temporal awareness

3. **Multi-Hop Inference**
   - "What language do I use for my main work focus?"
   - Chains: Work focus → Project → Framework → Language

4. **Hybrid Vector + Graph**
   - Combines semantic similarity (mem0) with structured knowledge (Graphiti)
   - Returns comprehensive, contextually-rich results

### Memory Features
- **Persistent Context**: Remembers user preferences, facts, and conversations
- **Dual Storage**: Vector (semantic) + Graph (structured)
- **Entity Extraction**: Automatically identifies people, places, dates, companies, tools
- **Relationship Mapping**: Builds knowledge graph of connected information
- **Fact Consolidation**: Deduplicates and merges related memories
- **Temporal Context**: Tracks when information was learned
- **Granular Facts**: Breaks down compound statements into atomic facts
- **Location Preservation**: Maintains detailed location specificity (e.g., "north side of Indianapolis")

### Custom Memory Prompts

The system uses carefully crafted prompts with 500+ examples for:

**CUSTOM_FACT_EXTRACTION_PROMPT** (27,680 characters)
- Extracts facts from user messages only (not assistant)
- Returns JSON: `{"facts": ["fact1", "fact2", ...]}`
- Breaks down compound statements
- Preserves location details with full specificity
- Extracts personal info, preferences, actions, tools, dates, times

**CUSTOM_UPDATE_MEMORY_PROMPT** (6,411 characters)
- Manages 4 operations: ADD, UPDATE, DELETE, NONE
- **Critical rule**: ALWAYS keep facts with MORE specificity
- Never simplifies location information
- Examples show preservation of detailed facts

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (for fact extraction and graph reasoning)
- IP Geolocation API key (optional - free tier available)
- Ollama server with llama3.1:8b and nomic-embed-text models

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd agent
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

   Required variables in `.env`:
   ```bash
   # OpenAI (for fact extraction, graph reasoning, embeddings)
   OPENAI_GRAPH_API_KEY=sk-proj-...

   # Ollama (for chat and embeddings)
   OLLAMA_HOST=http://192.168.1.97:11434
   OLLAMA_MODEL=llama3.1:8b
   OLLAMA_EMBEDDING_MODEL=nomic-embed-text

   # Neo4j (Graphiti knowledge graph)
   NEO4J_URI=bolt://192.168.1.97:17687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=password123

   # PostgreSQL (mem0 vector store)
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=agent_memory
   POSTGRES_HOST=postgres-memory
   POSTGRES_PORT=5432

   # Langfuse (observability - optional)
   LANGFUSE_ENABLED=true
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com

   # IP Geolocation (optional)
   IP_GEOLOCATION_API_KEY=your_key_here

   # API
   BACKEND_PORT=8000

   # Frontend
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

   This starts:
   - FastAPI backend (port 8000)
   - Next.js frontend (port 3000)
   - PostgreSQL with pgvector (port 5432)
   - Neo4j graph database (port 7687, UI on 7474)
   - Langfuse (if enabled)

4. **Access the chat interface:**
   - Open http://localhost:3000
   - Start chatting with the hybrid memory-enabled AI agent

5. **Monitor services:**
   ```bash
   # View all logs
   docker-compose logs -f

   # View specific service
   docker-compose logs -f pydantic-api
   docker-compose logs -f frontend
   docker-compose logs -f postgres-memory
   docker-compose logs -f neo4j
   ```

## API Endpoints

### Health Check
```bash
GET /api/health
```
Returns service status and readiness.

### Streaming Chat
```bash
POST /api/chat/stream
Content-Type: application/json

{
  "message": "What's my name?",
  "location": {
    "city": "Indianapolis",
    "state": "Indiana",
    "country": "United States",
    "timezone": "America/Indiana/Indianapolis",
    "latitude": 39.7684,
    "longitude": -86.1581
  }
}
```

Returns Server-Sent Events stream:
```
data: {"token": "Your"}
data: {"token": " name"}
data: {"token": " is"}
data: {"token": " Brian"}
data: {"done": true}
```

Location context is optional but enables timezone-aware responses.

## System Prompt Templates

The agent comes with 5 pre-configured personality templates. Switch by setting `AGENT_PROMPT_TEMPLATE` in `.env`:

- **GENERAL_ASSISTANT** (default) - Versatile conversational agent with memory
- **DATA_ANALYST** - Specialized in data analysis and insights
- **CODE_HELPER** - Programming assistance and code review
- **CUSTOMER_SUPPORT** - Customer service with history tracking
- **RESEARCH_ASSISTANT** - Research and information gathering

Example:
```bash
AGENT_PROMPT_TEMPLATE=CODE_HELPER
```

All templates include:
- Hybrid memory-aware context retrieval
- Anti-hallucination rules
- Timezone/location awareness
- Personalized greetings using remembered names

## Anti-Hallucination Features

The agent implements strict rules to prevent fabricating information:

1. **Explicit Memory Boundaries**: Only uses information from `[Previous Context]` section
2. **Admission of Uncertainty**: States "I don't have that information" when memory is empty
3. **No Inference**: Never guesses or infers details not explicitly stored
4. **Specific Detail Prevention**: Won't make up company names, locations, dates, people, etc.
5. **Source Attribution**: All facts traceable to actual stored memories

Example behavior:
```
User: "Where do I work?"
Agent with empty memory: "I don't have that information stored in my memory."
Agent with memory: "You work at Company X in Indianapolis." [only if explicitly stored]
```

## Testing

### Graph RAG Test Suite

Comprehensive test suite verifies hybrid memory capabilities:

```bash
# Run full Graph RAG test suite
docker exec pydantic-api python /app/test_graph_rag.py

# Or use the v2 version with custom prompts
docker exec pydantic-api python /app/test_graph_rag_v2.py
```

**Test Coverage:**
1. **Multi-Entity Relationship Queries** - Complex queries across company, project, location, team
2. **Temporal Knowledge Retrieval** - Time-sequenced information and historical queries
3. **Multi-Hop Inference** - Reasoning across multiple relationship hops
4. **Hybrid Vector + Graph Combination** - Verifies both systems work together

**Sample Test Results:**
- ✓ 33 total memories extracted
- ✓ 46 ADD events (granular fact extraction)
- ✓ 5 vector + 5 graph results per query
- ✓ Successfully combining both memory systems

### Test Utilities

```bash
# Clean test data from Neo4j
docker exec pydantic-api python /tmp/clean_test_data.py

# Clean test memories from PostgreSQL
docker exec pydantic-api python -c "
from mem0 import Memory
m = Memory.from_config(config)
for mem in m.get_all(user_id='test_user').get('results', []):
    m.delete(memory_id=mem['id'])
"
```

## Development

### Project Structure

```
agent/
├── frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/            # Next.js app directory
│   │   ├── components/     # React components
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── StreamingMessage.tsx
│   │   └── lib/            # Utilities
│   │       ├── streaming.ts      # SSE client
│   │       └── geolocation.ts    # IP geolocation
│   ├── package.json
│   └── Dockerfile
├── agent/                   # FastAPI backend
│   ├── main.py             # Core agent logic with hybrid memory
│   ├── hybrid_memory.py    # Hybrid memory manager (mem0 + Graphiti)
│   ├── api.py              # FastAPI endpoints
│   ├── config.py           # Environment configuration
│   ├── prompts.py          # System prompt templates
│   ├── test_graph_rag.py   # Graph RAG test suite
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
├── docker-compose.yml      # Service orchestration
├── .env                    # Environment variables
└── README.md              # This file
```

### Local Development (Backend)

Run backend locally without Docker:

```bash
cd agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ensure supporting services are running
docker-compose up -d postgres-memory neo4j

# Run FastAPI server
python api.py
```

Backend runs on http://localhost:8000

### Local Development (Frontend)

Run frontend locally without Docker:

```bash
cd frontend

# Install dependencies
npm install

# Set API URL
export NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server
npm run dev
```

Frontend runs on http://localhost:3000

### Hybrid Memory Manager

The `HybridMemoryManager` class in `hybrid_memory.py` coordinates both memory systems:

```python
from hybrid_memory import HybridMemoryManager

# Initialize
manager = HybridMemoryManager(
    mem0_config=mem0_config,      # Vector store config
    neo4j_uri=neo4j_uri,          # Graph database URI
    neo4j_username=username,
    neo4j_password=password,
    openai_api_key=api_key
)
await manager.initialize()

# Add conversation (stores in both mem0 and Graphiti)
result = await manager.add(
    messages=[
        {"role": "user", "content": "I work at Tesla in Palo Alto"},
        {"role": "assistant", "content": "That's a great company!"}
    ],
    user_id="user123",
    agent_id="agent1"
)

# Search (queries both systems and combines results)
results = await manager.search(
    query="where does user work",
    user_id="user123",
    limit=5
)

# Results include both vector and graph facts
print(results['combined_context'])
```

### Custom Memory Prompts

The custom prompts in `agent/main.py` are carefully designed for comprehensive extraction:

```python
CUSTOM_FACT_EXTRACTION_PROMPT = """
CRITICAL: You MUST return ONLY this exact JSON structure:
{"facts": ["fact1", "fact2", ...]}

Extract facts from the user message. Each fact should be separate.

RULES:
1. ALWAYS include the "facts" key - even if empty: {"facts": []}
2. Extract location details with full specificity (city, neighborhood, area)
3. Break down compound statements into separate facts
4. Extract personal info, preferences, actions, tools, dates, times
5. User questions return empty array: {"facts": []}

Examples:
user: I work at Tesla as a senior engineer in Palo Alto
{"facts": ["Works at Tesla", "Position: senior engineer", "Location: Palo Alto"]}

... (500+ more examples)
"""
```

### Adding Custom Tools

Extend agent capabilities in `agent/main.py`:

```python
from pydantic_ai import RunContext

@agent.tool
async def custom_tool(ctx: RunContext[Dependencies], arg: str) -> str:
    """Tool description for the LLM"""
    # Implementation
    return result
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://192.168.1.97:11434` |
| `OLLAMA_MODEL` | Chat model | `llama3.1:8b` |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model | `nomic-embed-text` |
| `OPENAI_GRAPH_API_KEY` | OpenAI API key | Required |
| `NEO4J_URI` | Neo4j connection | `bolt://192.168.1.97:17687` |
| `NEO4J_USERNAME` | Neo4j user | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | Required |
| `POSTGRES_HOST` | PostgreSQL host | `postgres-memory` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | PostgreSQL user | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | Required |
| `POSTGRES_DB` | Database name | `agent_memory` |
| `LANGFUSE_ENABLED` | Enable observability | `true` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | Optional |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | Optional |
| `AGENT_PROMPT_TEMPLATE` | System prompt template | `GENERAL_ASSISTANT` |
| `IP_GEOLOCATION_API_KEY` | Geolocation API key | Optional |
| `BACKEND_PORT` | FastAPI port | `8000` |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | `http://localhost:8000` |

### Message Limit Configuration

Adjust frontend memory usage in `frontend/src/components/ChatInterface.tsx`:

```typescript
const MAX_MESSAGES = 100; // Change to desired limit
```

## Service URLs

- **Frontend Chat**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Neo4j Browser**: http://localhost:7474 (user: neo4j, pass: password123)
- **PostgreSQL**: localhost:5432 (via psql or client)
- **Langfuse Dashboard**: https://cloud.langfuse.com (if enabled)

## Troubleshooting

### Hybrid Memory Not Working
- Check PostgreSQL: `docker-compose logs postgres-memory`
- Check Neo4j: `docker-compose logs neo4j`
- Verify pgvector extension: `docker exec postgres-memory psql -U postgres -d agent_memory -c "SELECT * FROM pg_extension WHERE extname='vector';"`
- Access Neo4j browser: http://localhost:7474
- Check Graphiti indices: Run test suite to verify

### OpenAI API Errors
- Verify API key in `.env` is valid
- Check quota/billing at OpenAI dashboard
- Review logs: `docker-compose logs pydantic-api | grep -i openai`
- Ensure both GPT-4o-mini and text-embedding-3-small are available

### Ollama Connection Errors
- Verify Ollama is running: `curl http://192.168.1.97:11434/api/tags`
- Check models are available: llama3.1:8b, nomic-embed-text
- Update `OLLAMA_HOST` in `.env` if needed
- Pull models: `ollama pull llama3.1:8b && ollama pull nomic-embed-text`

### Frontend Not Loading
- Check Next.js logs: `docker-compose logs frontend`
- Verify `NEXT_PUBLIC_API_URL` matches backend location
- Clear browser cache and reload

### Streaming Issues
- Check CORS configuration in `agent/api.py`
- Monitor network tab for SSE connection
- Verify no proxy/firewall blocking streaming

### Memory Extraction Issues
- Check if custom prompts are loaded: `docker-compose logs pydantic-api | grep "custom_fact_extraction_prompt"`
- Should see: `Has custom_fact_extraction_prompt: True`
- Run test suite to verify: `docker exec pydantic-api python /app/test_graph_rag_v2.py`
- Check for `event='ADD'` in logs (not `event='NONE'` for new facts)

### Neo4j Performance
- Verify indices are created: Check Neo4j browser → Database Information
- Run `CALL db.indexes()` in Neo4j browser
- Check Graphiti initialization logs for index creation

## IP Geolocation

The system automatically detects user location and timezone:

1. **Frontend Detection**: Calls ipgeolocation.io API on component mount
2. **Context Passing**: Sends location data with each chat message
3. **Agent Integration**: Agent receives timezone-aware context
4. **Smart Responses**: Only mentions time/location when relevant

To disable geolocation:
- Remove `IP_GEOLOCATION_API_KEY` from `.env`
- Agent will work without location context

## Hybrid LLM Architecture

Why multiple LLMs?

**Ollama llama3.1:8b (Local)**
- Conversational responses
- Privacy-focused (no data sent externally)
- Cost-effective (self-hosted)
- Fast inference
- Vector embeddings (nomic-embed-text)

**OpenAI GPT-4o-mini (Cloud)**
- Structured JSON extraction (mem0)
- Entity/relationship extraction (Graphiti)
- Complex reasoning for memory consolidation
- Strict format adherence
- Graph reasoning capabilities

**OpenAI text-embedding-3-small (Cloud)**
- High-quality embeddings for Graphiti
- Semantic search in knowledge graph
- Entity similarity matching

This hybrid approach balances privacy, cost, performance, and reliability.

## Observability with Langfuse

Langfuse provides comprehensive LLM tracing and analytics:

### Features
- **Request Tracing**: Track every LLM call with timing, tokens, cost
- **Memory Operations**: Monitor fact extraction, entity creation
- **Graph Operations**: Observe Graphiti entity/relationship creation
- **Performance Metrics**: Latency, token usage, error rates
- **Cost Tracking**: Per-user, per-session cost analysis

### Setup
1. Sign up at https://cloud.langfuse.com
2. Create new project and get API keys
3. Add to `.env`:
   ```bash
   LANGFUSE_ENABLED=true
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
4. View traces in Langfuse dashboard

### What's Tracked
- Agent chat completions
- Memory fact extraction
- Entity/relationship creation
- Token usage (input/output)
- Response latency
- Error traces

## Security Considerations

- **API Keys**: Store in `.env`, never commit to version control
- **Local LLM**: Main chat uses self-hosted Ollama (privacy-preserving)
- **OpenAI Usage**: Only for structured extraction and graph reasoning
- **CORS**: Configure allowed origins in `agent/api.py`
- **Environment Isolation**: All services run in Docker containers
- **Database Security**: PostgreSQL and Neo4j passwords in environment variables
- **Network Isolation**: Services communicate via Docker network

## Performance Optimization

- **Streaming Responses**: SSE provides instant feedback (no waiting for full response)
- **Message Limits**: Prevents unbounded memory growth in frontend
- **Efficient Embeddings**:
  - nomic-embed-text (768d) for mem0 - lightweight and fast
  - text-embedding-3-small for Graphiti - high quality
- **Graph Storage**: Neo4j provides sub-millisecond relationship lookups
- **Vector Search**: pgvector optimized for high-dimensional similarity search
- **Hybrid Retrieval**: Parallel queries to both mem0 and Graphiti
- **Custom Prompts**: Optimized for minimal tokens while maximizing extraction quality

## Memory Leak Prevention

Frontend optimizations to prevent excessive memory usage:

1. **Message Limit**: Keeps only last 100 messages (configurable via `MAX_MESSAGES`)
2. **Minimal Logging**: Removed excessive console.log statements from streaming code
3. **Auto-scroll Management**: Efficient DOM updates during streaming
4. **Ref-based Content**: Uses refs for streaming content to avoid unnecessary re-renders

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Make your changes
4. Test thoroughly (chat, memory, streaming, graph queries)
5. Run test suite: `docker exec pydantic-api python /app/test_graph_rag.py`
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check troubleshooting section above
- Review Docker logs: `docker-compose logs -f`
- Run test suite to verify setup

## Acknowledgments

- **mem0ai**: Powerful memory management framework
- **Graphiti**: Advanced knowledge graph for temporal reasoning
- **Pydantic AI**: Type-safe agent framework
- **Ollama**: Local LLM hosting
- **OpenAI**: Reliable structured extraction and embeddings
- **PostgreSQL + pgvector**: High-performance vector database
- **Neo4j**: Graph database for knowledge relationships
- **Langfuse**: LLM observability and tracing
- **Next.js**: Modern React framework
- **FastAPI**: Fast Python web framework
