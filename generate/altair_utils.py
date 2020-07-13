from typing import List

import altair
from ps2_census.enums import Faction

# Axis
X: str = "x"
Y: str = "y"

# Faction
_FACTION_COLOR_DOMAIN: List[int] = [
    Faction.TERRAN_REPUBLIC.name,
    Faction.VANU_SOVEREIGNTY.name,
    Faction.NEW_CONGLOMERATE.name,
    Faction.NONE.name,
]
_FACTION_COLOR_RANGE: List[str] = ["red", "purple", "blue", "green"]

FACTION_SELECTION = altair.selection_multi(fields=["Faction"])
FACTION_COLOR = altair.condition(
    FACTION_SELECTION,
    altair.Color(
        "Faction:N",
        scale=altair.Scale(domain=_FACTION_COLOR_DOMAIN, range=_FACTION_COLOR_RANGE),
        legend=None,
    ),
    altair.value("lightgray"),
)

# Simulation point type
_SIMULATION_POINT_TYPE_COLOR_DOMAIN: List[str] = ["cursor", "pellet"]
_SIMULATION_POINT_TYPE_COLOR_RANGE: List[str] = ["red", "green"]

SIMULATION_POINT_TYPE_SELECTION = altair.selection_multi(fields=["Type"])
SIMULATION_POINT_TYPE_COLOR = altair.condition(
    SIMULATION_POINT_TYPE_SELECTION,
    altair.Color(
        "Type:N",
        scale=altair.Scale(
            domain=_SIMULATION_POINT_TYPE_COLOR_DOMAIN,
            range=_SIMULATION_POINT_TYPE_COLOR_RANGE,
        ),
        legend=None,
    ),
    altair.value("lightgray"),
)


def dark_theme():

    lightColor: str = "#fff"
    medColor: str = "#888"

    return {
        "config": {
            "background": "#343c3d",
            "title": {"color": lightColor},
            "style": {
                "guide-label": {"fill": lightColor},
                "guide-title": {"fill": lightColor},
            },
            "axis": {
                "domainColor": lightColor,
                "gridColor": medColor,
                "tickColor": lightColor,
            },
        }
    }
