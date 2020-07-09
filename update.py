import os
from typing import Optional

from generate.bucket import clean_bucket, upload_to_bucket
from generate.site import clean_site, generate_site

SITE_DIRECTORY: str = "site"
TEMPLATES_DIRECTORY: str = "templates"
PAGES_DIRECTORY: str = "pages"
STATICS_DIRECTORY: str = "statics"
DATA_FILES_DIRECTORY: str = "datafiles"

BUCKET_NAME = "ps2.liquidwarp.net"

CENSUS_SERVICE_ID: Optional[str] = os.environ.get("CENSUS_SERVICE_ID")

if not CENSUS_SERVICE_ID:
    raise ValueError("No CENSUS_SERVICE_ID envvar found")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--generate", dest="generate", action="store_true", default=False
    )
    action_group.add_argument(
        "--upload", dest="upload", action="store_true", default=False
    )
    action_group.add_argument(
        "--upgrade", dest="upgrade", action="store_true", default=False
    )

    parser.add_argument(
        "--no-simulations", dest="no_simulations", action="store_true", default=False
    )
    parser.add_argument(
        "--clean-all", dest="clean_all", action="store_true", default=False
    )
    parser.add_argument(
        "--clean-local", dest="clean_local", action="store_true", default=False
    )
    parser.add_argument(
        "--clean-remote", dest="clean_remote", action="store_true", default=False
    )

    args = parser.parse_args()

    if args.clean_all is True or args.clean_local is True:
        clean_site(directory=SITE_DIRECTORY)

    if args.upgrade is True or args.generate is True:
        generate_site(
            templates_directory=TEMPLATES_DIRECTORY,
            pages_directory=PAGES_DIRECTORY,
            statics_directory=STATICS_DIRECTORY,
            data_files_directory=DATA_FILES_DIRECTORY,
            output_directory=SITE_DIRECTORY,
            census_service_id=CENSUS_SERVICE_ID,
            no_simulations=args.no_simulations is True,
        )

    if args.clean_all is True or args.clean_remote is True:
        clean_bucket(bucket_name=BUCKET_NAME)

    if args.upgrade is True or args.upload is True:
        upload_to_bucket(directory_path=SITE_DIRECTORY, bucket_name=BUCKET_NAME)
