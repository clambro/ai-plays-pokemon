"""SQLAlchemy model for observed route transitions."""

from sqlalchemy import Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from common.enums import Button, MapId
from database.base import SQLAlchemyBase


class RouteTransitionDBModel(SQLAlchemyBase):
    """One directed map transition completed by player-controlled movement."""

    __tablename__ = "route_transition"

    source_map_id: Mapped[MapId] = mapped_column(Integer, primary_key=True)
    source_row: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_col: Mapped[int] = mapped_column(Integer, primary_key=True)
    button: Mapped[Button] = mapped_column(Enum(Button), primary_key=True)
    destination_map_id: Mapped[MapId] = mapped_column(Integer, primary_key=True)
    destination_row: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_col: Mapped[int] = mapped_column(Integer, primary_key=True)
    create_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
