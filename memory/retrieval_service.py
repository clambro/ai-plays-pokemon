import numpy as np

from common.constants import (
    DEFAULT_MIN_SEMANTIC_SIMILARITY,
    DEFAULT_NUM_MEMORIES_RETRIEVED,
    DEFAULT_RERANKING_FACTOR,
)
from common.embedding_service import GeminiEmbeddingService
from database.long_term_memory.repository import (
    get_all_long_term_memory_embeddings,
    get_long_term_memories,
)
from database.long_term_memory.schemas import LongTermMemoryRead

embedding_service = GeminiEmbeddingService()


class MemoryRetrievalService:
    """Service for retrieving long-term memories based on semantic similarity to a query."""

    def __init__(
        self,
        num_memories: int = DEFAULT_NUM_MEMORIES_RETRIEVED,
        reranking_factor: float = DEFAULT_RERANKING_FACTOR,
        min_semantic_similarity: float = DEFAULT_MIN_SEMANTIC_SIMILARITY,
    ) -> None:
        """
        Initialize the memory similarity service.

        :param num_memories: The number of memories to return.
        :param reranking_factor: The multiplier for determining how many more memories to pull
            before reranking.
        """
        if num_memories < 1:
            raise ValueError("Number of memories must be greater than 0")
        if reranking_factor < 1:
            raise ValueError("Reranking factor must be greater than 1")

        self.num_memories = num_memories
        self.num_to_rerank = int(self.num_memories * reranking_factor)
        self.min_semantic_similarity = min_semantic_similarity

    async def get_most_relevant_memories(
        self,
        query: str,
        iteration: int,
    ) -> list[LongTermMemoryRead]:
        """
        Get the most relevant memories to the `query`.

        :param query: The query to search for.
        :param iteration: The current iteration of the Agent.
        :return: A list of the `num_memories` most relevant memories to the `query`.
        """
        embeddings = await get_all_long_term_memory_embeddings()
        if len(embeddings) <= self.num_memories:
            return await get_long_term_memories(list(embeddings.keys()), iteration)

        query_embedding = await embedding_service.get_embedding(query)
        top_similarities = await self._get_top_n_semantic_similarity(query_embedding, embeddings)
        if not top_similarities:
            return []

        memories_to_rerank = await get_long_term_memories(list(top_similarities.keys()), iteration)
        if len(memories_to_rerank) <= self.num_memories:
            return memories_to_rerank

        return self._rerank_memories(iteration, memories_to_rerank, top_similarities)

    async def _get_top_n_semantic_similarity(
        self,
        query_embedding: list[float],
        memory_embeddings: dict[str, list[float]],
    ) -> dict[str, float]:
        """
        Get the IDs and semantic similarity of the most relevant memories to the query.

        :param query_embedding: The embedding of the query.
        :param memory_embeddings: The embeddings of the memories.
        :return: A dictionary of the IDs and semantic similarity of the most relevant memories to
            the query.
        """
        mem_ids, mem_embeddings = zip(*memory_embeddings.items(), strict=True)
        mem_embeddings = np.array(mem_embeddings)
        similarities = np.dot(query_embedding, mem_embeddings.T) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(mem_embeddings, axis=1)
        )
        top_n_ids = np.argsort(similarities)[-self.num_to_rerank :]
        return {
            mem_ids[i]: similarities[i]
            for i in top_n_ids
            if similarities[i] >= self.min_semantic_similarity
        }

    def _rerank_memories(
        self,
        iteration: int,
        memories: list[LongTermMemoryRead],
        top_similarities: dict[str, float],
    ) -> list[LongTermMemoryRead]:
        """
        Rerank the memories based on semantic similarity, recency, and importance.

        :param iteration: The current iteration of the Agent.
        :param memories: The memories to rerank.
        :param top_similarities: The semantic similarity of the memories to the query.
        :return: A list of the reranked memories.
        """
        scores = (
            (
                memory,
                top_similarities.get(memory.title, self.min_semantic_similarity)
                * memory.importance
                / max(memory.last_accessed_iteration - iteration, 1),
            )
            for memory in memories
        )
        reranked_memories = sorted(scores, key=lambda x: x[1], reverse=True)
        return [r[0] for r in reranked_memories]
