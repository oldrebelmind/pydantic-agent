"""
Pydantic AI Agent with Mem0, Langfuse, and Guardrails AI

Main application entry point.
"""
import asyncio
from typing import Optional
import httpx
import re
from datetime import datetime
import pytz
try:
    import ntplib
except ImportError:
    ntplib = None  # NTP sync will be disabled if ntplib not available

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
CUSTOM_FACT_EXTRACTION_PROMPT = """You extract facts from the user line only. Extract ALL specific details separately.

IMPORTANT:
- Extract location details with full specificity (city, neighborhood, area, side of town)
- Break down compound statements into separate facts
- Preserve exact details like addresses, neighborhoods, districts
- Extract preferences, habits, and contextual information

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

user: I live on the north side of Indianapolis
assistant: That's a nice area!
{"facts": ["Lives in Indianapolis", "Lives on north side of Indianapolis"]}

user: I live in San Francisco, specifically in the Mission District
assistant: The Mission is vibrant!
{"facts": ["Lives in San Francisco", "Lives in Mission District"]}

user: I usually work from my office downtown near 5th and Main
assistant: That's convenient!
{"facts": ["Works from office", "Office is downtown", "Office near 5th and Main"]}

user: Where am I going?
assistant: You're going to Spain.
{"facts": []}

user: I'm a data scientist
assistant: Data science is interesting!
{"facts": ["Works as data scientist"]}

user: I prefer working in the mornings
assistant: Morning work is productive!
{"facts": ["Prefers working in mornings"]}

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

CUSTOM_UPDATE_MEMORY_PROMPT = """You are a smart memory manager which controls the memory of a system.
You can perform four operations: (1) add into the memory, (2) update the memory, (3) delete from the memory, and (4) no change.

Based on the above four operations, the memory will change.

Compare newly retrieved facts with the existing memory. For each new fact, decide whether to:
- ADD: Add it to the memory as a new element
- UPDATE: Update an existing memory element
- DELETE: Delete an existing memory element
- NONE: Make no change (if the fact is already present or irrelevant)

**CRITICAL RULES FOR PRESERVING DETAIL:**
1. ALWAYS keep the fact with MORE specificity and detail
2. NEVER simplify or generalize location information (neighborhoods, sides of town, districts, addresses)
3. When comparing similar facts, keep the one that contains MORE information, not less
4. "Lives on north side of Indianapolis" is MORE detailed than "Lives in Indianapolis" - KEEP THE DETAILED VERSION
5. "Office near 5th and Main" is MORE detailed than "Office downtown" - KEEP THE DETAILED VERSION
6. If both old and new facts have different details, COMBINE them into one fact with all details

There are specific guidelines to select which operation to perform:

1. **Add**: If the retrieved facts contain new information not present in the memory, then you have to add it by generating a new ID in the id field.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "User is a software engineer"
            }
        ]
    - Retrieved facts: ["Name is John"]
    - New Memory:
        {
            "memory" : [
                {
                    "id" : "0",
                    "text" : "User is a software engineer",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "Name is John",
                    "event" : "ADD"
                }
            ]

        }

2. **Update**: If the retrieved facts contain information that is already present in the memory but the information is totally different, then you have to update it.
**CRITICAL**: If the retrieved fact contains information that conveys the same thing as the elements present in the memory, then you MUST keep the fact which has the MOST SPECIFIC information and detail.
Example (a) -- if the memory contains "User likes to play cricket" and the retrieved fact is "Loves to play cricket with friends", then update the memory with the retrieved facts because it adds "with friends".
Example (b) -- if the memory contains "Likes cheese pizza" and the retrieved fact is "Loves cheese pizza", then you do not need to update it because they convey the same information with the same level of detail.
**Example (c) -- if the memory contains "Lives on north side of Indianapolis" and the retrieved fact is "Lives in Indianapolis", DO NOT UPDATE because the existing memory has MORE detail (specifies "north side"). Keep the existing detailed memory.**
**Example (d) -- if the memory contains "Lives in Indianapolis" and the retrieved fact is "Lives on north side of Indianapolis", UPDATE to the more detailed version because it adds neighborhood specificity.**
If the direction is to update the memory, then you have to update it.
Please keep in mind while updating you have to keep the same ID.
Please note to return the IDs in the output from the input IDs only and do not generate any new ID.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "Lives on north side of Indianapolis"
            },
            {
                "id" : "1",
                "text" : "User is a software engineer"
            },
            {
                "id" : "2",
                "text" : "User likes to play cricket"
            }
        ]
    - Retrieved facts: ["Lives in Indianapolis", "Loves to play cricket with friends"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "Lives on north side of Indianapolis",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "User is a software engineer",
                    "event" : "NONE"
                },
                {
                    "id" : "2",
                    "text" : "Loves to play cricket with friends",
                    "event" : "UPDATE",
                    "old_memory" : "User likes to play cricket"
                }
            ]
        }


3. **Delete**: If the retrieved facts contain information that contradicts the information present in the memory, then you have to delete it. Or if the direction is to delete the memory, then you have to delete it.
Please note to return the IDs in the output from the input IDs only and do not generate any new ID.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "Name is John"
            },
            {
                "id" : "1",
                "text" : "Loves cheese pizza"
            }
        ]
    - Retrieved facts: ["Dislikes cheese pizza"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "Name is John",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "Loves cheese pizza",
                    "event" : "DELETE"
                }
        ]
        }

4. **No Change**: If the retrieved facts contain information that is already present in the memory, then you do not need to make any changes.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "Name is John"
            },
            {
                "id" : "1",
                "text" : "Loves cheese pizza"
            }
        ]
    - Retrieved facts: ["Name is John"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "Name is John",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "Loves cheese pizza",
                    "event" : "NONE"
                }
            ]
        }
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
                    "provider": "milvus",
                    "config": {
                        "url": f"http://{config.MILVUS_HOST}:{config.MILVUS_PORT}",
                        "token": "",  # Empty token for local Milvus standalone
                        "collection_name": config.MILVUS_COLLECTION,
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
                            "api_key": config.OPENAI_GRAPH_API_KEY,
                            "openai_base_url": "https://api.openai.com/v1",
                        }
                    },
                    "custom_prompt": CUSTOM_ENTITY_EXTRACTION_PROMPT,
                },
                "custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT,
                "custom_update_memory_prompt": CUSTOM_UPDATE_MEMORY_PROMPT,
            }

            memory = Memory.from_config(memory_config)
            logger.info("Mem0 initialized successfully with Milvus, Neo4j GraphRAG, and Ollama embeddings (GitHub main)")
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

    def _get_ntp_time(self) -> Optional[float]:
        """
        Get current time from NTP server (us.pool.ntp.org).

        Returns:
            Unix timestamp from NTP server, or None if NTP query fails
        """
        if ntplib is None:
            logger.warning("ntplib not available. Using system time as fallback.")
            return None

        try:
            ntp_client = ntplib.NTPClient()

            # Query US NTP pool with 3 second timeout
            response = ntp_client.request('us.pool.ntp.org', version=3, timeout=3)

            # Get the NTP time
            ntp_time = response.tx_time

            logger.info(f"Successfully synced with NTP server us.pool.ntp.org")
            return ntp_time

        except Exception as e:
            logger.warning(f"Failed to sync with NTP server: {e}. Using system time as fallback.")
            return None

    def _get_user_timezone(self) -> str:
        """
        Retrieve user's timezone preference from Mem0 memory.
        Can detect both explicit timezone strings (e.g., "America/New_York")
        and city names (e.g., "Indianapolis", "New York").

        Returns:
            Timezone string (e.g., 'America/New_York') or 'UTC' if not found
        """
        if not self.memory:
            return 'UTC'

        # Mapping of common US cities to their IANA timezones
        city_to_timezone = {
            'new york': 'America/New_York',
            'nyc': 'America/New_York',
            'boston': 'America/New_York',
            'philadelphia': 'America/New_York',
            'washington': 'America/New_York',
            'miami': 'America/New_York',
            'atlanta': 'America/New_York',
            'chicago': 'America/Chicago',
            'indianapolis': 'America/Indiana/Indianapolis',
            'dallas': 'America/Chicago',
            'houston': 'America/Chicago',
            'denver': 'America/Denver',
            'phoenix': 'America/Phoenix',
            'los angeles': 'America/Los_Angeles',
            'la': 'America/Los_Angeles',
            'san francisco': 'America/Los_Angeles',
            'sf': 'America/Los_Angeles',
            'seattle': 'America/Los_Angeles',
            'portland': 'America/Los_Angeles',
            'las vegas': 'America/Los_Angeles',
        }

        try:
            # Search memory for timezone information
            logger.info("Searching for user timezone in memory...")
            memories = self.memory.search(
                query="user timezone preference location city",
                user_id=config.MEM0_USER_ID,
                limit=5
            )

            # Parse memories to find timezone
            if memories and isinstance(memories, dict):
                memory_list = memories.get('results', [])
            elif memories and isinstance(memories, list):
                memory_list = memories
            else:
                memory_list = []

            # Look for timezone patterns in memories
            timezone_pattern = r'\b([A-Z][a-z]+/[A-Z][a-z_]+)\b'  # Matches "America/New_York" format

            for mem in memory_list:
                if isinstance(mem, dict):
                    mem_text = mem.get('memory', mem.get('text', str(mem)))
                else:
                    mem_text = str(mem)

                mem_text_lower = mem_text.lower()

                # 1. Check if memory contains explicit timezone information
                if 'timezone' in mem_text_lower or 'time zone' in mem_text_lower:
                    # Try to extract timezone string
                    match = re.search(timezone_pattern, mem_text)
                    if match:
                        timezone_str = match.group(1)
                        # Validate timezone
                        try:
                            pytz.timezone(timezone_str)
                            logger.info(f"Found explicit timezone in memory: {timezone_str}")
                            return timezone_str
                        except pytz.exceptions.UnknownTimeZoneError:
                            logger.warning(f"Invalid timezone found in memory: {timezone_str}")
                            continue

                # 2. Check if memory contains a city name we can map to a timezone
                for city, tz in city_to_timezone.items():
                    if city in mem_text_lower:
                        logger.info(f"Found city '{city}' in memory, mapping to timezone: {tz}")
                        return tz

            # Fallback: Try get_all() to retrieve all memories if search didn't find location
            logger.info("Search didn't find timezone, trying get_all() as fallback...")
            try:
                all_memories = self.memory.get_all(user_id=config.MEM0_USER_ID)
                if all_memories:
                    if isinstance(all_memories, dict):
                        all_memory_list = all_memories.get('results', [])
                    elif isinstance(all_memories, list):
                        all_memory_list = all_memories
                    else:
                        all_memory_list = []

                    for mem in all_memory_list:
                        if isinstance(mem, dict):
                            mem_text = mem.get('memory', mem.get('text', str(mem)))
                        else:
                            mem_text = str(mem)

                        mem_text_lower = mem_text.lower()

                        # Check for city names in all memories
                        for city, tz in city_to_timezone.items():
                            if city in mem_text_lower:
                                logger.info(f"Found city '{city}' in fallback memory check, mapping to timezone: {tz}")
                                return tz

                logger.info("No valid timezone found in all memories")
            except Exception as fallback_error:
                logger.warning(f"Fallback memory retrieval failed: {fallback_error}")

            logger.info("No valid timezone found in memory, using UTC")
            return 'UTC'

        except Exception as e:
            logger.error(f"Error retrieving timezone from memory: {e}", exc_info=True)
            return 'UTC'

    def _get_current_time_context(self, timezone_str: str = 'UTC') -> str:
        """
        Get current date and time context for this specific message.
        Time is synced with us.pool.ntp.org for accuracy.

        Args:
            timezone_str: Timezone string (e.g., 'America/New_York' or 'UTC')

        Returns:
            Time context string with current datetime in the specified timezone
        """
        # Try to get NTP time first, fallback to system time
        ntp_timestamp = self._get_ntp_time()

        if ntp_timestamp:
            # Use NTP time
            now_utc = datetime.fromtimestamp(ntp_timestamp, tz=pytz.UTC)
            time_source = "(synced with us.pool.ntp.org)"
        else:
            # Fallback to system time
            now_utc = datetime.now(pytz.UTC)
            time_source = "(system time)"

        # Convert to user's timezone
        try:
            user_tz = pytz.timezone(timezone_str)
            now_local = now_utc.astimezone(user_tz)

            # Format datetime information
            current_datetime = now_local.strftime("%A, %B %d, %Y at %I:%M %p %Z")
            timezone_name = now_local.tzname()

            return f"\n[Current Time]: {current_datetime} (Your timezone: {timezone_name}) {time_source}\n"

        except Exception as e:
            logger.error(f"Error converting to timezone {timezone_str}: {e}")
            # Fallback to UTC
            current_datetime = now_utc.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            return f"\n[Current Time]: {current_datetime} {time_source}\n"

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

    async def _save_to_memory_async(self, user_input: str, agent_response: str) -> None:
        """
        Async wrapper for saving conversation to long-term memory.
        Runs memory.add() in a background thread to avoid blocking.

        Args:
            user_input: User message
            agent_response: Agent response
        """
        if not self.memory:
            logger.warning("Memory not initialized, skipping save")
            return

        try:
            logger.info(f"Saving conversation to memory (async background task)...")

            # Run the blocking memory.add() call in a thread pool executor
            # to prevent blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,  # Use default executor
                lambda: self.memory.add(
                    messages=[
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": agent_response}
                    ],
                    user_id=config.MEM0_USER_ID,
                    agent_id=config.MEM0_AGENT_ID,
                    metadata=self.session_metadata,
                    infer=True,  # Enable LLM-based fact extraction with custom prompt
                )
            )
            logger.info(f"Conversation saved to memory successfully (background task completed)")

        except Exception as e:
            logger.error(f"Error saving to memory (async): {e}", exc_info=True)

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

        # Get user's timezone from memory
        user_timezone = self._get_user_timezone()

        # Get current time context (fresh for this message, in user's timezone)
        time_context = self._get_current_time_context(user_timezone)

        # Get memory context
        memory_context = self._get_memory_context(user_input)

        # Prepare the full message with context
        full_message = user_input
        if time_context or memory_context:
            context_parts = [time_context, memory_context]
            combined_context = "".join([ctx for ctx in context_parts if ctx])
            full_message = f"{combined_context}\n{user_input}"

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

    async def process_message_stream(self, user_input: str):
        """
        Process a user message and stream the agent response token by token

        This method is used by the FastAPI streaming endpoint to provide
        real-time responses using Server-Sent Events (SSE).

        Args:
            user_input: User message

        Yields:
            Individual tokens of the agent's response
        """
        try:
            # Sanitize input
            user_input = sanitize_input(user_input)

            # Validate input with guardrails - disabled for now
            # if not self._validate_with_guardrails(user_input):
            #     yield "I'm sorry, but I cannot process that message."
            #     return

            # Get user's timezone from memory
            user_timezone = self._get_user_timezone()

            # Get current time context (fresh for this message, in user's timezone)
            time_context = self._get_current_time_context(user_timezone)

            # Get memory context
            memory_context = self._get_memory_context(user_input)

            # Prepare the full message with context
            full_message = user_input
            if time_context or memory_context:
                context_parts = [time_context, memory_context]
                combined_context = "".join([ctx for ctx in context_parts if ctx])
                full_message = f"{combined_context}\n{user_input}"

            logger.info(f"Streaming response for message: {user_input[:50]}...")

            # Stream response from agent
            full_response = ""
            async with self.agent.run_stream(full_message) as result:
                # Stream text deltas (token by token)
                async for text in result.stream_text(delta=True):
                    full_response += text
                    yield text  # Yield each token as it arrives

            logger.info(f"Stream completed. Total length: {len(full_response)}")

            # Validate response with guardrails - disabled for now
            # if not self._validate_with_guardrails(full_response):
            #     yield " [Response was filtered for safety]"

            # Save complete response to memory asynchronously (non-blocking)
            # This runs in the background so it doesn't delay the stream completion signal
            asyncio.create_task(self._save_to_memory_async(user_input, full_response))

        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            yield f"Error: {str(e)}"

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
