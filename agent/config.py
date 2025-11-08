"""
Configuration management for Pydantic AI Agent

Loads all configuration from environment variables.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""

    # Ollama Configuration
    OLLAMA_HOST: str = os.getenv('OLLAMA_HOST', 'http://192.168.1.97:11434')
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL', 'llama3.2')
    OLLAMA_TIMEOUT: int = int(os.getenv('OLLAMA_TIMEOUT', '120'))

    # PostgreSQL Configuration (for pgvector/Mem0)
    POSTGRES_HOST: str = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT: int = int(os.getenv('POSTGRES_PORT', '5432'))
    POSTGRES_DB: str = os.getenv('POSTGRES_DB', 'agent_memory')
    POSTGRES_USER: str = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', 'postgres')

    # Mem0 Configuration
    MEM0_USER_ID: str = os.getenv('MEM0_USER_ID', 'default_user')
    MEM0_AGENT_ID: str = os.getenv('MEM0_AGENT_ID', 'pydantic_agent')

    # Neo4j Configuration (for GraphRAG)
    NEO4J_URI: str = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USERNAME: str = os.getenv('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD: str = os.getenv('NEO4J_PASSWORD', 'password')
    NEO4J_DATABASE: str = os.getenv('NEO4J_DATABASE', 'neo4j')

    # OpenAI Configuration (for Graph Entity Extraction)
    OPENAI_GRAPH_API_KEY: str = os.getenv('OPENAI_GRAPH_API_KEY', '')

    # Langfuse Configuration
    LANGFUSE_HOST: str = os.getenv('LANGFUSE_BASE_URL', os.getenv('LANGFUSE_HOST', 'http://localhost:3000'))
    LANGFUSE_PUBLIC_KEY: Optional[str] = os.getenv('LANGFUSE_PUBLIC_KEY')
    LANGFUSE_SECRET_KEY: Optional[str] = os.getenv('LANGFUSE_SECRET_KEY')
    LANGFUSE_ENABLED: bool = os.getenv('LANGFUSE_ENABLED', 'true').lower() == 'true'

    # Guardrails AI Configuration
    GUARDRAILS_ENABLED: bool = os.getenv('GUARDRAILS_ENABLED', 'true').lower() == 'true'

    # Agent Configuration
    AGENT_PROMPT_TEMPLATE: str = os.getenv('AGENT_PROMPT_TEMPLATE', 'GENERAL_ASSISTANT')
    AGENT_NAME: str = os.getenv('AGENT_NAME', 'Pydantic AI Agent')
    AGENT_MAX_TOKENS: int = int(os.getenv('AGENT_MAX_TOKENS', '2048'))
    AGENT_TEMPERATURE: float = float(os.getenv('AGENT_TEMPERATURE', '0.7'))

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def validate(cls) -> bool:
        """
        Validate required configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        required_fields = [
            ('OLLAMA_HOST', cls.OLLAMA_HOST),
            ('OLLAMA_MODEL', cls.OLLAMA_MODEL),
        ]

        missing = []
        for name, value in required_fields:
            if not value:
                missing.append(name)

        if missing:
            print(f"Missing required configuration: {', '.join(missing)}")
            return False

        return True

    @classmethod
    def display(cls) -> None:
        """Display current configuration (masking sensitive values)"""
        print("\n=== Agent Configuration ===")
        print(f"Ollama Host: {cls.OLLAMA_HOST}")
        print(f"Ollama Model: {cls.OLLAMA_MODEL}")
        print(f"PostgreSQL: {cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}")
        print(f"Neo4j: {cls.NEO4J_URI}")
        print(f"Langfuse Enabled: {cls.LANGFUSE_ENABLED}")
        print(f"Guardrails Enabled: {cls.GUARDRAILS_ENABLED}")
        print(f"Prompt Template: {cls.AGENT_PROMPT_TEMPLATE}")
        print(f"Agent Name: {cls.AGENT_NAME}")
        print("===========================\n")


# Create a singleton instance
config = Config()
