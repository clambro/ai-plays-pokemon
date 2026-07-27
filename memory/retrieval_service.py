"""Long-term memory retrieval and ranking."""

from typing import TYPE_CHECKING

import numpy as np

from common.constants import (
    DEFAULT_MIN_SEMANTIC_SIMILARITY,
    DEFAULT_NUM_MEMORIES_RETRIEVED,
    DEFAULT_RERANKING_FACTOR,
)
from common.embedding_service import get_embedding
from database.long_term_memory.repository import (
    get_all_long_term_memory_embeddings,
    get_long_term_memories,
)

if TYPE_CHECKING:
    from database.long_term_memory.schemas import LongTermMemoryRead


async def get_most_relevant_memories(
    query: str,
    iteration: int,
    *,
    num_memories: int = DEFAULT_NUM_MEMORIES_RETRIEVED,
    reranking_factor: float = DEFAULT_RERANKING_FACTOR,
    min_semantic_similarity: float = DEFAULT_MIN_SEMANTIC_SIMILARITY,
) -> list[LongTermMemoryRead]:
    """Get the long-term memories most relevant to a query.

    Args:
        query: Semantic search query.
        iteration: Current agent iteration used to update memory access times.
        num_memories: Maximum number of memories to return.
        reranking_factor: Multiplier controlling how many semantic matches are reranked.
        min_semantic_similarity: Minimum cosine similarity accepted as a candidate.

    Returns:
        Up to ``num_memories`` memories ordered by combined relevance, recency, and importance.

    Raises:
        ValueError: ``num_memories`` or ``reranking_factor`` is less than one.
    """
    if num_memories < 1:
        raise ValueError("Number of memories must be greater than 0")
    if reranking_factor < 1:
        raise ValueError("Reranking factor must be greater than 1")

    embeddings = await get_all_long_term_memory_embeddings()
    if len(embeddings) <= num_memories:
        return await get_long_term_memories(list(embeddings.keys()), iteration)

    query_embedding = await get_embedding(query)
    top_similarities = _get_top_n_semantic_similarity(
        query_embedding,
        embeddings,
        num_to_rerank=int(num_memories * reranking_factor),
        min_semantic_similarity=min_semantic_similarity,
    )
    if not top_similarities:
        return []

    memories_to_rerank = await get_long_term_memories(list(top_similarities.keys()), iteration)
    if len(memories_to_rerank) <= num_memories:
        return memories_to_rerank

    reranked_memories = _rerank_memories(
        iteration,
        memories_to_rerank,
        top_similarities,
        min_semantic_similarity=min_semantic_similarity,
    )
    return reranked_memories[:num_memories]


def _get_top_n_semantic_similarity(
    query_embedding: list[float],
    memory_embeddings: dict[str, list[float]],
    *,
    num_to_rerank: int,
    min_semantic_similarity: float,
) -> dict[str, float]:
    """Get the memory IDs with the highest semantic similarity to a query.

    Args:
        query_embedding: Embedding of the retrieval query.
        memory_embeddings: Memory embeddings keyed by title.
        num_to_rerank: Maximum number of similarity matches to retain.
        min_semantic_similarity: Minimum cosine similarity accepted as a candidate.

    Returns:
        Retained memory titles mapped to their cosine similarity.
    """
    mem_ids, mem_embeddings = zip(*memory_embeddings.items(), strict=True)
    mem_embeddings = np.array(mem_embeddings)
    similarities = np.dot(query_embedding, mem_embeddings.T) / (
        np.linalg.norm(query_embedding) * np.linalg.norm(mem_embeddings, axis=1)
    )
    top_n_ids = np.argsort(similarities)[-num_to_rerank:]
    return {
        mem_ids[i]: similarities[i] for i in top_n_ids if similarities[i] >= min_semantic_similarity
    }


def _rerank_memories(
    iteration: int,
    memories: list[LongTermMemoryRead],
    top_similarities: dict[str, float],
    *,
    min_semantic_similarity: float,
) -> list[LongTermMemoryRead]:
    """Rerank memories by semantic similarity, recency, and importance.

    Args:
        iteration: Current agent iteration used to calculate recency.
        memories: Candidate memories to rerank.
        top_similarities: Cosine similarities keyed by memory title.
        min_semantic_similarity: Fallback similarity for a candidate missing from the mapping.

    Returns:
        Candidate memories ordered by descending combined score.
    """
    scores = (
        (
            memory,
            top_similarities.get(memory.title, min_semantic_similarity)
            * memory.importance
            / max(memory.last_accessed_iteration - iteration, 1),
        )
        for memory in memories
    )
    reranked_memories = sorted(scores, key=lambda x: x[1], reverse=True)
    return [r[0] for r in reranked_memories]
