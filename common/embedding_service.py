from google import genai
from google.genai.errors import ServerError
from google.genai.types import EmbedContentConfig
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from common.settings import settings

client = genai.Client(api_key=settings.gemini_api_key)
model = "gemini-embedding-001"  # The only one for now.


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(ServerError),
    reraise=True,
)
async def get_embedding(text: str, title: str | None = None) -> list[float]:
    """
    Get an embedding from the Gemini Embedding API.

    :param text: The text to get an embedding for.
    :param title: Optional title information to improve the embedding.
    :return: An embedding from the Gemini Embedding API.
    """
    response = await client.aio.models.embed_content(
        model=model,
        contents=text,
        config=EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            title=title,
            output_dimensionality=768,
        ),
    )
    if not response.embeddings:
        raise ValueError("No response from Gemini.")
    if len(response.embeddings) != 1:
        raise ValueError(f"Expected 1 embedding, got {len(response.embeddings)}")
    embedding = response.embeddings[0]
    if not embedding.values:
        raise ValueError("No values in embedding.")
    return embedding.values
