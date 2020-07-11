from typing import Dict, List

from ps2_census.enums import Faction

SITE_DIRECTORY: str = "site"
TEMPLATES_DIRECTORY: str = "templates"
PAGES_DIRECTORY: str = "pages"
STATICS_DIRECTORY: str = "statics"
DATA_FILES_DIRECTORY: str = "datafiles"
SIMULATIONS_DIRECTORY: str = "simulations"

TEMPLATE_EXTENSION: str = "html.jinja"

INFANTRY_WEAPON_STATS_TEMPLATE_PATH: str = "stats/infantry_weapon.html.jinja"
VEHICLE_WEAPON_STATS_TEMPLATE_PATH: str = "stats/vehicle_weapon.html.jinja"
CHART_TEMPLATE_PATH: str = "chart.html.jinja"


FIRE_GROUP_BACKGROUND_CLASSES: List[str] = [
    "has-background-primary",
    "has-background-success",
]

FIRE_MODE_BACKGROUND_CLASSES: List[str] = [
    "has-background-info",
    "has-background-warning",
]

FACTION_BACKGROUND_COLORS: Dict[Faction, str] = {
    Faction.NONE: "",
    Faction.VANU_SOVEREIGNTY: "#352c4f",
    Faction.NEW_CONGLOMERATE: "#1a2b3d",
    Faction.TERRAN_REPUBLIC: "#692b34",
    Faction.NS_OPERATIVES: "",
}
