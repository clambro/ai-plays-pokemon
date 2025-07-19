from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from common.enums import BlockedDirection, MapId
from common.schemas import Coords


class MapMemoryCreateUpdate(BaseModel):
    """Create/update model for a map memory."""

    map_id: MapId
    tiles: str
    blockages: dict[str, BlockedDirection]
    iteration: int

    @model_validator(mode="before")
    @classmethod
    def _from_coords(cls, data: Any) -> Any:  # noqa: ANN401
        """Turn the coordinates into strings. The DB doesn't support tuples."""
        if "blockages" in data and isinstance(data["blockages"], dict):
            data["blockages"] = {str(coord): block for coord, block in data["blockages"].items()}
        return data


class MapMemoryRead(BaseModel):
    """Read model for a map memory."""

    map_id: MapId
    tiles: str
    blockages: dict[Coords, BlockedDirection]

    model_config = ConfigDict(from_attributes=True)
