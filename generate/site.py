import os
import shutil
import subprocess
from datetime import datetime, timezone
from enum import Enum
from itertools import groupby
from pathlib import Path
from typing import Any, Dict, List, Tuple

import altair
import altair_saver
from htmlmin import minify
from jinja2 import Environment, FileSystemLoader, Template
from ps2_analysis.fire_groups.damage_profile import DamageLocation
from ps2_analysis.fire_groups.data_files import (
    update_data_files as update_fire_groups_data_files,
)
from ps2_analysis.fire_groups.fire_group import FireGroup
from ps2_analysis.fire_groups.fire_mode import FireMode
from ps2_analysis.weapons.infantry.data_files import (
    update_data_files as update_infantry_weapons_data_files,
)
from ps2_analysis.weapons.infantry.generate import generate_infantry_weapons
from ps2_analysis.weapons.infantry.infantry_weapon import InfantryWeapon
from ps2_analysis.weapons.vehicle.data_files import (
    update_data_files as update_vehicle_weapons_data_files,
)
from ps2_analysis.weapons.vehicle.generate import generate_vehicle_weapons
from ps2_analysis.weapons.vehicle.vehicle_weapon import VehicleWeapon
from ps2_census.enums import (
    Faction,
    FireModeType,
    ItemCategory,
    PlayerState,
    ProjectileFlightType,
    ResistType,
    TargetType,
)

STATICS_FOLDER: str = "statics"
TEMPLATE_EXTENSION: str = "html.jinja"

INFANTRY_WEAPON_STATS_TEMPLATE_PATH: str = "stats/infantry_weapon.html.jinja"
VEHICLE_WEAPON_STATS_TEMPLATE_PATH: str = "stats/vehicle_weapon.html.jinja"

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


def _items_filter(d: dict) -> List[Tuple[Any, Any]]:
    return list(d.items())


def _enum_name_filter(e: Enum) -> str:
    if isinstance(e, Enum):
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
            ItemCategory.ROCKET_LAUNCHER: "Rocket launcher",
            ItemCategory.EXPLOSIVE: "Explosive",
            ItemCategory.GRENADE: "Grenade",
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
            ItemCategory.AERIAL_COMBAT_WEAPON: "Aerial combat weapon",
            ItemCategory.VEHICLE_WEAPONS: "Vehicle weapon",
            ItemCategory.FLASH_PRIMARY_WEAPON: "Flash primary",
            ItemCategory.GALAXY_LEFT_WEAPON: "Galaxy left",
            ItemCategory.GALAXY_TAIL_WEAPON: "Galazy tail",
            ItemCategory.GALAXY_RIGHT_WEAPON: "Galaxy right",
            ItemCategory.GALAXY_TOP_WEAPON: "Galaxy top",
            ItemCategory.HARASSER_TOP_GUNNER: "Harasser top",
            ItemCategory.LIBERATOR_BELLY_WEAPON: "Liberator belly",
            ItemCategory.LIBERATOR_NOSE_CANNON: "Liberator nose",
            ItemCategory.LIBERATOR_TAIL_WEAPON: "Liberator tail",
            ItemCategory.LIGHTNING_PRIMARY_WEAPON: "Lightning",
            ItemCategory.MAGRIDER_GUNNER_WEAPON: "Magrider gunner",
            ItemCategory.MAGRIDER_PRIMARY_WEAPON: "Magrider primary",
            ItemCategory.MOSQUITO_NOSE_CANNON: "Mosquito nose",
            ItemCategory.MOSQUITO_WING_MOUNT: "Mosquito wing",
            ItemCategory.PROWLER_GUNNER_WEAPON: "Prowler gunner",
            ItemCategory.PROWLER_PRIMARY_WEAPON: "Prowler primary",
            ItemCategory.REAVER_NOSE_CANNON: "Reaver nose",
            ItemCategory.REAVER_WING_MOUNT: "Reaver wing",
            ItemCategory.SCYTHE_NOSE_CANNON: "Scythe nose",
            ItemCategory.SCYTHE_WING_MOUNT: "Scythe wing",
            ItemCategory.SUNDERER_FRONT_GUNNER: "Sunderer front",
            ItemCategory.SUNDERER_REAR_GUNNER: "Sunderer rear",
            ItemCategory.VANGUARD_GUNNER_WEAPON: "Vanguard gunner",
            ItemCategory.VANGUARD_PRIMARY_WEAPON: "Vanguard primary",
            ItemCategory.VALKYRIE_NOSE_GUNNER: "Valkyrie nose",
            ItemCategory.ANT_TOP_TURRET: "Ant top",
            ItemCategory.BASTION_POINT_DEFENSE: "Bastion point defense",
            ItemCategory.BASTION_BOMBARD: "Bastion bombard",
            ItemCategory.BASTION_WEAPON_SYSTEM: "Bastion weapon system",
            ItemCategory.COLOSSUS_PRIMARY_WEAPON: "Colossus primary",
            ItemCategory.COLOSSUS_FRONT_RIGHT_WEAPON: "Colossus front right",
            ItemCategory.COLOSSUS_FRONT_LEFT_WEAPON: "Colossus front left",
            ItemCategory.COLOSSUS_REAR_RIGHT_WEAPON: "Colossus rear right",
            ItemCategory.COLOSSUS_REAR_LEFT_WEAPON: "Colossus rear left",
            ItemCategory.AA_MAX_RIGHT: "MAX AA right",
            ItemCategory.AA_MAX_LEFT: "MAX AA left",
            ItemCategory.AV_MAX_RIGHT: "MAX AV right",
            ItemCategory.AV_MAX_LEFT: "MAX AV left",
            ItemCategory.AI_MAX_RIGHT: "MAX AI right",
            ItemCategory.AI_MAX_LEFT: "MAX AI left",
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
            PlayerState.FALLING_LONG: "Falling long",
            PlayerState.CROUCH_WALKING: "Crouch walking",
            PlayerState.FALLING_SHORT: "Falling short",
            PlayerState.JUMPING: "Jumping",
        }
        resist_type_resolver: Dict[ResistType, str] = {
            ResistType.NONE: "None",
            ResistType.MELEE: "Melee",
            ResistType.SMALL_ARM: "Small arm",
            ResistType.HEAVY_MACHINE_GUN: "Heavy machine gun",
            ResistType.HEAVY_ANTI_ARMOR: "Heavy anti armor",
            ResistType.EXPLOSIVE: "Explosive",
            ResistType.TANK_SHELL: "Tank shell",
            ResistType.AIRCRAFT_MACHINE_GUN: "Aircraft machine gun",
            ResistType.ANTI_VEHICLE_MINE: "Anti-vehicle mine",
            ResistType.FLAK_EXPLOSIVE_BLAST: "Flak explosive blast",
            ResistType.ANTI_AIRCRAFT_MACHINE_GUN: "Anti aircraft machine gun",
            ResistType.AIR_TO_GROUND_WARHEAD: "Air to ground warhead",
            ResistType.ARMOR_PIERCING_CHAIN_GUN: "Armor-piercing chain gun",
            ResistType.DEFAULT_ROCKET_LAUNCHER: "Rocket launcher",
            ResistType.ANTI_MATERIEL_RIFLE: "Anti-materiel rifle",
            ResistType.WHALE_HUNTER: "Whale hunter",
            ResistType.CORE_EXPLOSION: "Core explosion",
        }
        target_type_resolver: Dict[TargetType, str] = {
            TargetType.SELF: "Self",
            TargetType.ANY: "Any",
            TargetType.ENEMY: "Enemy",
            TargetType.ALLY: "Ally",
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
        elif isinstance(e, ResistType):
            return resist_type_resolver[e]
        elif isinstance(e, TargetType):
            return target_type_resolver[e]
        else:
            return e.name
    else:
        return str(e)


def clean_site(directory: str):
    print("Cleaning site")
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)

        print(f"Deleting {filepath}")

        try:
            shutil.rmtree(filepath)
        except OSError:
            os.remove(filepath)


def generate_site(
    templates_directory: str,
    pages_directory: str,
    statics_directory: str,
    data_files_directory: str,
    output_directory: str,
    census_service_id: str,
    no_simulations: bool = False,
):
    print("Updating site")

    update_datetime: datetime = datetime.now(timezone.utc)

    # Update data files
    update_fire_groups_data_files(
        directory=data_files_directory, service_id=census_service_id,
    )

    update_infantry_weapons_data_files(
        directory=data_files_directory, service_id=census_service_id,
    )

    update_vehicle_weapons_data_files(
        directory=data_files_directory, service_id=census_service_id,
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

    vehicle_weapons: List[VehicleWeapon] = generate_vehicle_weapons(
        data_files_directory=data_files_directory
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

    # Altair dark theme
    altair.themes.enable("dark")

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
        "ItemCategory": ItemCategory,
        "update_datetime": update_datetime,
        "faction_background_colors": FACTION_BACKGROUND_COLORS,
        "faction_category_infantry_weapons": faction_category_infantry_weapons,
        "faction_category_vehicle_weapons": faction_category_vehicle_weapons,
        "fire_group_background_classes": FIRE_GROUP_BACKGROUND_CLASSES,
        "fire_mode_background_classes": FIRE_MODE_BACKGROUND_CLASSES,
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

        with open(output_path, "w") as f:
            f.write(
                minify(
                    j2_env.get_template(str(source_template_path)).render(**j2_context)
                )
            )

    # Dynamically generated pages
    # Infantry weapons stats
    infantry_weapon_stats_template: Template = j2_env.get_template(
        INFANTRY_WEAPON_STATS_TEMPLATE_PATH
    )

    infantry_weapon_stats_output_dir: Path = Path(
        output_directory, "stats", "infantry-weapons"
    )

    infantry_weapon_stats_output_dir.mkdir(parents=True, exist_ok=True)

    ifw_sim_path: Path = Path(
        STATICS_FOLDER, "images", "simulations", "infantry-weapons"
    )
    ifw_sim_output_dir: Path = Path(output_directory).joinpath(ifw_sim_path)
    ifw_sim_output_dir.mkdir(parents=True, exist_ok=True)

    wp: InfantryWeapon
    for wp in infantry_weapons:

        # Generate shooting simulations

        if wp.category not in {
            ItemCategory.EXPLOSIVE,
            ItemCategory.GRENADE,
            ItemCategory.KNIFE,
            ItemCategory.ROCKET_LAUNCHER,
        }:

            fg: FireGroup
            for fg in wp.fire_groups:

                fm: FireMode
                for fm in fg.fire_modes:

                    if fm.ammo or fm.heat:

                        i_w_sim_filename: str = f"{wp.slug}-{wp.item_id}-fg{fg.fire_group_id}-fm{fm.fire_mode_id}-magdump.png"

                        i_w_sim_path: Path = ifw_sim_path.joinpath(i_w_sim_filename)

                        i_w_sim_output_path: Path = (
                            ifw_sim_output_dir.joinpath(i_w_sim_filename)
                        )

                        if no_simulations is False:

                            print(f"Creating {i_w_sim_output_path}")

                            c: altair.HConcatChart = fm.generate_altair_simulation(
                                shots=fm.max_consecutive_shots,
                                runs=100,
                                recentering=False,
                            )

                            altair_saver.save(c, str(i_w_sim_output_path))

                        fm.simulation_image_path = "/" + str(i_w_sim_path)

        i_w_s_output_path: Path = (
            infantry_weapon_stats_output_dir.joinpath(f"{wp.slug}-{wp.item_id}.html")
        )

        print(f"Creating {i_w_s_output_path}")

        with open(i_w_s_output_path, "w") as f:
            f.write(
                minify(
                    infantry_weapon_stats_template.render(
                        **j2_context, **{"weapon": wp}
                    )
                )
            )

    # Vehicle weapons stats
    vehicle_weapon_stats_template: Template = j2_env.get_template(
        VEHICLE_WEAPON_STATS_TEMPLATE_PATH
    )

    vehicle_weapon_stats_output_dir: Path = Path(
        output_directory, "stats", "vehicle-weapons"
    )

    vehicle_weapon_stats_output_dir.mkdir(parents=True, exist_ok=True)

    v: VehicleWeapon
    for v in vehicle_weapons:
        i_v_s_output_path: Path = (
            vehicle_weapon_stats_output_dir.joinpath(f"{v.slug}-{v.item_id}.html")
        )

        print(f"Creating {i_v_s_output_path}")

        with open(i_v_s_output_path, "w") as f:
            f.write(
                minify(
                    vehicle_weapon_stats_template.render(**j2_context, **{"weapon": v})
                )
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
