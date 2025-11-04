# Pydantic AI Agent

A production-ready AI agent built with Pydantic AI, featuring long-term memory, observability, and safety guardrails.

## Features

- **🤖 Pydantic AI** - Type-safe AI agent framework
- **🧠 Long-term Memory** - Persistent memory via Mem0 with Qdrant vector database
- **📊 Observability** - Complete trace logging via Langfuse
- **🛡️ Safety Guardrails** - Content validation using Guardrails AI
- **🔒 Security** - Snyk MCP integration for security scanning
- **🏠 Local LLM** - Powered by self-hosted Ollama (llama3.1:8b)

## Architecture

```
┌─────────────────────────────────────────────────┐
│            Pydantic AI Agent                    │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Mem0    │  │ Langfuse │  │Guardrails│       │
│  │ Memory   │  │   Track  │  │   Check  │       │
│  └────┬─────┘  └────┬─────┘  └──────────┘       │
│       │             │                           │
└───────┼─────────────┼──────────────────────────-┘
        │             │
        ▼             ▼
   ┌─────────┐   ┌──────────┐
   │ Qdrant  │   │Langfuse  │
   │Vector DB│   │  Server  │
   └─────────┘   └──────────┘
                       │
                       ▼
                 ┌──────────┐
                 │PostgreSQL│
                 └──────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Ollama running at `ollama.brainiacs.technology` (or modify `.env`)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd pydantic-ai-agent
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Access Langfuse dashboard:**
   - Open http://localhost:4000
   - Create an account
   - Copy API keys to `.env`
   - Restart agent: `docker-compose restart agent`

5. **Start chatting:**
   ```bash
   docker-compose logs -f agent
   ```

   Or attach to the container:
   ```bash
   docker attach pydantic-agent
   ```

## System Prompt Templates

The agent comes with 5 pre-configured templates. Switch by setting `AGENT_PROMPT_TEMPLATE` in `.env`:

- **GENERAL_ASSISTANT** (default) - Versatile conversational agent
- **DATA_ANALYST** - Specialized in data analysis and insights
- **CODE_HELPER** - Programming assistance and code review
- **CUSTOMER_SUPPORT** - Customer service oriented
- **RESEARCH_ASSISTANT** - Research and information gathering

Example:
```bash
AGENT_PROMPT_TEMPLATE=CODE_HELPER
```

## Service URLs

- **Agent**: Running in Docker container
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Langfuse Dashboard**: http://localhost:4000

## Development

### Project Structure

```
pydantic-ai-agent/
├── agent/
│   ├── main.py           # Main application
│   ├── config.py         # Configuration management
│   ├── prompts.py        # System prompt templates
│   ├── utils.py          # Helper utilities
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile        # Agent container
├── docs/
│   └── SETUP.md          # Detailed setup guide
├── docker-compose.yml    # Multi-service orchestration
├── .env.example          # Environment template
└── README.md            # This file
```

### Local Development

Run the agent locally (without Docker):

```bash
cd agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Make sure Qdrant and Langfuse are running (via docker-compose)
docker-compose up -d qdrant langfuse-server langfuse-db

# Run agent
python main.py
```

### Adding Custom Tools

Extend the agent with custom tools in `main.py`:

```python
from pydantic_ai import RunContext

@self.agent.tool
async def custom_tool(ctx: RunContext[str], arg: str) -> str:
    """Your custom tool description"""
    # Tool implementation
    return result
```

## Configuration

Key environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://ollama.brainiacs.technology:11434` |
| `OLLAMA_MODEL` | Model to use | `llama3.2` |
| `AGENT_PROMPT_TEMPLATE` | System prompt template | `GENERAL_ASSISTANT` |
| `LANGFUSE_ENABLED` | Enable observability | `true` |
| `GUARDRAILS_ENABLED` | Enable safety checks | `true` |

See `.env.example` for complete list.

## Troubleshooting

**Agent can't connect to Ollama:**
- Verify Ollama is running: `curl http://ollama.brainiacs.technology:11434/api/tags`
- Check `OLLAMA_HOST` in `.env`

**Qdrant connection errors:**
- Ensure Qdrant is running: `docker-compose ps qdrant`
- Check logs: `docker-compose logs qdrant`

**Langfuse keys not working:**
- Access http://localhost:3000 and create/verify keys
- Ensure keys are correctly set in `.env`
- Restart agent after updating keys

## Security

This project uses:
- **Guardrails AI** for content validation
- **Snyk MCP** for dependency scanning (configure as needed)
- Local LLM (no data sent to external APIs)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Check [docs/SETUP.md](docs/SETUP.md) for detailed setup
- Review troubleshooting section above
- Open an issue on GitHub
