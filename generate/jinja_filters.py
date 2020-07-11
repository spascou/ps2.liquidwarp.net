from enum import Enum
from typing import Any, List, Tuple

from ps2_analysis.enums import DamageLocation
from ps2_census.enums import (
    Faction,
    FireModeType,
    ItemCategory,
    PlayerState,
    ProjectileFlightType,
    ResistType,
    TargetType,
)

from .enum_resolvers import (
    damage_location_resolver,
    faction_resolver,
    fire_mode_type_resolver,
    item_category_resolver,
    player_state_resolver,
    projectile_flight_type_resolver,
    resist_type_resolver,
    target_type_resolver,
)


def items_filter(d: dict) -> List[Tuple[Any, Any]]:

    return list(d.items())


def enum_name_filter(e: Enum) -> str:

    if isinstance(e, Enum):

        if isinstance(e, Faction):

            return faction_resolver[e]

        elif isinstance(e, FireModeType):

            return fire_mode_type_resolver[e]

        elif isinstance(e, ItemCategory):

            return item_category_resolver[e]

        elif isinstance(e, ProjectileFlightType):

            return projectile_flight_type_resolver[e]

        elif isinstance(e, DamageLocation):

            return damage_location_resolver[e]

        elif isinstance(e, PlayerState):

            return player_state_resolver[e]

        elif isinstance(e, ResistType):

            return resist_type_resolver[e]

        elif isinstance(e, TargetType):

            return target_type_resolver[e]

        else:

            return e.name

    else:

        return str(e)
