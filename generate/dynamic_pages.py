import itertools
import math
from datetime import datetime, timezone
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import altair
import altair_saver
from htmlmin import minify
from jinja2 import Environment, FileSystemLoader, Template
from ps2_analysis.enums import DamageLocation
from ps2_analysis.fire_groups.data_files import (
    load_data_files as load_fire_groups_data_files,
)
from ps2_analysis.fire_groups.fire_group import FireGroup
from ps2_analysis.fire_groups.fire_mode import FireMode
from ps2_analysis.weapons.infantry.data_files import (
    load_data_files as load_infantry_weapons_data_files,
)
from ps2_analysis.weapons.infantry.generate import (
    EXCLUDED_ITEM_IDS as INFANTRY_WEAPONS_EXCLUDED_ITEM_IDS,
)
from ps2_analysis.weapons.infantry.generate import parse_infantry_weapon_data
from ps2_analysis.weapons.infantry.infantry_weapon import InfantryWeapon
from ps2_analysis.weapons.vehicle.data_files import (
    load_data_files as load_vehicle_weapons_data_files,
)
from ps2_analysis.weapons.vehicle.generate import (
    EXCLUDED_ITEM_IDS as VEHICLE_WEAPONS_EXCLUDED_ITEM_IDS,
)
from ps2_analysis.weapons.vehicle.generate import parse_vehicle_weapon_data
from ps2_analysis.weapons.vehicle.vehicle_weapon import VehicleWeapon
from ps2_census.enums import ItemCategory, PlayerState

from .altair_utils import (
    SIMULATION_FIRE_MODE_COLOR,
    SIMULATION_FIRE_MODE_SELECTION,
    SIMULATION_POINT_TYPE_COLOR,
    SIMULATION_POINT_TYPE_SELECTION,
    X,
    Y,
)
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
    TEMPLATES_DIRECTORY,
    VEHICLE_WEAPON_STATS_TEMPLATE_PATH,
)
from .enum_resolvers import fire_mode_type_resolver
from .jinja_filters import enum_name_filter, items_filter


def generate_magdump_simulation(
    fire_group: FireGroup,
    runs: int = 1,
    control_time: int = 0,
    auto_burst_length: Optional[int] = None,
    recentering: bool = False,
    recentering_response_time: int = 1_000,
    recentering_inertia_factor: float = 0.3,
    player_state: PlayerState = PlayerState.STANDING,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Tuple[Optional[altair.HConcatChart], Dict[int, altair.HConcatChart]]:

    assert (width or height) and not (width and height)

    datapoints: List[dict]
    fire_modes_datapoints: Dict[int, List[dict]] = {}

    for fire_mode in fire_group.fire_modes:

        if fire_mode.max_consecutive_shots > 0:

            fire_mode_id: int = fire_mode.fire_mode_id

            datapoints = []

            simulation: Iterator[
                Tuple[int, Tuple[float, float], List[Tuple[float, float]]]
            ]
            for simulation in (
                fire_mode.simulate_shots(
                    shots=fire_mode.max_consecutive_shots,
                    control_time=control_time,
                    auto_burst_length=auto_burst_length,
                    recentering=recentering,
                    recentering_response_time=recentering_response_time,
                    recentering_inertia_factor=recentering_inertia_factor,
                    player_state=player_state,
                )
                for _ in range(runs)
            ):

                t: int
                cursor_coor: Tuple[float, float]
                pellets_coors: List[Tuple[float, float]]
                for t, cursor_coor, pellets_coors in simulation:

                    cursor_x, cursor_y = cursor_coor

                    datapoints.append(
                        {
                            "FireMode": f"{fire_mode_type_resolver[fire_mode.fire_mode_type]} {'ADS' if fire_mode.is_ads else 'Hipfire'} ({fire_mode.fire_mode_id})",
                            "Time": t,
                            X: cursor_x,
                            Y: cursor_y,
                            "Type": "cursor",
                        }
                    )

                    for pellet_x, pellet_y in pellets_coors:
                        datapoints.append(
                            {
                                "FireMode": f"{fire_mode_type_resolver[fire_mode.fire_mode_type]} {'ADS' if fire_mode.is_ads else 'Hipfire'} ({fire_mode.fire_mode_id})",
                                "Time": t,
                                X: pellet_x,
                                Y: pellet_y,
                                "Type": "pellet",
                            }
                        )

            fire_modes_datapoints[fire_mode_id] = datapoints

    if not fire_modes_datapoints:

        return (None, {})

    # Generate charts for fire group and individual fire groups
    fire_modes_charts: Dict[int, altair.HConcatChart] = {}

    # Fire modes
    for fire_mode_id, datapoints in fire_modes_datapoints.items():
        chart_height: int
        chart_width: int

        min_x: float = min((d[X] for d in datapoints))
        max_x: float = max((d[X] for d in datapoints))
        min_y: float = min((d[Y] for d in datapoints))
        max_y: float = max((d[Y] for d in datapoints))

        if height:
            chart_height = height

            if max_y != min_y:
                chart_width = int(math.ceil((max_x - min_x) * height / (max_y - min_y)))
            else:
                chart_width = 0

        elif width:
            chart_width = width

            if max_x != min_x:
                chart_height = int(math.ceil((max_y - min_y) * width / (max_x - min_x)))
            else:
                chart_height = 0

        dataset: altair.Data = altair.Data(values=datapoints)

        chart: altair.Chart = (
            altair.Chart(dataset)
            .mark_point()
            .encode(
                x=altair.X(
                    f"{X}:Q",
                    axis=altair.Axis(title="horizontal angle (degrees)"),
                    scale=altair.Scale(domain=(min_x, max_x), zero=False),
                ),
                y=altair.Y(
                    f"{Y}:Q",
                    axis=altair.Axis(title="vertical angle (degrees)"),
                    scale=altair.Scale(domain=(min_y, max_y), zero=False),
                ),
                color=SIMULATION_POINT_TYPE_COLOR,
                tooltip=["Time:Q", f"{X}:Q", f"{Y}:Q"],
            )
            .properties(width=chart_width, height=chart_height)
            .interactive()
        )

        legend: altair.Chart = (
            altair.Chart(dataset)
            .mark_point()
            .encode(
                y=altair.Y("Type:N", axis=altair.Axis(orient="right")),
                color=SIMULATION_POINT_TYPE_COLOR,
            )
            .add_selection(SIMULATION_POINT_TYPE_SELECTION)
        )

        fire_modes_charts[fire_mode_id] = altair.hconcat(chart, legend)

    # Fire group
    all_datapoints: List[dict] = list(
        itertools.chain.from_iterable(
            (
                filter(lambda x: x["Type"] == "pellet", d)
                for _, d in fire_modes_datapoints.items()
            )
        )
    )

    fg_chart_height: int
    fg_chart_width: int

    fg_min_x: float = min((d[X] for d in all_datapoints))
    fg_max_x: float = max((d[X] for d in all_datapoints))
    fg_min_y: float = min((d[Y] for d in all_datapoints))
    fg_max_y: float = max((d[Y] for d in all_datapoints))

    if height:
        fg_chart_height = height

        if fg_max_y != fg_min_y:
            fg_chart_width = int(
                math.ceil((fg_max_x - fg_min_x) * height / (fg_max_y - fg_min_y))
            )
        else:
            fg_chart_width = 0

    elif width:
        fg_chart_width = width

        if fg_max_x != fg_min_x:
            fg_chart_height = int(
                math.ceil((fg_max_y - fg_min_y) * width / (fg_max_x - fg_min_x))
            )
        else:
            fg_chart_height = 0

    fg_dataset: altair.Data = altair.Data(values=all_datapoints)

    fg_chart: altair.Chart = (
        altair.Chart(fg_dataset)
        .mark_point()
        .encode(
            x=altair.X(
                f"{X}:Q",
                axis=altair.Axis(title="horizontal angle (degrees)"),
                scale=altair.Scale(domain=(fg_min_x, fg_max_x), zero=False),
            ),
            y=altair.Y(
                f"{Y}:Q",
                axis=altair.Axis(title="vertical angle (degrees)"),
                scale=altair.Scale(domain=(fg_min_y, fg_max_y), zero=False),
            ),
            color=SIMULATION_FIRE_MODE_COLOR,
            tooltip=["Time:Q", f"{X}:Q", f"{Y}:Q"],
        )
        .properties(width=fg_chart_width, height=fg_chart_height)
        .interactive()
    )

    fg_legend: altair.Chart = (
        altair.Chart(fg_dataset)
        .mark_point()
        .encode(
            y=altair.Y("FireMode:N", axis=altair.Axis(orient="right")),
            color=SIMULATION_FIRE_MODE_COLOR,
        )
        .add_selection(SIMULATION_FIRE_MODE_SELECTION)
    )

    return (altair.hconcat(fg_chart, fg_legend), fire_modes_charts)


def generate_dynamic_pages(update_simulations: bool = True):

    generate_infantry_weapons_stats_pages(update_simulations=update_simulations)
    generate_vehicle_weapons_stats_pages(update_simulations=update_simulations)


def generate_infantry_weapons_stats_pages(update_simulations: bool = True):

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

    pool = Pool(cpu_count())

    pool.starmap(
        _generate_infantry_weapons_stats_page,
        (
            (ifwd, fire_groups_data_id_idx, update_simulations)
            for ifwd in infantry_weapons_data
        ),
    )


def _generate_infantry_weapons_stats_page(
    infantry_weapon_data: dict,
    fire_groups_data_id_idx: Dict[int, dict],
    update_simulations: bool = True,
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
        "faction_background_colors": FACTION_BACKGROUND_COLORS,
        "fire_group_background_classes": FIRE_GROUP_BACKGROUND_CLASSES,
        "fire_mode_background_classes": FIRE_MODE_BACKGROUND_CLASSES,
        "with_stk_simulation": True,
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

        fm: FireMode

        fg: FireGroup
        for fg in infantry_weapon.fire_groups:

            fg_magdump_sim_base_filename: str = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-magdump"
            fg_magdump_sim_path: Path = sim_path.joinpath(fg_magdump_sim_base_filename)
            fg_magdump_sim_output_path: Path = (
                sim_output_dir.joinpath(fg_magdump_sim_base_filename)
            )

            fm_magdump_sim_base_filename: str
            fm_magdump_sim_path: Path
            fm_magdump_sim_output_path: Path

            if update_simulations is False:

                # Fire group
                if (
                    fg_magdump_sim_output_path.with_suffix(".html").is_file()
                    and fg_magdump_sim_output_path.with_suffix(".png").is_file()
                ):

                    fg.magdump_simulation_base_path = str(fg_magdump_sim_path)

                # Fire modes
                for fm in fg.fire_modes:

                    fm_magdump_sim_base_filename = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-fm{fm.fire_mode_id}-magdump"
                    fm_magdump_sim_path = sim_path.joinpath(
                        fm_magdump_sim_base_filename
                    )
                    fm_magdump_sim_output_path = sim_output_dir.joinpath(
                        fm_magdump_sim_base_filename
                    )

                    if (
                        fg_magdump_sim_output_path.with_suffix(".html").is_file()
                        and fg_magdump_sim_output_path.with_suffix(".png").is_file()
                    ):

                        fm.magdump_simulation_base_path = str(fm_magdump_sim_path)

            else:

                print(f"Simulating {infantry_weapon.slug} magdump")

                fg_magdump_chart: Optional[altair.HConcatChart]
                fm_magdump_charts: Dict[int, altair.HConcatChart]
                fg_magdump_chart, fm_magdump_charts = generate_magdump_simulation(
                    fire_group=fg, runs=50, recentering=False, height=600,
                )

                # Fire group
                if fg_magdump_chart:

                    altair_saver.save(
                        fg_magdump_chart,
                        ".".join((str(fg_magdump_sim_output_path), "png")),
                    )

                    with open(
                        ".".join((str(fg_magdump_sim_output_path), "html")), "w"
                    ) as f:
                        f.write(
                            minify(
                                chart_template.render(
                                    **j2_context,
                                    **{
                                        "title": f"{infantry_weapon.name} {fg.description} fire group magazine dump simulation",
                                        "chart": fg_magdump_chart,
                                        "update_datetime": datetime.now(timezone.utc),
                                    },
                                )
                            )
                        )

                    fg.magdump_simulation_base_path = str(fg_magdump_sim_path)

                # Fire modes
                if fm_magdump_charts:

                    for fm in fg.fire_modes:

                        if fm.fire_mode_id in fm_magdump_charts:

                            fm_magdump_chart: altair.HConcatChart = fm_magdump_charts[
                                fm.fire_mode_id
                            ]

                            fm_magdump_sim_base_filename = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-fm{fm.fire_mode_id}-magdump"
                            fm_magdump_sim_path = sim_path.joinpath(
                                fm_magdump_sim_base_filename
                            )
                            fm_magdump_sim_output_path = sim_output_dir.joinpath(
                                fm_magdump_sim_base_filename
                            )

                            altair_saver.save(
                                fm_magdump_chart,
                                ".".join((str(fm_magdump_sim_output_path), "png")),
                            )

                            with open(
                                ".".join((str(fm_magdump_sim_output_path), "html")), "w"
                            ) as f:
                                f.write(
                                    minify(
                                        chart_template.render(
                                            **j2_context,
                                            **{
                                                "title": f"{infantry_weapon.name} {fg.description} {fire_mode_type_resolver[fm.fire_mode_type]} {'ADS' if fm.is_ads else 'Hipfire'} magazine dump simulation",
                                                "chart": fm_magdump_chart,
                                                "update_datetime": datetime.now(
                                                    timezone.utc
                                                ),
                                            },
                                        )
                                    )
                                )

                            fm.magdump_simulation_base_path = str(fm_magdump_sim_path)

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


def generate_vehicle_weapons_stats_pages(update_simulations: bool = True):

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

    pool = Pool(cpu_count())

    pool.starmap(
        _generate_vehicle_weapons_stats_page,
        (
            (vhwd, fire_groups_data_id_idx, update_simulations)
            for vhwd in vehicle_weapons_data
        ),
    )


def _generate_vehicle_weapons_stats_page(
    vehicle_weapon_data: dict,
    fire_groups_data_id_idx: Dict[int, dict],
    update_simulations: bool = True,
):

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
