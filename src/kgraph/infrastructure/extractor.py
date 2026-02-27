"""Entity and relationship extraction using LLM structured output.

Supports Anthropic Claude (tool use) and Google Gemini (JSON mode)
for extracting entities and relationships with schema compliance.
"""

from __future__ import annotations

import json

import anthropic
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

from kgraph.domain.models import Chunk, Entity, ExtractionResult, Relationship


class ExtractedEntity(BaseModel):
    """Schema for extracted entity (used in Claude tool call)."""

    name: str
    entity_type: str
    description: str


class ExtractedRelationship(BaseModel):
    """Schema for extracted relationship (used in Claude tool call)."""

    source: str
    target: str
    relationship_type: str
    description: str


class ExtractionOutput(BaseModel):
    """Schema for the full extraction output."""

    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]


EXTRACTION_TOOL = {
    "name": "extract_knowledge",
    "description": (
        "Extract entities and relationships from the provided text. "
        "Identify all notable people, organizations, concepts, locations, "
        "events, and their relationships."
    ),
    "input_schema": ExtractionOutput.model_json_schema(),
}

EXTRACTION_SYSTEM = """You are a knowledge graph extraction engine. Given a text chunk, extract:

1. **Entities**: Notable people, organizations, concepts, locations, events, technologies, etc.
   - Use UPPERCASE types: PERSON, ORGANIZATION, CONCEPT, LOCATION, EVENT, TECHNOLOGY, etc.
   - Write concise but informative descriptions (one sentence).
   - Use canonical names (full names, official titles).

2. **Relationships**: Connections between entities.
   - Use UPPERCASE relationship types: WORKS_AT, PART_OF, CAUSES, RELATES_TO, CREATED, USES, etc.
   - Source and target must match entity names exactly.
   - Description should provide context from the text.

Be thorough but precise. Only extract what's clearly stated or strongly implied.
Do not invent entities or relationships not supported by the text."""


class ClaudeExtractor:
    """Extracts entities and relationships using Claude structured output."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def extract(self, chunk: Chunk) -> ExtractionResult:
        """Extract entities and relationships from a text chunk.

        Args:
            chunk: Text chunk with provenance metadata.

        Returns:
            ExtractionResult with entities and relationships.
        """
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=EXTRACTION_SYSTEM,
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_knowledge"},
            messages=[
                {
                    "role": "user",
                    "content": f"Extract entities and relationships from this text:\n\n{chunk.text}",
                }
            ],
        )

        # Parse the tool use response
        entities: list[Entity] = []
        relationships: list[Relationship] = []

        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_knowledge":
                output = ExtractionOutput.model_validate(block.input)

                entities = [
                    Entity(
                        name=e.name,
                        entity_type=e.entity_type,
                        description=e.description,
                        source=chunk.source_reference,
                    )
                    for e in output.entities
                ]

                relationships = [
                    Relationship(
                        source=r.source,
                        target=r.target,
                        relationship_type=r.relationship_type,
                        description=r.description,
                    )
                    for r in output.relationships
                ]

        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            source_chunk=chunk,
        )


class GeminiExtractor:
    """Extracts entities and relationships using Google Gemini's JSON mode."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def extract(self, chunk: Chunk) -> ExtractionResult:
        """Extract entities and relationships from a text chunk.

        Uses Gemini's structured JSON output with the same schema
        as the Claude extractor for consistency.
        """
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=f"Extract entities and relationships from this text:\n\n{chunk.text}",
            config=genai_types.GenerateContentConfig(
                system_instruction=EXTRACTION_SYSTEM,
                response_mime_type="application/json",
                response_schema=ExtractionOutput,
                temperature=0.0,
            ),
        )

        # Parse the JSON response
        entities: list[Entity] = []
        relationships: list[Relationship] = []

        try:
            output = ExtractionOutput.model_validate_json(response.text)

            entities = [
                Entity(
                    name=e.name,
                    entity_type=e.entity_type,
                    description=e.description,
                    source=chunk.source_reference,
                )
                for e in output.entities
            ]

            relationships = [
                Relationship(
                    source=r.source,
                    target=r.target,
                    relationship_type=r.relationship_type,
                    description=r.description,
                )
                for r in output.relationships
            ]
        except (json.JSONDecodeError, Exception):
            # If parsing fails, return empty result rather than crashing
            pass

        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            source_chunk=chunk,
        )
