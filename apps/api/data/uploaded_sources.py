"""The file of an upload, kept where a data source can read it again.

An upload is the creation of a data source: the bytes are written under the
uploads directory, and a row of type ``file_upload`` names that file. The
sync of the source then reads it through the shared import chain - the same
chain the upload itself used.

The shape of the decision is written down in
``docs/reasoning/2026-11-25-file-upload-source.md``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import DataSourceDB

# The directory of the uploads that hold the file of a source. It lives under
# the uploads directory, because that is the only directory a source may
# read from - ``_resolve_source_file`` refuses everything else.
SOURCE_FILES_DIRNAME = "sources"

# The name of the file a source reads is written by an operator (it is the
# name they gave the upload), so it is reduced to a name that is safe to
# write into a directory: no separators, no dots, no spaces.
_UNSAFE_CHARS = re.compile(r"[^a-z0-9]+")

_MAX_FILE_NAME_LENGTH = 60


def safe_source_filename(name: str, suffix: str) -> str:
    """The name of the file a source of this name reads.

    The name of the source is the name of the operator, and the name of the
    file is written into a directory, so the two are not the same string:
    the name is reduced to letters, digits and dashes.
    """
    slug = _UNSAFE_CHARS.sub("-", name.strip().lower()).strip("-")
    if not slug:
        slug = "upload"
    return f"{slug[:_MAX_FILE_NAME_LENGTH]}{suffix}"


def store_uploaded_source_file(
    payload: bytes,
    *,
    uploads_root: Path,
    name: str,
    suffix: str,
) -> str:
    """Keep the file of an upload and return where it is, relative to the root.

    The path that is returned is relative to the uploads directory, because
    that is how a source names its file: the directory of the deployment is
    not the same on every machine, and a config that carried an absolute
    path would name a file of one machine only.

    A file of the same name is replaced. The source of that name is the same
    source - the upload is the creation of a source, not a copy of one - so
    the second upload of that name replaces the file of the first.
    """
    directory = Path(uploads_root).expanduser() / SOURCE_FILES_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)

    target = directory / safe_source_filename(name, suffix)
    target.write_bytes(payload)
    return f"{SOURCE_FILES_DIRNAME}/{target.name}"


async def register_file_upload_source(
    session: AsyncSession,
    *,
    name: str,
    filename: str,
    file_path: str,
    sheet_name: Optional[str],
    header_row: int,
    size_bytes: int,
    records: int,
) -> DataSourceDB:
    """Create - or update - the source that reads the file of an upload.

    The source is found by its name and its type: an upload with a name
    that is already a source updates that source, so the panel carries one
    source per name rather than one per upload.
    """
    result = await session.execute(
        select(DataSourceDB).where(
            DataSourceDB.name == name,
            DataSourceDB.source_type == "file_upload",
        )
    )
    source = result.scalars().first()

    config = {
        "filename": filename,
        "file_path": file_path,
        "sheet_name": sheet_name,
        "header_row": header_row,
        "size_bytes": size_bytes,
    }

    if source is None:
        source = DataSourceDB(
            name=name,
            source_type="file_upload",
            config=config,
            # The upload already put the listings into the catalogue, so the
            # source carries what the file carried.
            status="active",
            total_records=records,
            last_records_synced=records,
        )
        session.add(source)
    else:
        source.config = config
        source.status = "active"
        source.total_records = records
        source.last_records_synced = records
        # The file is there and the source reads it, so a failure of an
        # earlier run is not what the source is about any more.
        source.last_error = None
        source.last_sync_status = "success"

    await session.flush()
    return source
