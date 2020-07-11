import os
import shutil
import subprocess
from datetime import datetime, timezone
from itertools import groupby
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, Iterator, List

import altair
import altair_saver
from htmlmin import minify
from jinja2 import Environment, FileSystemLoader, Template
from ps2_analysis.enums import DamageLocation
from ps2_analysis.fire_groups.data_files import (
    load_data_files as load_fire_groups_data_files,
)
from ps2_analysis.fire_groups.data_files import (
    update_data_files as update_fire_groups_data_files,
)
from ps2_analysis.fire_groups.fire_group import FireGroup
from ps2_analysis.fire_groups.fire_mode import FireMode
from ps2_analysis.weapons.infantry.data_files import (
    load_data_files as load_infantry_weapons_data_files,
)
from ps2_analysis.weapons.infantry.data_files import (
    update_data_files as update_infantry_weapons_data_files,
)
from ps2_analysis.weapons.infantry.generate import (
    EXCLUDED_ITEM_IDS as INFANTRY_WEAPONS_EXCLUDED_ITEM_IDS,
)
from ps2_analysis.weapons.infantry.generate import (
    generate_all_infantry_weapons,
    parse_infantry_weapon_data,
)
from ps2_analysis.weapons.infantry.infantry_weapon import InfantryWeapon
from ps2_analysis.weapons.vehicle.data_files import (
    load_data_files as load_vehicle_weapons_data_files,
)
from ps2_analysis.weapons.vehicle.data_files import (
    update_data_files as update_vehicle_weapons_data_files,
)
from ps2_analysis.weapons.vehicle.generate import (
    EXCLUDED_ITEM_IDS as VEHICLE_WEAPONS_EXCLUDED_ITEM_IDS,
)
from ps2_analysis.weapons.vehicle.generate import (
    generate_all_vehicle_weapons,
    parse_vehicle_weapon_data,
)
from ps2_analysis.weapons.vehicle.vehicle_weapon import VehicleWeapon
from ps2_census.enums import Faction, ItemCategory

from .altair_utils import dark_theme
from .constants import (
    CHART_TEMPLATE_PATH,
    DATA_FILES_DIRECTORY,
    FACTION_BACKGROUND_COLORS,
    FIRE_GROUP_BACKGROUND_CLASSES,
    FIRE_MODE_BACKGROUND_CLASSES,
    INFANTRY_WEAPON_STATS_TEMPLATE_PATH,
    PAGES_DIRECTORY,
    SIMULATIONS_DIRECTORY,
    SITE_DIRECTORY,
    STATICS_DIRECTORY,
    TEMPLATE_EXTENSION,
    TEMPLATES_DIRECTORY,
    VEHICLE_WEAPON_STATS_TEMPLATE_PATH,
)
from .jinja_filters import enum_name_filter, items_filter

# Altair dark theme
altair.themes.register("dark", dark_theme)
altair.themes.enable("dark")


def clean_site():

    print("Cleaning site")

    for filename in os.listdir(SITE_DIRECTORY):

        filepath = os.path.join(SITE_DIRECTORY, filename)

        print(f"Deleting {filepath}")

        try:

            shutil.rmtree(filepath)

        except OSError:

            os.remove(filepath)


def update_all_data_files(census_service_id: str):

    update_fire_groups_data_files(
        directory=DATA_FILES_DIRECTORY, service_id=census_service_id,
    )
    update_infantry_weapons_data_files(
        directory=DATA_FILES_DIRECTORY, service_id=census_service_id,
    )
    update_vehicle_weapons_data_files(
        directory=DATA_FILES_DIRECTORY, service_id=census_service_id,
    )


def generate_css():

    subprocess.check_call("npm run css-build", shell=True)


def generate_pages():

    generate_predefined_pages()
    generate_dynamic_pages()


def generate_predefined_pages():

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


def generate_dynamic_pages():

    generate_infantry_weapons_stats_pages()
    generate_vehicle_weapons_stats_pages()


def generate_infantry_weapons_stats_pages():

    fire_groups_data: List[dict] = list(
        load_fire_groups_data_files(directory=DATA_FILES_DIRECTORY)
    )

    fire_groups_data_id_idx: Dict[int, dict] = {
        int(x["fire_group_id"]): x for x in fire_groups_data
    }

    infantry_weapons_data: Iterator[dict] = filter(
        lambda x: int(x["item_id"]) not in INFANTRY_WEAPONS_EXCLUDED_ITEM_IDS,
        load_infantry_weapons_data_files(directory=DATA_FILES_DIRECTORY),
    )

    pool: Pool = Pool(cpu_count())

    pool.starmap(
        _generate_infantry_weapons_stats_page,
        ((ifwd, fire_groups_data_id_idx) for ifwd in infantry_weapons_data),
    )


def _generate_infantry_weapons_stats_page(
    infantry_weapon_data, fire_groups_data_id_idx
):

    infantry_weapon: InfantryWeapon = parse_infantry_weapon_data(
        data=infantry_weapon_data, fire_groups_data_id_idx=fire_groups_data_id_idx,
    )

    j2_env: Environment = Environment(
        loader=FileSystemLoader((TEMPLATES_DIRECTORY, PAGES_DIRECTORY))
    )
    j2_env.filters["items"] = items_filter
    j2_env.filters["enum_name"] = enum_name_filter

    j2_context: Dict[str, Any] = {
        "DamageLocation": DamageLocation,
        "ItemCategory": ItemCategory,
        "faction_background_colors": FACTION_BACKGROUND_COLORS,
        "fire_group_background_classes": FIRE_GROUP_BACKGROUND_CLASSES,
        "fire_mode_background_classes": FIRE_MODE_BACKGROUND_CLASSES,
        "with_stk": True,
        "with_magdump_simulation": True,
    }

    infantry_weapon_stats_template: Template = j2_env.get_template(
        INFANTRY_WEAPON_STATS_TEMPLATE_PATH
    )

    infantry_weapon_stats_output_dir: Path = Path(
        SITE_DIRECTORY, "stats", "infantry-weapons"
    )

    infantry_weapon_stats_output_dir.mkdir(parents=True, exist_ok=True)

    chart_template: Template = j2_env.get_template(CHART_TEMPLATE_PATH)

    sim_path: Path = Path(SIMULATIONS_DIRECTORY, "infantry-weapons")
    sim_output_dir: Path = Path(SITE_DIRECTORY).joinpath(sim_path)
    sim_output_dir.mkdir(parents=True, exist_ok=True)

    if infantry_weapon.category not in {
        ItemCategory.EXPLOSIVE,
        ItemCategory.GRENADE,
        ItemCategory.KNIFE,
        ItemCategory.ROCKET_LAUNCHER,
    }:

        fg: FireGroup
        for fg in infantry_weapon.fire_groups:

            fm: FireMode
            for fm in fg.fire_modes:

                if fm.max_consecutive_shots > 0:

                    magdump_sim_base_filename: str = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-fm{fm.fire_mode_id}-magdump"

                    magdump_sim_output_path: Path = (
                        sim_output_dir.joinpath(magdump_sim_base_filename)
                    )

                    print(f"Simulating {magdump_sim_output_path}")

                    magdump_chart: altair.HConcatChart = fm.altair_simulate_shots(
                        shots=fm.max_consecutive_shots,
                        runs=50,
                        recentering=False,
                        width=450,
                        height=450,
                    )

                    altair_saver.save(
                        magdump_chart, ".".join((str(magdump_sim_output_path), "png"))
                    )

                    with open(
                        ".".join((str(magdump_sim_output_path), "html")), "w"
                    ) as f:
                        f.write(
                            minify(
                                chart_template.render(
                                    title=f"{infantry_weapon.name} magazine dump simulation",
                                    chart=magdump_chart,
                                )
                            )
                        )

                    magdump_sim_path: Path = sim_path.joinpath(
                        magdump_sim_base_filename
                    )

                    fm.magdump_simulation_base_path = str(magdump_sim_path)

    output_path: Path = (
        infantry_weapon_stats_output_dir.joinpath(
            f"{infantry_weapon.slug}-{infantry_weapon.item_id}.html"
        )
    )

    print(f"Creating {output_path}")

    with open(output_path, "w") as f:
        f.write(
            minify(
                infantry_weapon_stats_template.render(
                    **j2_context,
                    **{
                        "weapon": infantry_weapon,
                        "update_datetime": datetime.now(timezone.utc),
                    },
                )
            )
        )


def generate_vehicle_weapons_stats_pages():

    fire_groups_data: List[dict] = list(
        load_fire_groups_data_files(directory=DATA_FILES_DIRECTORY)
    )

    fire_groups_data_id_idx: Dict[int, dict] = {
        int(x["fire_group_id"]): x for x in fire_groups_data
    }

    vehicle_weapons_data: Iterator[dict] = filter(
        lambda x: int(x["item_id"]) not in VEHICLE_WEAPONS_EXCLUDED_ITEM_IDS,
        load_vehicle_weapons_data_files(directory=DATA_FILES_DIRECTORY),
    )

    pool: Pool = Pool(cpu_count())

    pool.starmap(
        _generate_vehicle_weapons_stats_page,
        ((vhwd, fire_groups_data_id_idx) for vhwd in vehicle_weapons_data),
    )


def _generate_vehicle_weapons_stats_page(vehicle_weapon_data, fire_groups_data_id_idx):

    vehicle_weapon: VehicleWeapon = parse_vehicle_weapon_data(
        data=vehicle_weapon_data, fire_groups_data_id_idx=fire_groups_data_id_idx,
    )

    j2_env: Environment = Environment(
        loader=FileSystemLoader((TEMPLATES_DIRECTORY, PAGES_DIRECTORY))
    )
    j2_env.filters["items"] = items_filter
    j2_env.filters["enum_name"] = enum_name_filter

    j2_context: Dict[str, Any] = {
        "DamageLocation": DamageLocation,
        "ItemCategory": ItemCategory,
        "faction_background_colors": FACTION_BACKGROUND_COLORS,
        "fire_group_background_classes": FIRE_GROUP_BACKGROUND_CLASSES,
        "fire_mode_background_classes": FIRE_MODE_BACKGROUND_CLASSES,
    }

    vehicle_weapon_stats_template: Template = j2_env.get_template(
        VEHICLE_WEAPON_STATS_TEMPLATE_PATH
    )

    vehicle_weapon_stats_output_dir: Path = Path(
        SITE_DIRECTORY, "stats", "vehicle-weapons"
    )

    vehicle_weapon_stats_output_dir.mkdir(parents=True, exist_ok=True)

    sim_path: Path = Path(SIMULATIONS_DIRECTORY, "vehicle-weapons")
    sim_output_dir: Path = Path(SITE_DIRECTORY).joinpath(sim_path)
    sim_output_dir.mkdir(parents=True, exist_ok=True)

    output_path: Path = (
        vehicle_weapon_stats_output_dir.joinpath(
            f"{vehicle_weapon.slug}-{vehicle_weapon.item_id}.html"
        )
    )

    print(f"Creating {output_path}")

    with open(output_path, "w") as f:
        f.write(
            minify(
                vehicle_weapon_stats_template.render(
                    **j2_context,
                    **{
                        "weapon": vehicle_weapon,
                        "update_datetime": datetime.now(timezone.utc),
                    },
                )
            )
        )


def copy_statics():

    for static_path in Path(STATICS_DIRECTORY).rglob("*"):

        if not os.path.isfile(static_path):
            continue

        static_dirs: List[str]
        static_filename: str
        _, *static_dirs, static_filename = static_path.parts

        destination_dir: Path = Path(SITE_DIRECTORY, STATICS_DIRECTORY, *static_dirs)
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination_path: Path = destination_dir.joinpath(static_filename)

        print(f"Copying {destination_path}")

        shutil.copyfile(static_path, destination_path)
