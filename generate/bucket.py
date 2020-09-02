import gzip
from io import BytesIO
from pathlib import Path
from typing import List

from google.cloud import storage

from .constants import SITE_DIRECTORY, SUFFIX_CONTENT_TYPE


def clean_bucket(bucket_name: str):

    print(f"Cleaning {bucket_name} bucket")

    client: storage.Client = storage.Client()
    bucket: storage.Bucket = client.get_bucket(bucket_name)

    blob: storage.Blob
    for blob in bucket.list_blobs():

        print(f"Deleting {blob.name}")

        blob.delete()


def upload_to_bucket(bucket_name: str, prefix: str = ""):

    print(f"Uploading files to {bucket_name} bucket")

    client: storage.Client = storage.Client()
    bucket: storage.Bucket = client.get_bucket(bucket_name)

    for file_path in Path(SITE_DIRECTORY).rglob("*"):

        if file_path.is_dir():

            continue

        elif not str(file_path).startswith(str(Path(SITE_DIRECTORY).joinpath(prefix))):

            continue

        file_dirs: List[str]
        file_filename: str
        _, *file_dirs, file_filename = file_path.parts

        destination_path = Path(*file_dirs, file_filename)

        suffix: str = file_path.suffix

        print(f"Uploading {destination_path}")

        blob: storage.Blob = bucket.blob(str(destination_path))

        # Compress files that can be compressed
        if suffix in {".html", ".css", ".js"}:

            content_type: str = SUFFIX_CONTENT_TYPE[suffix]

            blob.content_encoding = "gzip"
            blob.content_type = content_type

            with open(file_path, "rb") as f:
                data: BytesIO = BytesIO(gzip.compress(f.read()))

            blob.upload_from_file(data, rewind=True, content_type=content_type)

        # Otherwise just upload
        else:

            blob.upload_from_filename(str(file_path))
