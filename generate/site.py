import os
import shutil
import subprocess
from pathlib import Path
from typing import List

import altair
from ps2_analysis.fire_groups.data_files import (
    update_data_files as update_fire_groups_data_files,
)
from ps2_analysis.weapons.infantry.data_files import (
    update_data_files as update_infantry_weapons_data_files,
)
from ps2_analysis.weapons.vehicle.data_files import (
    update_data_files as update_vehicle_weapons_data_files,
)

from .altair_utils import dark_theme
from .constants import DATA_FILES_DIRECTORY, SITE_DIRECTORY, STATICS_DIRECTORY
from .dynamic_pages import generate_dynamic_pages
from .predefined_pages import generate_predefined_pages

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


def generate_pages(update_simulations: bool = True):

    generate_predefined_pages(update_simulations=update_simulations)
    generate_dynamic_pages(update_simulations=update_simulations)


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
