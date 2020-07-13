import os
from typing import Optional

from generate import (
    clean_bucket,
    clean_site,
    copy_statics,
    generate_css,
    generate_pages,
    update_all_data_files,
    upload_to_bucket,
)

BUCKET_NAME = "ps2.liquidwarp.net"

CENSUS_SERVICE_ID: Optional[str] = os.environ.get("CENSUS_SERVICE_ID")

if not CENSUS_SERVICE_ID:
    raise ValueError("No CENSUS_SERVICE_ID envvar found")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    # Main action
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--generate-all", action="store_true")
    action_group.add_argument("--upload", action="store_true")
    action_group.add_argument("--update", action="store_true")
    action_group.add_argument("--copy-statics", action="store_true")
    action_group.add_argument("--generate-css", action="store_true")

    action_group.add_argument("--clean-local", action="store_true")
    action_group.add_argument("--clean-remote", action="store_true")

    args = parser.parse_args()

    # Run
    if args.update or args.clean_local:

        clean_site()

    if args.update or args.generate_css:

        generate_css()

    if args.update or args.generate_all:

        update_all_data_files(census_service_id=CENSUS_SERVICE_ID)
        generate_pages()

    if args.update or args.copy_statics:

        copy_statics()

    if args.clean_remote:

        clean_bucket(bucket_name=BUCKET_NAME)

    if args.update or args.upload:

        upload_to_bucket(bucket_name=BUCKET_NAME)
