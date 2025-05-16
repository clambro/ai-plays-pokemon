from datetime import datetime

from database.db_config import db_sessionmaker
from database.llm_messages.model import LLMMessageDBModel
from database.llm_messages.schemas import LLMMessageCreate


async def create_llm_message(llm_message: LLMMessageCreate) -> None:
    """Create a new LLM message."""
    async with db_sessionmaker() as session:
        db_obj = LLMMessageDBModel(
            model=llm_message.model,
            prompt=llm_message.prompt,
            response=llm_message.response,
            prompt_tokens=llm_message.prompt_tokens,
            thought_tokens=llm_message.thought_tokens,
            response_tokens=llm_message.response_tokens,
            created_at=datetime.now(),
        )
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
