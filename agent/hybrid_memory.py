"""
Hybrid Memory Manager for Pydantic AI Agent

Combines:
- mem0: Vector-based semantic search (pgvector)
- Graphiti: Temporal knowledge graph (Neo4j)

This provides best-of-both-worlds memory:
- Fast semantic search from mem0's pgvector integration
- Rich temporal knowledge graph from Graphiti
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime

from mem0 import Memory
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder import OpenAIEmbedder
from graphiti_core.embedder.openai import OpenAIEmbedderConfig

# Import contradiction handler
from contradiction_handler import ContradictionHandler

logger = logging.getLogger(__name__)


class HybridMemoryManager:
    """
    Hybrid memory manager combining mem0 (vectors) and Graphiti (graph).

    Architecture:
    - mem0: Handles vector embeddings and semantic search (pgvector)
    - Graphiti: Handles knowledge graph with temporal awareness (Neo4j)
    """

    def __init__(
        self,
        mem0_config: Dict[str, Any],
        neo4j_uri: str,
        neo4j_username: str,
        neo4j_password: str,
        openai_api_key: str
    ):
        """
        Initialize hybrid memory manager.

        Args:
            mem0_config: Configuration dict for mem0 (vector store only, no graph)
            neo4j_uri: Neo4j connection URI (bolt://...)
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
            openai_api_key: OpenAI API key for Graphiti's LLM operations
        """
        self.mem0_config = mem0_config
        self.neo4j_uri = neo4j_uri
        self.neo4j_username = neo4j_username
        self.neo4j_password = neo4j_password
        self.openai_api_key = openai_api_key

        # Will be initialized asynchronously
        self.mem0: Optional[Memory] = None
        self.graphiti: Optional[Graphiti] = None
        self.contradiction_handler: Optional[ContradictionHandler] = None
        self._initialized = False

        # Store last user message for context enhancement
        self._last_user_message: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize both mem0 and Graphiti asynchronously."""
        if self._initialized:
            logger.warning("Hybrid memory already initialized")
            return

        try:
            # Initialize mem0 (vector store only - disable graph)
            logger.info("Initializing mem0 for vector storage...")

            # Deep copy to avoid modifying original config
            import copy
            mem0_config_no_graph = copy.deepcopy(self.mem0_config)

            # Remove graph_store from config to use mem0 for vectors only
            if 'graph_store' in mem0_config_no_graph:
                del mem0_config_no_graph['graph_store']

            # Debug: log the config being used
            logger.info(f"mem0 config keys: {list(mem0_config_no_graph.keys())}")
            logger.info(f"Has custom_fact_extraction_prompt: {'custom_fact_extraction_prompt' in mem0_config_no_graph}")
            logger.info(f"Has custom_update_memory_prompt: {'custom_update_memory_prompt' in mem0_config_no_graph}")

            self.mem0 = Memory.from_config(mem0_config_no_graph)
            logger.info("mem0 initialized successfully with OpenAI LLM (vector store only)")

            # Initialize Graphiti (knowledge graph)
            logger.info(f"Initializing Graphiti with Neo4j: {self.neo4j_uri}")

            # Create OpenAI LLM client for Graphiti
            # Use gpt-4o for main operations, gpt-4o-mini for simple tasks
            llm_config = LLMConfig(
                api_key=self.openai_api_key,
                model="gpt-4o",  # Main model for complex operations
                small_model="gpt-4o-mini",  # Smaller model for simple operations
                base_url="https://api.openai.com/v1",
                temperature=0.1,  # Low temperature for consistent entity extraction
                max_tokens=4096
            )
            # Configure OpenAI client for gpt-4o compatibility
            # Set verbosity to 'medium' as 'low' is not supported by gpt-4o
            llm_client = OpenAIClient(config=llm_config, reasoning=None, verbosity='medium')

            # Create OpenAI embedder for Graphiti
            embedder_config = OpenAIEmbedderConfig(
                api_key=self.openai_api_key,
                embedding_model="text-embedding-3-small",  # OpenAI's efficient embedding model
                base_url="https://api.openai.com/v1"
            )
            embedder = OpenAIEmbedder(config=embedder_config)

            self.graphiti = Graphiti(
                uri=self.neo4j_uri,
                user=self.neo4j_username,
                password=self.neo4j_password,
                llm_client=llm_client,
                embedder=embedder
            )

            # Build indices and constraints (only needs to be done once)
            logger.info("Building Graphiti indices and constraints...")
            await self.graphiti.build_indices_and_constraints()
            logger.info("Graphiti initialized successfully")

            # Initialize contradiction handler
            self.contradiction_handler = ContradictionHandler(self.graphiti)
            logger.info("Contradiction handler initialized")

            self._initialized = True
            logger.info("Hybrid memory manager fully initialized!")

        except Exception as e:
            logger.error(f"Failed to initialize hybrid memory: {e}", exc_info=True)
            raise

    async def add(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        infer: bool = True
    ) -> Dict[str, Any]:
        """
        Add conversation to both mem0 (vectors) and Graphiti (graph).

        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User identifier
            agent_id: Agent identifier
            metadata: Optional metadata dict
            infer: Whether to infer facts for mem0

        Returns:
            Combined results from both systems
        """
        if not self._initialized:
            raise RuntimeError("Hybrid memory not initialized. Call initialize() first.")

        results = {
            'mem0': None,
            'graphiti': None
        }

        try:
            # WORKAROUND for mem0 bug: Delete conflicting memories before adding corrections
            # mem0's fact extraction includes old memory context, causing it to extract
            # old values instead of new ones when users correct information.
            # We detect corrections and pre-emptively delete related memories.
            for i, msg in enumerate(messages):
                if msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    negation = self.contradiction_handler.detect_negation(user_message)

                    if negation:
                        logger.info(f"Detected correction in message, deleting related mem0 memories: '{negation}'")

                        # Extract keywords from the correction
                        keywords = self.contradiction_handler.extract_topic_keywords(negation)

                        # ALSO extract keywords from previous user message for context (e.g., company name)
                        # Look back through messages to find the previous user message
                        for j in range(i - 1, -1, -1):
                            prev_msg = messages[j]
                            if prev_msg.get('role') == 'user':
                                prev_keywords = self.contradiction_handler.extract_topic_keywords(prev_msg.get('content', ''))
                                # Add company names from previous context
                                for keyword in prev_keywords:
                                    if keyword not in keywords:
                                        keywords.append(keyword)
                                logger.info(f"Added context keywords from previous message: {prev_keywords}")
                                break

                        if keywords:
                            # Search mem0 for memories related to these keywords
                            # Use ALL keywords to be more specific
                            search_query = " ".join(keywords)
                            logger.info(f"Searching mem0 for memories to delete with query: '{search_query}'")

                            related_memories = self.mem0.search(
                                query=search_query,
                                user_id=user_id,
                                limit=10
                            )

                            # Delete related memories
                            deleted_count = 0
                            if related_memories and 'results' in related_memories:
                                for memory in related_memories['results']:
                                    memory_id = memory.get('id')
                                    memory_text = memory.get('memory', '')

                                    # Check if this memory is about the topic being corrected
                                    memory_lower = memory_text.lower()
                                    # ALL keywords must match (more specific)
                                    if all(keyword.lower() in memory_lower for keyword in keywords):
                                        try:
                                            self.mem0.delete(memory_id=memory_id)
                                            logger.info(f"Deleted mem0 memory: {memory_text}")
                                            deleted_count += 1
                                        except Exception as e:
                                            logger.warning(f"Failed to delete memory {memory_id}: {e}")

                            logger.info(f"Deleted {deleted_count} conflicting mem0 memories")

            # Add to mem0 (vector store)
            logger.info("Adding conversation to mem0 (vector store)...")
            logger.info(f"Messages to add: {messages}")
            logger.info(f"user_id: {user_id}, agent_id: {agent_id}, infer: {infer}")

            # ENHANCEMENT: Enrich correction messages with context from previous messages
            # This helps mem0's fact extraction include company names and other context
            enhanced_messages = []
            for i, msg in enumerate(messages):
                if msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    negation = self.contradiction_handler.detect_negation(user_message)

                    # If this is a correction, add context from previous user message
                    if negation:
                        # Look for previous user message in the messages array first
                        prev_context = None
                        for j in range(i - 1, -1, -1):
                            prev_msg = messages[j]
                            if prev_msg.get('role') == 'user':
                                prev_context = prev_msg.get('content', '')
                                break

                        # If no previous message in array, use stored last message
                        if not prev_context and self._last_user_message:
                            prev_context = self._last_user_message
                            logger.info(f"Using stored last user message for context: '{prev_context}'")

                        if prev_context:
                            # Extract company/entity names from previous context
                            import re
                            # Look for "at/for/with [Company]" pattern
                            company_matches = re.findall(r'(?:at|for|with)\s+([A-Z][a-zA-Z]+)', prev_context)

                            if company_matches:
                                company = company_matches[0]
                                # Check if current message already mentions the company
                                if company.lower() not in user_message.lower():
                                    # Enhance the message by injecting company context
                                    # Look for role-related phrases
                                    role_pattern = r'(my role|my position|my job|my title|i work|i am|i\'m)\s+(?:is|as)?\s*(.+)'
                                    role_match = re.search(role_pattern, user_message.lower())

                                    if role_match:
                                        # Reconstruct message with company context using re.sub for case-insensitive replacement
                                        def enhance_role(match):
                                            return f"{match.group(1)} at {company} is {match.group(2)}"

                                        enhanced_msg = re.sub(
                                            role_pattern,
                                            enhance_role,
                                            user_message,
                                            count=1,
                                            flags=re.IGNORECASE
                                        )
                                        logger.info(f"Enhanced correction message with context: '{user_message}' -> '{enhanced_msg}'")
                                        enhanced_messages.append({'role': 'user', 'content': enhanced_msg})
                                        continue

                # No enhancement needed, use original message
                enhanced_messages.append(msg)

            mem0_result = self.mem0.add(
                messages=enhanced_messages,
                user_id=user_id,
                agent_id=agent_id,
                metadata=metadata,
                infer=infer
            )
            results['mem0'] = mem0_result
            logger.info(f"mem0 add result: {mem0_result}")

            # Check if mem0 actually saved anything
            if mem0_result and isinstance(mem0_result, dict):
                num_results = len(mem0_result.get('results', []))
                logger.info(f"mem0 saved {num_results} memories")
                if num_results == 0:
                    logger.warning("mem0 returned 0 memories - check if custom prompts are working correctly")

            # Add to Graphiti (knowledge graph)
            # Graphiti uses "episodes" - convert conversation to episode format
            logger.info("Adding conversation to Graphiti (knowledge graph)...")

            # Combine all messages into a single episode
            conversation_text = "\n".join([
                f"{msg['role'].capitalize()}: {msg['content']}"
                for msg in messages
            ])

            episode_name = f"Conversation_{user_id}_{datetime.now().isoformat()}"
            reference_time = datetime.now()
            graphiti_result = await self.graphiti.add_episode(
                name=episode_name,
                episode_body=conversation_text,
                source_description=f"Conversation with user {user_id}",
                source=EpisodeType.message,  # Use 'source' parameter with EpisodeType
                reference_time=reference_time
            )
            results['graphiti'] = graphiti_result
            logger.info(f"Graphiti add result: {graphiti_result}")

            # Check for contradictions and invalidate outdated facts
            # Only check user messages for negations/corrections
            for msg in messages:
                if msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    negation = self.contradiction_handler.detect_negation(user_message)

                    if negation:
                        logger.info(f"Detected negation/correction: '{negation}'")
                        invalidated_count = await self.contradiction_handler.invalidate_contradicting_facts(
                            negated_topic=negation,
                            user_id=user_id,
                            reference_time=reference_time
                        )
                        results['invalidated_facts'] = invalidated_count
                        logger.info(f"Invalidated {invalidated_count} contradicting facts")

            # Store the last user message for future context enhancement
            for msg in reversed(messages):
                if msg.get('role') == 'user':
                    self._last_user_message = msg.get('content', '')
                    logger.info(f"Stored last user message for context: '{self._last_user_message}'")
                    break

            return results

        except Exception as e:
            logger.error(f"Error adding to hybrid memory: {e}", exc_info=True)
            return results

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search both mem0 (vector) and Graphiti (graph).

        Args:
            query: Search query
            user_id: User identifier
            limit: Max results to return

        Returns:
            Combined results with vector memories and graph relationships
        """
        if not self._initialized:
            raise RuntimeError("Hybrid memory not initialized. Call initialize() first.")

        results = {
            'vector_results': [],
            'graph_results': [],
            'combined_context': ""
        }

        try:
            # Search mem0 (vector store)
            logger.info(f"Searching mem0 for: '{query}'")
            mem0_results = self.mem0.search(
                query=query,
                user_id=user_id,
                limit=limit
            )

            if mem0_results and isinstance(mem0_results, dict):
                results['vector_results'] = mem0_results.get('results', [])

            # Search Graphiti (knowledge graph)
            logger.info(f"Searching Graphiti for: '{query}'")
            graphiti_results = await self.graphiti.search(
                query=query,
                num_results=limit
            )
            # Graphiti returns a list of edges directly
            results['graph_results'] = graphiti_results if graphiti_results else []

            # Combine into unified context
            context_parts = []

            # Add vector results
            logger.info(f"Processing {len(results['vector_results'])} vector results")
            for i, mem in enumerate(results['vector_results']):
                if isinstance(mem, dict):
                    logger.info(f"Vector result {i} keys: {mem.keys()}")
                    mem_text = mem.get('memory', mem.get('text', str(mem)))
                    context_parts.append(f"- {mem_text}")
                    logger.info(f"Added vector context: {mem_text}")

            # Add graph results - format edge relationships
            # IMPORTANT: Only include ACTIVE facts (where invalid_at is None)
            logger.info(f"Processing {len(results['graph_results'])} graph results")
            for i, edge in enumerate(results['graph_results']):
                # Skip invalid facts
                if hasattr(edge, 'invalid_at') and edge.invalid_at is not None:
                    logger.info(f"Skipping INVALID graph fact: {edge.fact if hasattr(edge, 'fact') else 'unknown'}")
                    continue

                logger.info(f"Graph result {i} type: {type(edge)}, has fact: {hasattr(edge, 'fact')}, has name: {hasattr(edge, 'name')}")
                # Graphiti edges have fact/name that describes the relationship
                if hasattr(edge, 'fact'):
                    context_parts.append(f"- {edge.fact}")
                    logger.info(f"Added graph fact: {edge.fact}")
                elif hasattr(edge, 'name'):
                    context_parts.append(f"- {edge.name}")
                    logger.info(f"Added graph name: {edge.name}")
                else:
                    # Fallback: try to format as source -> relation -> target
                    try:
                        source = getattr(edge, 'source_node_name', 'Unknown')
                        target = getattr(edge, 'target_node_name', 'Unknown')
                        relation = getattr(edge, 'name', getattr(edge, 'fact', 'related to'))
                        formatted = f"{source} {relation} {target}"
                        context_parts.append(f"- {formatted}")
                        logger.info(f"Added graph relationship: {formatted}")
                    except Exception as ex:
                        logger.warning(f"Failed to format graph edge: {ex}")

            if context_parts:
                results['combined_context'] = "\n[Previous Context]:\n" + "\n".join(context_parts)
                logger.info(f"Combined context created with {len(context_parts)} parts")
                logger.info(f"Combined context: {results['combined_context'][:500]}...")
            else:
                logger.warning("No context parts collected - combined_context will be empty")

            logger.info(f"Hybrid search returned {len(results['vector_results'])} vector results + {len(results['graph_results'])} graph results")

            return results

        except Exception as e:
            logger.error(f"Error searching hybrid memory: {e}", exc_info=True)
            return results

    async def close(self) -> None:
        """Clean up connections."""
        if self.graphiti:
            await self.graphiti.close()
        logger.info("Hybrid memory connections closed")
