from typing import Dict

from ps2_census.enums import Faction

SITE_DIRECTORY: str = "site"
TEMPLATES_DIRECTORY: str = "templates"
PAGES_DIRECTORY: str = "pages"
STATICS_DIRECTORY: str = "statics"
DATA_FILES_DIRECTORY: str = "datafiles"
SIMULATIONS_DIRECTORY: str = "simulations"

TEMPLATE_EXTENSION: str = "html.jinja"

INFANTRY_WEAPON_STATS_TEMPLATE_PATH: str = "stats/weapons/infantry.html.jinja"
VEHICLE_WEAPON_STATS_TEMPLATE_PATH: str = "stats/weapons/vehicle.html.jinja"
CHART_TEMPLATE_PATH: str = "chart.html.jinja"

FACTION_BACKGROUND_COLOR_CLASSES: Dict[Faction, str] = {
    Faction.NONE: "has-background-no-faction",
    Faction.VANU_SOVEREIGNTY: "has-background-vs",
    Faction.NEW_CONGLOMERATE: "has-background-nc",
    Faction.TERRAN_REPUBLIC: "has-background-tr",
    Faction.NS_OPERATIVES: "has-background-no-faction",
}

CURSOR: str = "cursor"
PELLET: str = "pellet"

PRECISION_DECIMALS: int = 3
