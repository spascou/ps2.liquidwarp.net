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
from ps2_analysis.enums import DamageLocation, DamageTargetType
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
    SIMULATION_STK_COLOR,
    SIMULATION_STK_OPACITY,
    SIMULATION_STK_SELECTION,
    X,
    Y,
)
from .constants import (
    CHART_TEMPLATE_PATH,
    CURSOR,
    DATA_FILES_DIRECTORY,
    INFANTRY_WEAPON_STATS_TEMPLATE_PATH,
    PAGES_DIRECTORY,
    PELLET,
    SIMULATIONS_DIRECTORY,
    SITE_DIRECTORY,
    TEMPLATES_DIRECTORY,
    VEHICLE_WEAPON_STATS_TEMPLATE_PATH,
)
from .enum_resolvers import fire_mode_type_resolver
from .jinja_filters import debug_filter, enum_name_filter, items_filter


def generate_magdump_simulation(
    fire_group: FireGroup,
    runs: int = 1,
    control_time: int = 0,
    auto_burst_length: Optional[int] = None,
    recoil_compensation: bool = False,
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
                Tuple[
                    int,
                    Tuple[float, float],
                    List[Tuple[float, float]],
                    float,
                    Tuple[float, float],
                    Tuple[float, float],
                ]
            ]
            for simulation in (
                fire_mode.simulate_shots(
                    shots=fire_mode.max_consecutive_shots,
                    control_time=control_time,
                    auto_burst_length=auto_burst_length,
                    recoil_compensation=recoil_compensation,
                    player_state=player_state,
                )
                for _ in range(runs)
            ):

                t: int
                cursor_coor: Tuple[float, float]
                pellets_coors: List[Tuple[float, float]]
                _cof: float
                _vertical_recoil: Tuple[float, float]
                _horizontal_recoil: Tuple[float, float]
                for (
                    t,
                    cursor_coor,
                    pellets_coors,
                    _cof,
                    _vertical_recoil,
                    _horizontal_recoil,
                ) in simulation:

                    cursor_x, cursor_y = cursor_coor

                    datapoints.append(
                        {
                            "firemode": f"{fire_mode_type_resolver[fire_mode.fire_mode_type]} {'ADS' if fire_mode.is_ads else 'Hipfire'} ({fire_mode.fire_mode_id})",
                            "time": t,
                            "type": CURSOR,
                            X: cursor_x,
                            Y: cursor_y,
                        }
                    )

                    for pellet_x, pellet_y in pellets_coors:
                        datapoints.append(
                            {
                                "firemode": f"{fire_mode_type_resolver[fire_mode.fire_mode_type]} {'ADS' if fire_mode.is_ads else 'Hipfire'} ({fire_mode.fire_mode_id})",
                                "time": t,
                                "type": PELLET,
                                X: pellet_x,
                                Y: pellet_y,
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
                chart_width = height

        elif width:
            chart_width = width

            if max_x != min_x:
                chart_height = int(math.ceil((max_y - min_y) * width / (max_x - min_x)))
            else:
                chart_height = width

        total_shots: int = len(list(filter(lambda x: x["type"] == CURSOR, datapoints)))
        total_pellets: int = len(
            list(filter(lambda x: x["type"] == PELLET, datapoints))
        )

        dataset: altair.Data = altair.Data(values=datapoints)

        chart: altair.Chart = (
            altair.Chart(dataset)
            .mark_point()
            .encode(
                x=altair.X(
                    f"{X}:Q",
                    axis=altair.Axis(title="horizontal angle (degrees)"),
                    scale=altair.Scale(domain=(min_x, max_x)),
                ),
                y=altair.Y(
                    f"{Y}:Q",
                    axis=altair.Axis(title="vertical angle (degrees)"),
                    scale=altair.Scale(domain=(min_y, max_y)),
                ),
                color=SIMULATION_POINT_TYPE_COLOR,
                tooltip=["time:Q", f"{X}:Q", f"{Y}:Q"],
            )
            .properties(
                width=chart_width,
                height=chart_height,
                title=f"{runs} magdumps, {total_shots} shots, {total_pellets} pellets",
            )
            .interactive()
        )

        legend: altair.Chart = (
            altair.Chart(dataset)
            .mark_point()
            .encode(
                y=altair.Y("type:N", axis=altair.Axis(orient="right")),
                color=SIMULATION_POINT_TYPE_COLOR,
            )
            .add_selection(SIMULATION_POINT_TYPE_SELECTION)
        )

        fire_modes_charts[fire_mode_id] = altair.hconcat(chart, legend)

    # Fire group
    all_datapoints: List[dict] = list(
        itertools.chain.from_iterable(fire_modes_datapoints.values())
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

    all_total_shots: int = len(
        list(filter(lambda x: x["type"] == CURSOR, all_datapoints))
    ) // len(fire_modes_datapoints)
    all_total_pellets: int = len(
        list(filter(lambda x: x["type"] == PELLET, all_datapoints))
    ) // len(fire_modes_datapoints)

    all_datapoints_pellets_only: List[dict] = list(
        filter(lambda x: x["type"] == PELLET, all_datapoints)
    )

    fg_dataset: altair.Data = altair.Data(values=all_datapoints_pellets_only)

    fg_chart: altair.Chart = (
        altair.Chart(fg_dataset)
        .mark_point()
        .encode(
            x=altair.X(
                f"{X}:Q",
                axis=altair.Axis(title="horizontal angle (degrees)"),
                scale=altair.Scale(domain=(fg_min_x, fg_max_x)),
            ),
            y=altair.Y(
                f"{Y}:Q",
                axis=altair.Axis(title="vertical angle (degrees)"),
                scale=altair.Scale(domain=(fg_min_y, fg_max_y)),
            ),
            color=SIMULATION_FIRE_MODE_COLOR,
            tooltip=["time:Q", f"{X}:Q", f"{Y}:Q"],
        )
        .properties(
            width=fg_chart_width,
            height=fg_chart_height,
            title=f"{runs} magdumps, {all_total_shots} shots, {all_total_pellets} pellets",
        )
        .interactive()
    )

    fg_legend: altair.Chart = (
        altair.Chart(fg_dataset)
        .mark_point()
        .encode(
            y=altair.Y("firemode:N", axis=altair.Axis(orient="right")),
            color=SIMULATION_FIRE_MODE_COLOR,
        )
        .add_selection(SIMULATION_FIRE_MODE_SELECTION)
    )

    return (altair.hconcat(fg_chart, fg_legend), fire_modes_charts)


def generate_stkr_simulation(
    fire_group: FireGroup,
    width: Optional[int] = None,
    height: Optional[int] = None,
    range_extension_factor: float = 1.1,
    zero_range_width: float = 10,
) -> Tuple[Optional[altair.VConcatChart], Dict[int, altair.VConcatChart]]:
    assert width or height

    fire_group_chart: Optional[altair.VConcatChart] = None
    fire_mode_charts: Dict[FireMode, altair.VConcatChart] = {}

    if not fire_group.fire_modes:

        return (None, {})

    fire_group_hcharts: List[altair.HConcatChart] = []

    if (
        (fire_group.direct_damage_profile and fire_group.indirect_damage_profile)
        or (
            fire_group.direct_damage_profile
            and not fire_group.indirect_damage_profile
            and all((x.indirect_damage_profile is None for x in fire_group.fire_modes))
        )
        or (
            fire_group.indirect_damage_profile
            and not fire_group.direct_damage_profile
            and all((x.direct_damage_profile is None for x in fire_group.fire_modes))
        )
    ):

        fm: FireMode = fire_group.fire_modes[0]

        damage_location: DamageLocation
        for damage_location in (DamageLocation.TORSO, DamageLocation.HEAD):

            datapoints: List[dict] = []

            baseline_stkr: List[Tuple[float, int]] = list(
                fm.shots_to_kill_ranges(
                    damage_target_type=DamageTargetType.INFANTRY_BASELINE,
                    damage_location=damage_location,
                )
            )

            if not baseline_stkr:

                continue

            b_distance: float
            b_stk: int
            for b_distance, b_stk in baseline_stkr:
                datapoints.append(
                    {
                        X: b_distance,
                        Y: b_stk,
                        "target": DamageTargetType.INFANTRY_BASELINE,
                    }
                )

            damage_target_type: DamageTargetType
            for damage_target_type in {
                DamageTargetType.INFANTRY_AUXILIARY_SHIELD,
                DamageTargetType.INFANTRY_INFILTRATOR,
                DamageTargetType.INFANTRY_HEAVY_RESIST_SHIELD,
                DamageTargetType.INFANTRY_HEAVY_HEALTH_SHIELD,
                DamageTargetType.INFANTRY_NANOWEAVE,
                DamageTargetType.INFANTRY_FLAK_ARMOR,
            }:
                stkr: List[Tuple[float, int]] = list(
                    fm.shots_to_kill_ranges(
                        damage_target_type=damage_target_type,
                        damage_location=damage_location,
                    )
                )

                if stkr and stkr != baseline_stkr:
                    distance: float
                    stk: int
                    for distance, stk in stkr:
                        datapoints.append(
                            {X: distance, Y: stk, "target": damage_target_type}
                        )

            if not datapoints:

                continue

            min_x: float = min((d[X] for d in datapoints))
            max_x: float = max((d[X] for d in datapoints)) * range_extension_factor
            min_y: float = min((d[Y] for d in datapoints))
            max_y: float = max((d[Y] for d in datapoints)) + 1.0

            if min_y > 0.0:

                min_y -= 1.0

            if max_x == 0.0:

                max_x = zero_range_width

            target: str
            target_dp_it: Iterator[dict]
            for target, target_dp_it in itertools.groupby(
                sorted(datapoints, key=lambda x: x["target"]), lambda x: x["target"]
            ):
                last_stk = sorted(target_dp_it, key=lambda x: x[X])[-1][Y]

                datapoints.append({X: max_x, Y: last_stk, "target": target})

            size_properties: dict

            if width:
                size_properties = {"width": width}
            else:
                size_properties = {"height": height}

            dataset: altair.Data = altair.Data(values=datapoints)

            chart: altair.Chart = (
                altair.Chart(dataset)
                .mark_line(interpolate="step-after", strokeOpacity=0.5, strokeWidth=10)
                .encode(
                    x=altair.X(
                        f"{X}:Q",
                        axis=altair.Axis(title="range (meters)"),
                        scale=altair.Scale(domain=(min_x, max_x)),
                    ),
                    y=altair.Y(
                        f"{Y}:Q",
                        axis=altair.Axis(title="shots to kill"),
                        scale=altair.Scale(domain=(min_y, max_y)),
                    ),
                    color=SIMULATION_STK_COLOR,
                    opacity=SIMULATION_STK_OPACITY,
                    tooltip=["target:N", f"{X}:Q", f"{Y}:Q"],
                )
                .properties(title=damage_location, **size_properties)
                .interactive()
            )

            legend: altair.Chart = (
                altair.Chart(dataset)
                .mark_point()
                .encode(
                    y=altair.Y("target:N", axis=altair.Axis(orient="right")),
                    color=SIMULATION_STK_COLOR,
                )
                .add_selection(SIMULATION_STK_SELECTION)
            )

            fire_group_hcharts.append(altair.hconcat(chart, legend))

        else:

            for fm in fire_group.fire_modes:

                fire_mode_hcharts: List[altair.HConcatChart] = []

                for damage_location in (DamageLocation.TORSO, DamageLocation.HEAD):

                    datapoints = []

                    baseline_stkr = list(
                        fm.shots_to_kill_ranges(
                            damage_target_type=DamageTargetType.INFANTRY_BASELINE,
                            damage_location=damage_location,
                        )
                    )

                    if not baseline_stkr:

                        continue

                    for b_distance, b_stk in baseline_stkr:
                        datapoints.append(
                            {
                                X: b_distance,
                                Y: b_stk,
                                "target": DamageTargetType.INFANTRY_BASELINE,
                            }
                        )

                    for damage_target_type in {
                        DamageTargetType.INFANTRY_AUXILIARY_SHIELD,
                        DamageTargetType.INFANTRY_INFILTRATOR,
                        DamageTargetType.INFANTRY_HEAVY_RESIST_SHIELD,
                        DamageTargetType.INFANTRY_HEAVY_HEALTH_SHIELD,
                        DamageTargetType.INFANTRY_NANOWEAVE,
                        DamageTargetType.INFANTRY_FLAK_ARMOR,
                    }:
                        stkr = list(
                            fm.shots_to_kill_ranges(
                                damage_target_type=damage_target_type,
                                damage_location=damage_location,
                            )
                        )

                        if stkr and stkr != baseline_stkr:
                            for distance, stk in stkr:
                                datapoints.append(
                                    {X: distance, Y: stk, "target": damage_target_type}
                                )

                    if not datapoints:

                        continue

                    min_x = min((d[X] for d in datapoints))
                    max_x = max((d[X] for d in datapoints)) * range_extension_factor
                    min_y = min((d[Y] for d in datapoints))
                    max_y = max((d[Y] for d in datapoints))

                    if min_y > 0.0:

                        min_y -= 1.0

                    if max_x == 0.0:

                        max_x = zero_range_width

                    for target, target_dp_it in itertools.groupby(
                        sorted(datapoints, key=lambda x: x["target"]),
                        lambda x: x["target"],
                    ):
                        last_stk = sorted(target_dp_it, key=lambda x: x[X])[-1][Y]

                        datapoints.append({X: max_x, Y: last_stk, "target": target})

                    if width:
                        size_properties = {"width": width}
                    else:
                        size_properties = {"height": height}

                    dataset = altair.Data(values=datapoints)

                    chart = (
                        altair.Chart(dataset)
                        .mark_line(
                            interpolate="step-after", strokeOpacity=0.5, strokeWidth=10,
                        )
                        .encode(
                            x=altair.X(
                                f"{X}:Q",
                                axis=altair.Axis(title="range (meters)"),
                                scale=altair.Scale(domain=(min_x, max_x)),
                            ),
                            y=altair.Y(
                                f"{Y}:Q",
                                axis=altair.Axis(title="shots to kill"),
                                scale=altair.Scale(domain=(min_y, max_y)),
                            ),
                            color=SIMULATION_STK_COLOR,
                            opacity=SIMULATION_STK_OPACITY,
                            tooltip=["target:N", f"{X}:Q", f"{Y}:Q"],
                        )
                        .properties(title=damage_location, **size_properties)
                        .interactive()
                    )

                    legend = (
                        altair.Chart(dataset)
                        .mark_point()
                        .encode(
                            y=altair.Y("target:N", axis=altair.Axis(orient="right")),
                            color=SIMULATION_STK_COLOR,
                        )
                        .add_selection(SIMULATION_STK_SELECTION)
                    )

                    fire_mode_hcharts.append(altair.hconcat(chart, legend))

                if fire_mode_hcharts:
                    fire_mode_charts[fm.fire_mode_id] = altair.vconcat(
                        *fire_mode_hcharts
                    )

    if fire_mode_hcharts:
        fire_group_chart = altair.vconcat(*fire_group_hcharts)

    return (
        fire_group_chart,
        fire_mode_charts,
    )


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
    j2_env.filters["debug"] = debug_filter

    j2_context: Dict[str, Any] = {
        "DamageLocation": DamageLocation,
    }

    infantry_weapon_stats_template: Template = j2_env.get_template(
        INFANTRY_WEAPON_STATS_TEMPLATE_PATH
    )

    infantry_weapon_stats_output_dir: Path = Path(
        SITE_DIRECTORY, "stats", "weapons", "infantry"
    )

    infantry_weapon_stats_output_dir.mkdir(parents=True, exist_ok=True)

    chart_template: Template = j2_env.get_template(CHART_TEMPLATE_PATH)

    sim_path: Path = Path(SIMULATIONS_DIRECTORY, "weapons", "infantry")
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

            # Magdump
            fg_magdump_sim_base_filename: str = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-magdump"
            fg_magdump_sim_path: Path = sim_path.joinpath(fg_magdump_sim_base_filename)
            fg_magdump_sim_output_path: Path = (
                sim_output_dir.joinpath(fg_magdump_sim_base_filename)
            )

            fm_magdump_sim_base_filename: str
            fm_magdump_sim_path: Path
            fm_magdump_sim_output_path: Path

            # STKR
            fg_stkr_sim_base_filename: str = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-stkr"
            fg_stkr_sim_path: Path = sim_path.joinpath(fg_stkr_sim_base_filename)
            fg_stkr_sim_output_path: Path = (
                sim_output_dir.joinpath(fg_stkr_sim_base_filename)
            )

            fm_stkr_sim_base_filename: str
            fm_stkr_sim_path: Path
            fm_stkr_sim_output_path: Path

            if update_simulations is False:

                # Fire group
                if (
                    fg_magdump_sim_output_path.with_suffix(".html").is_file()
                    and fg_magdump_sim_output_path.with_suffix(".png").is_file()
                ):

                    fg.magdump_simulation_base_path = str(fg_magdump_sim_path)

                if (
                    fg_stkr_sim_output_path.with_suffix(".html").is_file()
                    and fg_stkr_sim_output_path.with_suffix(".png").is_file()
                ):

                    fg.stkr_simulation_base_path = str(fg_stkr_sim_path)

                # Fire modes
                for fm in fg.fire_modes:

                    fm_magdump_sim_base_filename = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-fm{fm.fire_mode_id}-magdump"
                    fm_magdump_sim_path = sim_path.joinpath(
                        fm_magdump_sim_base_filename
                    )

                    if (
                        fg_magdump_sim_output_path.with_suffix(".html").is_file()
                        and fg_magdump_sim_output_path.with_suffix(".png").is_file()
                    ):

                        fm.magdump_simulation_base_path = str(fm_magdump_sim_path)

                    fm_stkr_sim_base_filename = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-fm{fm.fire_mode_id}-stkr"
                    fm_stkr_sim_path = sim_path.joinpath(fm_stkr_sim_base_filename)

                    if (
                        fg_stkr_sim_output_path.with_suffix(".html").is_file()
                        and fg_stkr_sim_output_path.with_suffix(".png").is_file()
                    ):

                        fm.stkr_simulation_base_path = str(fm_stkr_sim_path)

            else:

                # Magdump
                print(f"Simulating {infantry_weapon.slug} magdump")

                fg_magdump_chart: Optional[altair.HConcatChart]
                fm_magdump_charts: Dict[int, altair.HConcatChart]
                fg_magdump_chart, fm_magdump_charts = generate_magdump_simulation(
                    fire_group=fg, runs=50, height=800,
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
                                        "title": f"{infantry_weapon.name} {fg.description} fire group magazine dump",
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
                                                "title": f"{infantry_weapon.name} {fg.description} {fire_mode_type_resolver[fm.fire_mode_type]} {'ADS' if fm.is_ads else 'Hipfire'} fire mode magazine dump",
                                                "chart": fm_magdump_chart,
                                                "update_datetime": datetime.now(
                                                    timezone.utc
                                                ),
                                            },
                                        )
                                    )
                                )

                            fm.magdump_simulation_base_path = str(fm_magdump_sim_path)

                # STKR
                print(f"Simulating {infantry_weapon.slug} STKR")

                fg_stkr_chart: Optional[altair.VConcatChart]
                fm_stkr_charts: Dict[int, altair.VConcatChart]
                fg_stkr_chart, fm_stkr_charts = generate_stkr_simulation(
                    fire_group=fg, width=800,
                )

                # Fire group
                if fg_stkr_chart:

                    altair_saver.save(
                        fg_stkr_chart, ".".join((str(fg_stkr_sim_output_path), "png")),
                    )

                    with open(
                        ".".join((str(fg_stkr_sim_output_path), "html")), "w"
                    ) as f:
                        f.write(
                            minify(
                                chart_template.render(
                                    **j2_context,
                                    **{
                                        "title": f"{infantry_weapon.name} {fg.description} fire group shots to kill ranges",
                                        "chart": fg_stkr_chart,
                                        "update_datetime": datetime.now(timezone.utc),
                                    },
                                )
                            )
                        )

                    fg.stkr_simulation_base_path = str(fg_stkr_sim_path)

                # Fire modes
                if fm_stkr_charts:

                    for fm in fg.fire_modes:

                        if fm.fire_mode_id in fm_stkr_charts:

                            fm_stkr_chart: altair.VConcatChart = fm_stkr_charts[
                                fm.fire_mode_id
                            ]

                            fm_stkr_sim_base_filename = f"{infantry_weapon.slug}-{infantry_weapon.item_id}-fg{fg.fire_group_id}-fm{fm.fire_mode_id}-stkr"
                            fm_stkr_sim_path = sim_path.joinpath(
                                fm_stkr_sim_base_filename
                            )
                            fm_stkr_sim_output_path = sim_output_dir.joinpath(
                                fm_stkr_sim_base_filename
                            )

                            altair_saver.save(
                                fm_stkr_chart,
                                ".".join((str(fm_stkr_sim_output_path), "png")),
                            )

                            with open(
                                ".".join((str(fm_stkr_sim_output_path), "html")), "w"
                            ) as f:
                                f.write(
                                    minify(
                                        chart_template.render(
                                            **j2_context,
                                            **{
                                                "title": f"{infantry_weapon.name} {fg.description} {fire_mode_type_resolver[fm.fire_mode_type]} {'ADS' if fm.is_ads else 'Hipfire'} fire mode shots to kill ranges",
                                                "chart": fm_stkr_chart,
                                                "update_datetime": datetime.now(
                                                    timezone.utc
                                                ),
                                            },
                                        )
                                    )
                                )

                            fm.stkr_simulation_base_path = str(fm_stkr_sim_path)

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
    }

    vehicle_weapon_stats_template: Template = j2_env.get_template(
        VEHICLE_WEAPON_STATS_TEMPLATE_PATH
    )

    vehicle_weapon_stats_output_dir: Path = Path(
        SITE_DIRECTORY, "stats", "weapons", "vehicle"
    )

    vehicle_weapon_stats_output_dir.mkdir(parents=True, exist_ok=True)

    sim_path: Path = Path(SIMULATIONS_DIRECTORY, "weapons", "vehicle")
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
