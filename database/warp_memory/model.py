from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase


class WarpMemoryDBModel(SQLAlchemyBase):
    """A table for warp tiles that are known to the Agent."""

    __tablename__ = "warp_memory"

    map_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    warp_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
