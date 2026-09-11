"""SQLAlchemy model for warp memory."""

from sqlalchemy import Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from common.enums import MapId, WarpActivation
from database.base import SQLAlchemyBase


class WarpMemoryDBModel(SQLAlchemyBase):
    """One observed route between a source warp and a destination warp."""

    __tablename__ = "warp_memory"

    map_id: Mapped[MapId] = mapped_column(Integer, primary_key=True, index=True)
    warp_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    col: Mapped[int] = mapped_column(Integer, nullable=False)
    destination_map_id: Mapped[MapId] = mapped_column(Integer, primary_key=True)
    destination_warp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activation: Mapped[WarpActivation] = mapped_column(Enum(WarpActivation), nullable=False)
    last_used_iteration: Mapped[int | None] = mapped_column(Integer, nullable=True)
