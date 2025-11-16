"""
Contradiction Detection and Fact Invalidation for Graphiti

Since Graphiti's automatic contradiction detection isn't working reliably,
this module implements manual contradiction detection and invalidation.
"""
import re
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ContradictionHandler:
    """Detects contradictions and invalidates outdated facts in Graphiti."""

    # Patterns that indicate the user is correcting/negating previous information
    NEGATION_PATTERNS = [
        # Explicit negations
        r"(?:do not|don't|does not|doesn't|did not|didn't)\s+(.+)",
        r"(?:no longer|not anymore)\s+(.+)",
        r"(?:never|not)\s+(.+)",
        r"(?:i am not|i'm not|i'm no longer)\s+(.+)",
        r"(?:that's|that is)\s+(?:incorrect|wrong|not true|not correct|not right)",  # "that's not correct"
        r"(?:actually|correction)[:,]?\s+(.+)",
        r"(?:flip|flipped|swapped|switched|reversed|backwards)",  # Detect flip-flopped corrections
        r"(?:the other way around|vice versa)",
        # Corrections by assertion (stating new value for existing topic)
        r"(?:my|the)\s+(?:role|position|job|title)\s+(?:at|with|for)\s+(.+)",  # "my role at X is Y"
        r"(?:i|we)\s+(?:work|works)\s+(?:at|for|with)\s+(.+)",  # "i work at X as Y"
    ]

    # Keywords that suggest employment/relationship topics
    WORK_KEYWORDS = ['work', 'works', 'working', 'worked', 'employed', 'job', 'position', 'role']
    LOCATION_KEYWORDS = ['live', 'lives', 'living', 'lived', 'located', 'reside', 'from']

    def __init__(self, graphiti):
        """
        Args:
            graphiti: Graphiti instance for querying and updating facts
        """
        self.graphiti = graphiti

    def detect_negation(self, message: str) -> Optional[str]:
        """
        Detect if a message contains a negation/correction.

        Args:
            message: User message text

        Returns:
            The topic being negated, or None if no negation detected
        """
        message_lower = message.lower().strip()

        for pattern in self.NEGATION_PATTERNS:
            match = re.search(pattern, message_lower)
            if match:
                if len(match.groups()) > 0:
                    return match.group(1).strip()
                else:
                    return message_lower

        return None

    def extract_topic_keywords(self, text: str) -> List[str]:
        """
        Extract key topic words from a negation/correction.

        Focus on the TOPIC CATEGORY (e.g., "role", "position", company name)
        NOT the specific values (e.g., "senior architect", "junior developer").

        Args:
            text: The negated text

        Returns:
            List of keywords that describe the topic being corrected
        """
        text_lower = text.lower()
        keywords = []

        # Check for employment-related topics - add category keywords, not specific values
        for keyword in self.WORK_KEYWORDS:
            if keyword in text_lower:
                # Add general employment keywords so we match any employment memory
                keywords.extend(['work', 'position', 'role', 'job', 'developer', 'engineer'])
                # Extract company name if present
                company_match = re.search(r'(?:work|works|working|role|position)\s+(?:at|for|with)\s+(\w+)', text_lower)
                if company_match:
                    keywords.append(company_match.group(1))
                break

        # Extract company names (case-insensitive now)
        company_patterns = [
            r'(?:at|for|with)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)',  # "at Mirazon", "at TechCorp"
            r'\b(mirazon|brainiacs|corpx|techcorp|tesla|microsoft|google|amazon|apple)\b',  # Known companies
        ]
        for pattern in company_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, str) and len(match) > 2:
                    keywords.append(match.strip())

        # Add topic category keywords
        if any(word in text_lower for word in ['role', 'position', 'title', 'job']):
            keywords.extend(['role', 'position'])

        # Check for location-related topics
        for keyword in self.LOCATION_KEYWORDS:
            if keyword in text_lower:
                keywords.extend(['location', 'live'])
                break

        # Add capitalized words (company names in original text)
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z]+\b', text)
        keywords.extend([n.lower() for n in proper_nouns])

        # Remove duplicates and noise words
        keywords = list(set(keywords))
        noise_words = {'the', 'and', 'but', 'for', 'not', 'this', 'that', 'with', 'from', 'have', 'has', 'is', 'as', 'a', 'an'}
        keywords = [k for k in keywords if k not in noise_words]

        return keywords

    async def invalidate_contradicting_facts(
        self,
        negated_topic: str,
        user_id: str = 'default_user',
        reference_time: Optional[datetime] = None
    ) -> int:
        """
        Find and invalidate facts that contradict the negation.

        Args:
            negated_topic: The topic being negated (e.g., "work at Tesla")
            user_id: User identifier
            reference_time: Time to set as invalid_at (defaults to now)

        Returns:
            Number of facts invalidated
        """
        if reference_time is None:
            reference_time = datetime.now()

        # Extract keywords from the negation
        keywords = self.extract_topic_keywords(negated_topic)

        if not keywords:
            logger.warning(f"No keywords extracted from negation: {negated_topic}")
            return 0

        logger.info(f"Searching for contradicting facts with keywords: {keywords}")

        # Search for facts related to these keywords
        search_query = " ".join(keywords)
        related_facts = await self.graphiti.search(query=search_query, num_results=20)

        if not related_facts:
            logger.info("No related facts found to invalidate")
            return 0

        invalidated_count = 0

        for edge in related_facts:
            # Skip already invalidated facts
            if edge.invalid_at is not None:
                continue

            # Skip facts that were just created (within last 10 seconds)
            # This prevents invalidating the new correct fact that was just added
            if edge.created_at is not None:
                time_diff = (reference_time - edge.created_at.replace(tzinfo=None)).total_seconds()
                if time_diff < 10:
                    logger.info(f"Skipping recently created fact (created {time_diff:.1f}s ago): {edge.fact}")
                    continue

            # Check if this fact contradicts the negation
            fact_lower = edge.fact.lower()

            # If the fact is about the negated topic and doesn't already contain negation
            should_invalidate = False

            for keyword in keywords:
                if keyword in fact_lower:
                    # Check if fact doesn't already contain negation words
                    if not any(neg in fact_lower for neg in ['not', 'no longer', 'never', 'does not', 'do not']):
                        should_invalidate = True
                        break

            if should_invalidate:
                # Invalidate this fact by setting invalid_at
                logger.info(f"Invalidating fact: {edge.fact}")

                try:
                    # Update the edge with invalid_at timestamp
                    await self._invalidate_edge(edge, reference_time)
                    invalidated_count += 1
                except Exception as e:
                    logger.error(f"Failed to invalidate fact '{edge.fact}': {e}")

        logger.info(f"Invalidated {invalidated_count} contradicting facts")
        return invalidated_count

    async def _invalidate_edge(self, edge, invalid_at: datetime):
        """
        Set the invalid_at timestamp on an edge in Neo4j.

        Args:
            edge: The EntityEdge to invalidate
            invalid_at: Timestamp when fact became invalid
        """
        from neo4j import AsyncGraphDatabase
        import os

        # Get Neo4j connection from environment
        driver = AsyncGraphDatabase.driver(
            os.getenv('NEO4J_URI', 'bolt://192.168.1.97:17687'),
            auth=(os.getenv('NEO4J_USERNAME', 'neo4j'), os.getenv('NEO4J_PASSWORD', 'password123'))
        )

        async with driver.session() as session:
            # Update the edge's invalid_at field
            await session.run(
                """
                MATCH ()-[r]->()
                WHERE r.uuid = $uuid
                SET r.invalid_at = datetime($invalid_at)
                """,
                uuid=str(edge.uuid),
                invalid_at=invalid_at.isoformat()
            )

        await driver.close()
