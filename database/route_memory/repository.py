"""Persistence operations for observed route transitions."""

from sqlalchemy import select

from common.schemas import Coords
from database.db_config import db_sessionmaker
from database.route_memory.model import RouteTransitionDBModel
from database.route_memory.schemas import RouteTransitionCreate, RouteTransitionRead


async def create_route_transition(
    iteration: int,
    transition: RouteTransitionCreate,
) -> None:
    """Persist a directed transition once, retaining its first observation."""
    identity = (
        transition.source_map_id,
        transition.source_coords.row,
        transition.source_coords.col,
        transition.button,
        transition.destination_map_id,
        transition.destination_coords.row,
        transition.destination_coords.col,
    )
    async with db_sessionmaker.begin() as session:
        if await session.get(RouteTransitionDBModel, identity) is None:
            session.add(
                RouteTransitionDBModel(
                    source_map_id=transition.source_map_id,
                    source_row=transition.source_coords.row,
                    source_col=transition.source_coords.col,
                    button=transition.button,
                    warp_activation=transition.warp_activation,
                    destination_map_id=transition.destination_map_id,
                    destination_row=transition.destination_coords.row,
                    destination_col=transition.destination_coords.col,
                    create_iteration=iteration,
                )
            )


async def get_route_transitions() -> list[RouteTransitionRead]:
    """Load observed transitions in deterministic first-seen order."""
    async with db_sessionmaker() as session:
        query = select(RouteTransitionDBModel).order_by(
            RouteTransitionDBModel.create_iteration,
            RouteTransitionDBModel.source_map_id,
            RouteTransitionDBModel.source_row,
            RouteTransitionDBModel.source_col,
            RouteTransitionDBModel.button,
            RouteTransitionDBModel.destination_map_id,
            RouteTransitionDBModel.destination_row,
            RouteTransitionDBModel.destination_col,
        )
        transitions = (await session.execute(query)).scalars().all()

    return [
        RouteTransitionRead(
            source_map_id=transition.source_map_id,
            source_coords=Coords(row=transition.source_row, col=transition.source_col),
            button=transition.button,
            warp_activation=transition.warp_activation,
            destination_map_id=transition.destination_map_id,
            destination_coords=Coords(
                row=transition.destination_row,
                col=transition.destination_col,
            ),
            create_iteration=transition.create_iteration,
        )
        for transition in transitions
    ]
