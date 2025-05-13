from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase


class KnownWarpTable(SQLAlchemyBase):
    """A table for warp tiles that are known to the Agent."""

    __tablename__ = "known_warp"

    map_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    warp_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    destination: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
