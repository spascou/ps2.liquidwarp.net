import os
import shutil
import subprocess
from datetime import datetime, timezone
from enum import Enum
from itertools import groupby
from pathlib import Path
from typing import Any, Dict, List, Tuple

from jinja2 import Environment, FileSystemLoader, Template
from ps2_analysis.data_file import DataFile, update_data_file
from ps2_analysis.infantry_weapons.damage_profile import DamageLocation
from ps2_analysis.infantry_weapons.generate import generate_infantry_weapons
from ps2_analysis.infantry_weapons.infantry_weapon import InfantryWeapon
from ps2_census.enums import (
    Faction,
    FireModeType,
    ItemCategory,
    PlayerState,
    ProjectileFlightType,
)

STATICS_FOLDER: str = "statics"
TEMPLATE_EXTENSION: str = "html.jinja"

INFANTRY_WEAPON_STATS_TEMPLATE_PATH: str = "stats/infantry_weapon.html.jinja"


def _items_filter(d: dict) -> List[Tuple[Any, Any]]:
    return list(d.items())


def _enum_name_filter(e: Enum) -> str:
    faction_resolver: Dict[Faction, str] = {
        Faction.NONE: "No faction",
        Faction.VANU_SOVEREIGNTY: "Vanu Sovereignty",
        Faction.NEW_CONGLOMERATE: "New Conglomerate",
        Faction.TERRAN_REPUBLIC: "Terran Republic",
        Faction.NS_OPERATIVES: "NS Operatives",
    }
    fire_mode_type_resolver: Dict[FireModeType, str] = {
        FireModeType.PROJECTILE: "Hip fire",
        FireModeType.IRON_SIGHT: "ADS",
        FireModeType.MELEE: "Melee",
        FireModeType.TRIGGER_ITEM_ABILITY: "Item ability",
        FireModeType.THROWN: "Throw",
    }
    item_category_resolver: Dict[ItemCategory, str] = {
        ItemCategory.KNIFE: "Knife",
        ItemCategory.PISTOL: "Pistol",
        ItemCategory.SHOTGUN: "Shotgun",
        ItemCategory.SMG: "SMG",
        ItemCategory.LMG: "LMG",
        ItemCategory.ASSAULT_RIFLE: "Assault rifle",
        ItemCategory.CARBINE: "Carbine",
        ItemCategory.SNIPER_RIFLE: "Sniper rifle",
        ItemCategory.SCOUT_RIFLE: "Scout rifle",
        ItemCategory.HEAVY_WEAPON: "Heavy weapon",
        ItemCategory.BATTLE_RIFLE: "Battle rifle",
        ItemCategory.CROSSBOW: "Crossbow",
        ItemCategory.HYBRID_RIFLE: "Hybrid rifle",
    }
    projectile_flight_type_resolver: Dict[ProjectileFlightType, str] = {
        ProjectileFlightType.BALLISTIC: "Ballistic",
        ProjectileFlightType.TRUE_BALLISTIC: "True ballistic",
        ProjectileFlightType.DYNAMIC: "Dynamic",
        ProjectileFlightType.PROXIMITY_DETONATE: "Proximity detonate",
    }
    damage_location_resolver: Dict[DamageLocation, str] = {
        DamageLocation.HEAD: "Head",
        DamageLocation.TORSO: "Body",
        DamageLocation.LEGS: "Legs",
    }
    player_state_resolver: Dict[PlayerState, str] = {
        PlayerState.STANDING: "Standing",
        PlayerState.CROUCHING: "Crouching",
        PlayerState.RUNNING: "Running",
        PlayerState.SPRINTING: "Sprinting",
        PlayerState.FALLING_LONG: "Falling",
        PlayerState.CROUCH_WALKING: "Crouch walking",
    }

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
    else:
        return e.name


def clean_site(directory: str):
    print("Cleaning site")
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)

        print(f"Deleting {filepath}")

        try:
            shutil.rmtree(filepath)
        except OSError:
            os.remove(filepath)


def update_site(
    templates_directory: str,
    pages_directory: str,
    statics_directory: str,
    data_files_directory: str,
    output_directory: str,
    census_service_id: str,
):
    print("Updating site")

    update_datetime: datetime = datetime.now(timezone.utc)

    # Update data files
    update_data_file(
        data_file=DataFile.INFANTRY_WEAPONS,
        directory=data_files_directory,
        service_id=census_service_id,
    )

    # Generate data sets
    infantry_weapons: List[InfantryWeapon] = generate_infantry_weapons(
        data_files_directory=data_files_directory
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

    # Generate CSS
    subprocess.check_call("npm run css-build", shell=True)

    # Create the jinja2 environment
    j2_env: Environment = Environment(
        loader=FileSystemLoader((templates_directory, pages_directory))
    )
    j2_env.filters["items"] = _items_filter
    j2_env.filters["enum_name"] = _enum_name_filter

    j2_context: Dict[str, Any] = {
        "DamageLocation": DamageLocation,
        "update_datetime": update_datetime,
        "faction_category_infantry_weapons": faction_category_infantry_weapons,
    }

    # Generate pages
    # Pre-defined pages
    for page_path in Path(pages_directory).rglob(f"*.{TEMPLATE_EXTENSION}"):
        page_dirs: List[str]
        page_filename: str
        _, *page_dirs, page_filename = page_path.parts

        source_template_path: Path = Path(*page_dirs, page_filename)

        output_dir: Path = Path(output_directory, *page_dirs)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path: Path = output_dir.joinpath(f"{page_filename.split('.')[0]}.html")

        print(f"Creating {output_path}")

        j2_env.get_template(str(source_template_path)).stream(**j2_context).dump(
            str(output_path)
        )

    # Dynamically generated pages
    infantry_weapon_stats_template: Template = j2_env.get_template(
        INFANTRY_WEAPON_STATS_TEMPLATE_PATH
    )

    infantry_weapon_stats_output_dir: Path = Path(
        output_directory, "stats", "infantry-weapons"
    )

    infantry_weapon_stats_output_dir.mkdir(parents=True, exist_ok=True)

    w: InfantryWeapon
    for w in infantry_weapons:
        i_w_s_output_path: Path = (
            infantry_weapon_stats_output_dir.joinpath(f"{w.slug}-{w.item_id}.html")
        )

        print(f"Creating {i_w_s_output_path}")

        infantry_weapon_stats_template.stream(**j2_context, **{"weapon": w}).dump(
            str(i_w_s_output_path)
        )

    # Copy statics
    for static_path in Path(statics_directory).rglob("*"):

        if not os.path.isfile(static_path):
            continue

        static_dirs: List[str]
        static_filename: str
        _, *static_dirs, static_filename = static_path.parts

        destination_dir: Path = Path(output_directory, STATICS_FOLDER, *static_dirs)
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination_path: Path = destination_dir.joinpath(static_filename)

        print(f"Copying {destination_path}")

        shutil.copyfile(static_path, destination_path)
