# AI Agent with Memory and Location Context

A production-ready conversational AI agent featuring long-term memory via mem0ai GraphRAG, hybrid LLM architecture, streaming responses, and automatic location/timezone detection.

## Features

### Core Capabilities
- **🧠 Advanced Memory System** - mem0ai GraphRAG with vector storage (Milvus) and graph storage (Neo4j)
- **🔄 Hybrid LLM Architecture** - Ollama llama3.1:8b for chat + OpenAI GPT-4o-mini for structured extraction
- **🌍 IP Geolocation** - Automatic location and timezone detection via ipgeolocation.io
- **⚡ Streaming Responses** - Real-time chat with Server-Sent Events (SSE)
- **🎯 Custom Memory Prompts** - Preserves detailed user information with hundreds of extraction examples
- **🛡️ Anti-Hallucination** - Strict rules prevent fabrication of information not in memory
- **💬 Modern Chat Interface** - Next.js frontend with real-time streaming and message history
- **🐳 Docker Compose** - Complete multi-service orchestration

### Technical Stack
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI (Python), Pydantic for validation
- **Memory**: mem0ai with Milvus (vectors), Neo4j (graph), Ollama embeddings (nomic-embed-text)
- **LLMs**:
  - Ollama llama3.1:8b (conversational responses)
  - OpenAI GPT-4o-mini (fact/entity extraction, reliable JSON output)
- **Streaming**: Server-Sent Events (SSE) for real-time responses

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
│  │   Streaming  │ → │  Pydantic AI │ → │   mem0ai        │  │
│  │   Endpoint   │   │    Agent     │   │   GraphRAG      │  │
│  └──────────────┘   └──────────────┘   └────────┬────────┘  │
└─────────────────────────────────────────────────┼───────────┘
                                                   │
                     ┌─────────────────────────────┼──────────────────┐
                     │                             │                  │
                     ▼                             ▼                  ▼
            ┌────────────────┐          ┌──────────────────┐  ┌──────────────┐
            │     Milvus     │          │      Neo4j       │  │    Ollama    │
            │  Vector Store  │          │   Graph Store    │  │  llama3.1:8b │
            │  (embeddings)  │          │  (entities/rel)  │  │nomic-embed   │
            └────────────────┘          └──────────────────┘  └──────────────┘

            ┌────────────────┐
            │     OpenAI     │
            │  GPT-4o-mini   │
            │ (extraction)   │
            └────────────────┘
```

## Memory System

### mem0ai GraphRAG Integration
The agent uses **mem0ai** for sophisticated memory management:

- **Vector Storage (Milvus)**: Semantic search across conversation history
- **Graph Storage (Neo4j)**: Entity relationships and structured knowledge
- **Embeddings**: Ollama nomic-embed-text for vector representations
- **Custom Prompts**: 500+ examples for detailed fact extraction
- **Hybrid LLM**:
  - OpenAI GPT-4o-mini for reliable JSON-structured extraction
  - Ollama llama3.1:8b for conversational responses

### Memory Features
- **Persistent Context**: Remembers user preferences, facts, and conversations
- **Entity Extraction**: Automatically identifies people, places, dates, companies, etc.
- **Relationship Mapping**: Builds knowledge graph of connected information
- **Fact Consolidation**: Deduplicates and merges related memories
- **Temporal Context**: Tracks when information was learned

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (for fact extraction)
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
   # OpenAI (for fact/entity extraction)
   OPENAI_GRAPH_API_KEY=sk-proj-...

   # Ollama (for chat and embeddings)
   OLLAMA_HOST=http://ollama.brainiacs.technology:11434
   OLLAMA_MODEL=llama3.1:8b
   OLLAMA_EMBEDDING_MODEL=nomic-embed-text

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
   - Milvus vector database (port 19530)
   - Neo4j graph database (port 7687, UI on 7474)

4. **Access the chat interface:**
   - Open http://localhost:3000
   - Start chatting with memory-enabled AI agent

5. **Monitor services:**
   ```bash
   # View all logs
   docker-compose logs -f

   # View specific service
   docker-compose logs -f api
   docker-compose logs -f frontend
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
- Memory-aware context retrieval
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

## Memory Leak Prevention

Frontend optimizations to prevent excessive memory usage:

1. **Message Limit**: Keeps only last 100 messages (configurable via `MAX_MESSAGES`)
2. **Minimal Logging**: Removed excessive console.log statements from streaming code
3. **Auto-scroll Management**: Efficient DOM updates during streaming
4. **Ref-based Content**: Uses refs for streaming content to avoid unnecessary re-renders

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
│   ├── main.py             # Core agent logic with mem0ai
│   ├── api.py              # FastAPI endpoints
│   ├── config.py           # Environment configuration
│   ├── prompts.py          # System prompt templates
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
docker-compose up -d milvus neo4j

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

### Custom Memory Prompts

Customize fact extraction in `agent/main.py`:

```python
CUSTOM_FACT_EXTRACTION_PROMPT = """
Extract factual information from user messages.

Examples:
user: I work at Acme Corp in Boston
assistant: {"facts": ["works at Acme Corp", "located in Boston"]}

... (add your examples)
"""
```

The agent includes 500+ examples for comprehensive extraction of:
- Personal information (name, age, location, occupation)
- Relationships (family, friends, colleagues)
- Preferences (hobbies, food, entertainment)
- Temporal information (dates, schedules, routines)
- Contextual details (companies, places, projects)

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
| `OLLAMA_HOST` | Ollama server URL | `http://ollama.brainiacs.technology:11434` |
| `OLLAMA_MODEL` | Chat model | `llama3.1:8b` |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model | `nomic-embed-text` |
| `OPENAI_GRAPH_API_KEY` | OpenAI API key for extraction | Required |
| `AGENT_PROMPT_TEMPLATE` | System prompt template | `GENERAL_ASSISTANT` |
| `IP_GEOLOCATION_API_KEY` | Geolocation API key | Optional |
| `BACKEND_PORT` | FastAPI port | `8000` |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | `http://localhost:8000` |
| `MILVUS_HOST` | Milvus server | `localhost` |
| `MILVUS_PORT` | Milvus port | `19530` |
| `NEO4J_URL` | Neo4j connection | `bolt://localhost:7687` |

### Message Limit Configuration

Adjust frontend memory usage in `frontend/src/components/ChatInterface.tsx`:

```typescript
const MAX_MESSAGES = 100; // Change to desired limit
```

## Service URLs

- **Frontend Chat**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Neo4j Browser**: http://localhost:7474 (user: neo4j, pass: password)
- **Milvus**: localhost:19530 (via SDK only)

## Troubleshooting

### Agent Memory Not Working
- Check Milvus: `docker-compose logs milvus`
- Check Neo4j: `docker-compose logs neo4j`
- Verify collections: Access Neo4j browser at http://localhost:7474

### OpenAI API Errors
- Verify API key in `.env` is valid
- Check quota/billing at OpenAI dashboard
- Review logs: `docker-compose logs api | grep -i openai`

### Ollama Connection Errors
- Verify Ollama is running: `curl http://ollama.brainiacs.technology:11434/api/tags`
- Check models are available: llama3.1:8b, nomic-embed-text
- Update `OLLAMA_HOST` in `.env` if needed

### Frontend Not Loading
- Check Next.js logs: `docker-compose logs frontend`
- Verify `NEXT_PUBLIC_API_URL` matches backend location
- Clear browser cache and reload

### Streaming Issues
- Check CORS configuration in `agent/api.py`
- Monitor network tab for SSE connection
- Verify no proxy/firewall blocking streaming

### Memory Leak (Browser)
- Frontend keeps only last 100 messages (configurable)
- Close and reopen tab if memory usage is high
- Check for excessive browser extensions

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

Why two LLMs?

**Ollama llama3.1:8b (Local)**
- Conversational responses
- Privacy-focused (no data sent externally)
- Cost-effective (self-hosted)
- Fast inference

**OpenAI GPT-4o-mini (Cloud)**
- Structured JSON extraction
- Reliable fact/entity identification
- Complex reasoning for memory consolidation
- Strict format adherence

This hybrid approach balances privacy, cost, and reliability.

## Security Considerations

- **API Keys**: Store in `.env`, never commit to version control
- **Local LLM**: Main chat uses self-hosted Ollama (privacy-preserving)
- **OpenAI Usage**: Only for structured extraction (no full conversations sent)
- **CORS**: Configure allowed origins in `agent/api.py`
- **Environment Isolation**: All services run in Docker containers

## Performance Optimization

- **Streaming Responses**: SSE provides instant feedback (no waiting for full response)
- **Message Limits**: Prevents unbounded memory growth in frontend
- **Efficient Embeddings**: nomic-embed-text is lightweight and fast
- **Graph Storage**: Neo4j provides sub-millisecond relationship lookups
- **Vector Search**: Milvus optimized for high-dimensional similarity search

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Make your changes
4. Test thoroughly (chat, memory, streaming)
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check troubleshooting section above
- Review Docker logs: `docker-compose logs -f`

## Acknowledgments

- **mem0ai**: Powerful memory management framework
- **Pydantic AI**: Type-safe agent framework
- **Ollama**: Local LLM hosting
- **OpenAI**: Reliable structured extraction
- **Milvus**: High-performance vector database
- **Neo4j**: Graph database for relationships
- **Next.js**: Modern React framework
- **FastAPI**: Fast Python web framework
