from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path
from typing import Any, Dict, List

from htmlmin import minify
from jinja2 import Environment, FileSystemLoader
from ps2_analysis.enums import DamageLocation
from ps2_analysis.weapons.infantry.generate import generate_all_infantry_weapons
from ps2_analysis.weapons.infantry.infantry_weapon import InfantryWeapon
from ps2_analysis.weapons.vehicle.generate import generate_all_vehicle_weapons
from ps2_analysis.weapons.vehicle.vehicle_weapon import VehicleWeapon
from ps2_census.enums import Faction, ItemCategory

from .constants import (
    DATA_FILES_DIRECTORY,
    FACTION_BACKGROUND_COLORS,
    PAGES_DIRECTORY,
    SITE_DIRECTORY,
    TEMPLATE_EXTENSION,
    TEMPLATES_DIRECTORY,
)
from .jinja_filters import debug_filter, enum_name_filter, items_filter


def generate_predefined_pages(update_simulations: bool = True):

    infantry_weapons: List[InfantryWeapon] = generate_all_infantry_weapons(
        data_files_directory=DATA_FILES_DIRECTORY, no_children=True
    )

    faction_category_infantry_weapons: Dict[
        Faction, Dict[ItemCategory, List[InfantryWeapon]]
    ] = {
        faction: {
            category: list(fcw_it)
            for category, fcw_it in groupby(
                sorted(fw_it, key=lambda x: x.category), lambda x: x.category
            )
        }
        for faction, fw_it in groupby(
            sorted(infantry_weapons, key=lambda x: x.faction), lambda x: x.faction
        )
    }

    vehicle_weapons: List[VehicleWeapon] = generate_all_vehicle_weapons(
        data_files_directory=DATA_FILES_DIRECTORY, no_children=True
    )

    faction_category_vehicle_weapons: Dict[
        Faction, Dict[ItemCategory, List[VehicleWeapon]]
    ] = {
        faction: {
            category: list(fcw_it)
            for category, fcw_it in groupby(
                sorted(fw_it, key=lambda x: x.category), lambda x: x.category
            )
        }
        for faction, fw_it in groupby(
            sorted(vehicle_weapons, key=lambda x: x.faction), lambda x: x.faction
        )
    }

    j2_env: Environment = Environment(
        loader=FileSystemLoader((TEMPLATES_DIRECTORY, PAGES_DIRECTORY))
    )
    j2_env.filters["items"] = items_filter
    j2_env.filters["enum_name"] = enum_name_filter
    j2_env.filters["debug"] = debug_filter

    j2_context: Dict[str, Any] = {
        "DamageLocation": DamageLocation,
        "ItemCategory": ItemCategory,
        "faction_background_colors": FACTION_BACKGROUND_COLORS,
        "faction_category_infantry_weapons": faction_category_infantry_weapons,
        "faction_category_vehicle_weapons": faction_category_vehicle_weapons,
    }

    for page_path in Path(PAGES_DIRECTORY).rglob(f"*.{TEMPLATE_EXTENSION}"):

        page_dirs: List[str]
        page_filename: str
        _, *page_dirs, page_filename = page_path.parts

        source_template_path: Path = Path(*page_dirs, page_filename)

        output_dir: Path = Path(SITE_DIRECTORY, *page_dirs)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path: Path = output_dir.joinpath(f"{page_filename.split('.')[0]}.html")

        print(f"Creating {output_path}")

        with open(output_path, "w") as f:
            f.write(
                minify(
                    j2_env.get_template(str(source_template_path)).render(
                        **j2_context, **{"update_datetime": datetime.now(timezone.utc)}
                    )
                )
            )
