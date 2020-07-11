import os
from typing import Optional

from generate.bucket import clean_bucket, upload_to_bucket
from generate.site import (
    clean_site,
    copy_statics,
    generate_css,
    generate_dynamic_pages,
    generate_pages,
    generate_predefined_pages,
    update_all_data_files,
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
    action_group.add_argument(
        "--generate-predefined", action="store_true",
    )
    action_group.add_argument(
        "--generate-dynamic", action="store_true",
    )
    action_group.add_argument("--upload", action="store_true")
    action_group.add_argument("--update", action="store_true")

    action_group.add_argument("--clean-local", action="store_true")
    action_group.add_argument("--clean-remote", action="store_true")

    args = parser.parse_args()

    # Run
    if args.update or args.clean_local:

        clean_site()

    if args.clean_remote:

        clean_bucket(bucket_name=BUCKET_NAME)

    if (
        args.update
        or args.generate_all
        or args.generate_predefined
        or args.generate_dynamic
    ):

        generate_css()
        update_all_data_files(census_service_id=CENSUS_SERVICE_ID)

        if args.update or args.generate_all:

            generate_pages()

        else:

            if args.generate_predefined:

                generate_predefined_pages()

            elif args.generate_dynamic:

                generate_dynamic_pages()

    if args.update or args.upload:

        copy_statics()
        upload_to_bucket(bucket_name=BUCKET_NAME)
