"""
Pydantic AI Agent with Mem0, Langfuse, and Guardrails AI

Main application entry point.
"""
import asyncio
from typing import Optional
import httpx
from pydantic_ai import Agent
try:
    from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
except ImportError:
    from pydantic_ai.models.openai import OpenAIModel

# Mem0 for long-term memory
from mem0 import Memory

# Langfuse for observability
from langfuse import Langfuse
try:
    from langfuse.decorators import observe
except ImportError:
    # Langfuse 3.x compatibility
    from langfuse import observe

# Guardrails AI - disabled for now
# from guardrails import Guard
# try:
#     from guardrails.hub import ToxicLanguage
# except ImportError:
#     ToxicLanguage = None  # Guardrails validator not available

# Local imports
from config import config
from prompts import get_system_prompt
from utils import (
    setup_logging,
    print_welcome_message,
    print_user_message,
    print_agent_message,
    print_system_message,
    print_error,
    sanitize_input,
    is_exit_command,
    create_conversation_metadata,
)

# Setup logging
logger = setup_logging(config.LOG_LEVEL)

# Custom fact extraction prompt for Mem0
# Note: This works best with larger models (8B+). With smaller models like llama3.2 (3B),
# some facts from assistant messages may be incorrectly extracted.
CUSTOM_FACT_EXTRACTION_PROMPT = """You extract facts from the user line only.

Format:
user: <user message>
assistant: <ignore this>

Extract from user line. Questions return empty.

Examples:

user: My name is John
assistant: Hi John!
{"facts": ["Name is John"]}

user: I work at Tesla as an engineer
assistant: Tesla is great!
{"facts": ["Works at Tesla", "Works as engineer"]}

user: I'm travelling to Paris next week
assistant: Paris is beautiful!
{"facts": ["Travelling to Paris", "Leaving next week"]}

user: Where am I going?
assistant: You're going to Spain.
{"facts": []}

user: I'm a data scientist
assistant: Data science is interesting!
{"facts": ["Works as data scientist"]}

Return: {"facts": [...]}
"""

CUSTOM_ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting entities and their relationships from conversations.

Extract ONLY concrete entities (people, organizations, places, projects, products) and their relationships.

Format your response as JSON with entities and relationships:

Examples:

Input: "My name is John and I work at Tesla"
Output:
{
    "entities": [
        {"name": "John", "type": "Person"},
        {"name": "Tesla", "type": "Organization"}
    ],
    "relationships": [
        {"from": "John", "to": "Tesla", "type": "WORKS_AT"}
    ]
}

Input: "I'm working on the Cybertruck project"
Output:
{
    "entities": [
        {"name": "Cybertruck", "type": "Project"}
    ],
    "relationships": [
        {"from": "Person", "to": "Cybertruck", "type": "WORKS_ON"}
    ]
}

Input: "My colleague Sarah leads the battery team"
Output:
{
    "entities": [
        {"name": "Sarah", "type": "Person"},
        {"name": "battery team", "type": "Team"}
    ],
    "relationships": [
        {"from": "Sarah", "to": "battery team", "type": "LEADS"}
    ]
}

Extract all entities and relationships from the conversation.
"""


class PydanticAIAgent:
    """
    Main agent class integrating Pydantic AI, Mem0, Langfuse, and Guardrails
    """

    def __init__(self):
        """Initialize the agent with all integrations"""
        logger.info("Initializing Pydantic AI Agent...")

        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid configuration. Please check your environment variables.")

        # Display configuration
        config.display()

        # Initialize Ollama model (via OpenAI-compatible endpoint)
        # Use simple model string for pydantic-ai 1.x
        self.model = f"openai:{config.OLLAMA_MODEL}"

        # Get system prompt
        system_prompt = get_system_prompt(config.AGENT_PROMPT_TEMPLATE)

        # Initialize Pydantic AI Agent
        self.agent = Agent(
            model=self.model,
            system_prompt=system_prompt,
        )

        # Initialize Mem0 for long-term memory
        self.memory = self._initialize_memory()

        # Initialize Langfuse for observability
        self.langfuse = self._initialize_langfuse()

        # Initialize Guardrails - disabled for now
        # self.guard = self._initialize_guardrails()
        self.guard = None

        # Session metadata
        self.session_metadata = create_conversation_metadata(config.MEM0_USER_ID)

        logger.info("Agent initialization complete!")

    def _initialize_memory(self) -> Optional[Memory]:
        """
        Initialize Mem0 with Qdrant backend

        Returns:
            Memory instance or None if initialization fails
        """
        try:
            # Use Ollama for both LLM and embeddings
            memory_config = {
                "llm": {
                    "provider": "ollama",
                    "config": {
                        "model": config.OLLAMA_MODEL,
                        "ollama_base_url": config.OLLAMA_HOST,
                    }
                },
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": config.QDRANT_HOST,
                        "port": config.QDRANT_PORT,
                        "collection_name": config.QDRANT_COLLECTION,
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
                "graph_store": {
                    "provider": "neo4j",
                    "config": {
                        "url": config.NEO4J_URI,
                        "username": config.NEO4J_USERNAME,
                        "password": config.NEO4J_PASSWORD,
                        "database": config.NEO4J_DATABASE,
                    },
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": "gpt-4o-mini",
                            "temperature": 0,
                            "max_tokens": 2000,
                            "api_key": config.OPENAI_GRAPH_API_KEY,  # Use separate API key for graph extraction
                            "openai_base_url": "https://api.openai.com/v1",  # Explicit OpenAI API endpoint
                        }
                    },
                    "custom_prompt": CUSTOM_ENTITY_EXTRACTION_PROMPT,
                },
                "custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT,
            }

            memory = Memory.from_config(memory_config)
            logger.info("Mem0 initialized successfully with Qdrant, Neo4j GraphRAG, and Ollama embeddings")
            return memory

        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            print_system_message(f"Warning: Memory system unavailable - {e}", "yellow")
            return None

    def _initialize_langfuse(self) -> Optional[Langfuse]:
        """
        Initialize Langfuse for observability

        Returns:
            Langfuse instance or None if disabled/failed
        """
        if not config.LANGFUSE_ENABLED:
            logger.info("Langfuse observability is disabled")
            return None

        if not config.LANGFUSE_PUBLIC_KEY or not config.LANGFUSE_SECRET_KEY:
            logger.warning("Langfuse keys not configured, skipping observability")
            return None

        try:
            langfuse = Langfuse(
                public_key=config.LANGFUSE_PUBLIC_KEY,
                secret_key=config.LANGFUSE_SECRET_KEY,
                host=config.LANGFUSE_HOST,
            )
            logger.info("Langfuse initialized successfully")
            return langfuse

        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            print_system_message(f"Warning: Observability unavailable - {e}", "yellow")
            return None

    # def _initialize_guardrails(self) -> Optional[Guard]:
    #     """
    #     Initialize Guardrails AI
    #
    #     Returns:
    #         Guard instance or None if disabled/failed
    #     """
    #     if not config.GUARDRAILS_ENABLED:
    #         logger.info("Guardrails AI is disabled")
    #         return None
    #
    #     try:
    #         if ToxicLanguage is None:
    #             logger.warning("ToxicLanguage validator not available, skipping Guardrails")
    #             return None
    #
    #         # Initialize with toxic language detection
    #         guard = Guard().use(
    #             ToxicLanguage,
    #             threshold=0.5,
    #             validation_method="sentence",
    #             on_fail="exception"
    #         )
    #         logger.info("Guardrails AI initialized successfully")
    #         return guard
    #
    #     except Exception as e:
    #         logger.error(f"Failed to initialize Guardrails: {e}")
    #         print_system_message(f"Warning: Guardrails unavailable - {e}", "yellow")
    #         return None

    def _get_memory_context(self, user_input: str) -> str:
        """
        Retrieve relevant memories based on user input

        Args:
            user_input: Current user message

        Returns:
            Memory context string
        """
        if not self.memory:
            return ""

        try:
            # Search for relevant memories
            logger.info(f"Searching memories for query: '{user_input}'")
            memories = self.memory.search(
                query=user_input,
                user_id=config.MEM0_USER_ID,
                limit=3
            )
            logger.info(f"Found {len(memories) if memories else 0} memories: {memories}")

            # Mem0 1.0.0 returns {'results': [...]} format
            if memories and isinstance(memories, dict):
                memory_list = memories.get('results', [])
            elif memories and isinstance(memories, list):
                memory_list = memories
            else:
                memory_list = []

            if memory_list:
                context = "\n[Previous Context]:\n"
                for mem in memory_list:
                    # Extract memory text from the result object
                    if isinstance(mem, dict):
                        mem_text = mem.get('memory', mem.get('text', str(mem)))
                    else:
                        mem_text = str(mem)
                    context += f"- {mem_text}\n"
                logger.info(f"Memory context created: {context}")
                return context
            else:
                logger.warning("No memories found for this query")

        except Exception as e:
            logger.error(f"Error retrieving memories: {e}", exc_info=True)

        return ""

    def _save_to_memory(self, user_input: str, agent_response: str) -> None:
        """
        Save conversation to long-term memory

        Args:
            user_input: User message
            agent_response: Agent response
        """
        if not self.memory:
            logger.warning("Memory not initialized, skipping save")
            return

        try:
            logger.info(f"Attempting to save conversation to memory...")

            # Save the conversation turn using the custom extraction prompt from memory config
            result = self.memory.add(
                messages=[
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": agent_response}
                ],
                user_id=config.MEM0_USER_ID,
                agent_id=config.MEM0_AGENT_ID,
                metadata=self.session_metadata,
                infer=True,  # Enable LLM-based fact extraction with custom prompt
            )
            logger.info(f"Conversation saved to memory. Result: {result}")

        except Exception as e:
            logger.error(f"Error saving to memory: {e}", exc_info=True)

    # def _validate_with_guardrails(self, text: str) -> bool:
    #     """
    #     Validate text using Guardrails AI
    #
    #     Args:
    #         text: Text to validate
    #
    #     Returns:
    #         True if valid, False otherwise
    #     """
    #     if not self.guard:
    #         return True
    #
    #     try:
    #         self.guard.validate(text)
    #         return True
    #
    #     except Exception as e:
    #         logger.warning(f"Guardrails validation failed: {e}")
    #         return False

    @observe()
    async def process_message(self, user_input: str) -> str:
        """
        Process a user message and return agent response

        Args:
            user_input: User message

        Returns:
            Agent response
        """
        # Sanitize input
        user_input = sanitize_input(user_input)

        # Validate input with guardrails - disabled for now
        # if not self._validate_with_guardrails(user_input):
        #     return "I'm sorry, but I cannot process that message. Please rephrase your request."

        # Get memory context
        memory_context = self._get_memory_context(user_input)

        # Prepare the full message with context
        full_message = user_input
        if memory_context:
            full_message = f"{memory_context}\n\n{user_input}"

        # Get response from agent
        try:
            result = await self.agent.run(full_message)
            # In pydantic-ai, result.output contains the response
            if hasattr(result, 'output'):
                response = result.output
            elif hasattr(result, 'data'):
                response = result.data
            elif isinstance(result, str):
                response = result
            else:
                # Fallback: convert to string
                response = str(result)

            # Validate response with guardrails - disabled for now
            # if not self._validate_with_guardrails(response):
            #     response = "I apologize, but I need to rephrase my response. Let me try again."

            # Save to memory
            self._save_to_memory(user_input, response)

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I encountered an error: {str(e)}"

    async def run_conversation_loop(self) -> None:
        """
        Run the main conversation loop
        """
        print_welcome_message(config.AGENT_NAME, config.AGENT_PROMPT_TEMPLATE)

        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                # Check for exit command
                if is_exit_command(user_input):
                    print_system_message("Goodbye! 👋")
                    break

                if not user_input:
                    continue

                # Print user message
                print_user_message(user_input)

                # Process message and get response
                response = await self.process_message(user_input)

                # Print agent response
                print_agent_message(response)

            except KeyboardInterrupt:
                print_system_message("\n\nConversation interrupted. Goodbye! 👋")
                break

            except Exception as e:
                logger.error(f"Error in conversation loop: {e}")
                print_error(str(e))


async def main():
    """Main entry point"""
    try:
        agent = PydanticAIAgent()
        await agent.run_conversation_loop()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print_error(f"Failed to start agent: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
