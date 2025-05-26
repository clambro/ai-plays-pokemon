import numpy as np
from pydantic import UUID4, BaseModel

from common.embedding_service import GeminiEmbeddingService
from database.long_term_memory.repository import (
    get_all_long_term_memory_embeddings,
    get_long_term_memories_by_ids,
)
from database.long_term_memory.schemas import LongTermMemoryRead

embedding_service = GeminiEmbeddingService()


class MemoryRetrievalService(BaseModel):
    """Service for getting the semantic similarity between a query and a memory."""

    def __init__(self, iteration: int, num_memories: int, reranking_factor: float) -> None:
        """
        Initialize the memory similarity service.

        :param iteration: The current iteration of the Agent.
        :param num_memories: The number of memories to return.
        :param reranking_factor: The multiplier for determining how many more memories to pull
            before reranking.
        """
        if iteration < 0:
            raise ValueError("Iteration must be greater than 0")
        if num_memories < 1:
            raise ValueError("Number of memories must be greater than 0")
        if reranking_factor < 1:
            raise ValueError("Reranking factor must be greater than 1")

        self.iteration = iteration
        self.num_memories = num_memories
        self.num_to_rerank = int(self.num_memories * reranking_factor)

    async def get_most_relevant_memories(self, query: str) -> list[LongTermMemoryRead]:
        """
        Get the most relevant memories to the `query`.

        :param query: The query to search for.
        :param num_memories: The number of memories to return.
        :return: A list of the `num_memories` most relevant memories to the `query`.
        """
        embeddings = await get_all_long_term_memory_embeddings()
        if len(embeddings) <= self.num_memories:
            return await get_long_term_memories_by_ids(list(embeddings.keys()))

        query_embedding = await embedding_service.get_embedding(query)
        top_similarities = await self._get_top_n_semantic_similarity(query_embedding, embeddings)
        memories_to_rerank = await get_long_term_memories_by_ids(list(top_similarities.keys()))

        return self._rerank_memories(memories_to_rerank, top_similarities)

    async def _get_top_n_semantic_similarity(
        self,
        query_embedding: list[float],
        memory_embeddings: dict[UUID4, list[float]],
    ) -> dict[UUID4, float]:
        """
        Get the IDs and semantic similarity of the most relevant memories to the query.

        :param query_embedding: The embedding of the query.
        :param memory_embeddings: The embeddings of the memories.
        :return: A dictionary of the IDs and semantic similarity of the most relevant memories to
            the query.
        """
        mem_ids, mem_embeddings = zip(*memory_embeddings.items())
        mem_embeddings = np.array(mem_embeddings)
        similarities = np.dot(query_embedding, mem_embeddings) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(mem_embeddings, axis=1)
        )
        top_n_ids = np.argsort(similarities)[-self.num_to_rerank :]
        return {mem_ids[i]: similarities[i] for i in top_n_ids}

    def _rerank_memories(
        self,
        memories: list[LongTermMemoryRead],
        top_similarities: dict[UUID4, float],
    ) -> list[LongTermMemoryRead]:
        """
        Rerank the memories based on semantic similarity, recency, and importance.

        :param memories: The memories to rerank.
        :param top_similarities: The semantic similarity of the memories to the query.
        :return: A list of the reranked memories.
        """
        scores = (
            (
                memory,
                top_similarities.get(memory.id, 0)
                * memory.importance
                / max((memory.last_accessed_iteration - self.iteration), 1),
            )
            for memory in memories
        )
        reranked_memories = sorted(scores, key=lambda x: x[1], reverse=True)
        return [r[0] for r in reranked_memories]
