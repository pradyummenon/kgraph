"""Domain error hierarchy for kgraph.

All exceptions raised by kgraph derive from KgraphError,
enabling callers to catch at the appropriate level of specificity.
Retryable errors are marked via RetryableError for use with tenacity.
"""

from __future__ import annotations


class KgraphError(Exception):
    """Base exception for all kgraph errors."""


class ExtractionError(KgraphError):
    """Raised when entity/relationship extraction from text fails."""


class EmbeddingError(KgraphError):
    """Raised when embedding generation fails."""


class GraphError(KgraphError):
    """Raised when a graph database operation fails."""


class ConfigError(KgraphError):
    """Raised when configuration is invalid or missing required values."""


class VisualizationError(KgraphError):
    """Raised when graph rendering or visualization fails."""


class RetryableError(KgraphError):
    """Marker base class for errors that are safe to retry via tenacity."""


class RateLimitError(RetryableError):
    """Raised when an external API returns a rate limit response."""


class ServiceUnavailableError(RetryableError):
    """Raised when an external service is temporarily unavailable."""
