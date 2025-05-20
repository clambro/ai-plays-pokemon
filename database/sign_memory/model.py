from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import SQLAlchemyBase
from emulator.enums import MapLocation


class SignMemoryDBModel(SQLAlchemyBase):
    """A table for sign tiles that are known to the Agent."""

    __tablename__ = "sign_memory"

    map_id: Mapped[MapLocation] = mapped_column(Integer, primary_key=True, index=True)
    sign_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    create_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    update_iteration: Mapped[int] = mapped_column(Integer, nullable=False)
