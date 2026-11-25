"""
Excel data loader for property data ingestion.

Supports .xlsx files (via openpyxl), with optional .xls (xlrd) and
.ods (odfpy) support when those extras are installed.

Provides:
- Sheet detection and selection (by name or index)
- Configurable header row
- Reuse of format_df normalization from csv_loader
- PropertyCollection integration for validated output
"""

import logging
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional, Union
from urllib.parse import urlparse

import pandas as pd

from core.security_utils import sanitize_for_log, validate_file_path
from data.csv_loader import DataLoaderCsv
from data.schemas import PropertyCollection

logger = logging.getLogger(__name__)

# The engine that reads each spreadsheet format, and the module that has to
# be installed for it. Only ``.xlsx`` is a runtime dependency; ``.xls`` and
# ``.ods`` are extras, so a deployment without them cannot read those files.
# The capability endpoint publishes the formats the deployment can read, so
# the mapping lives with the loader that reads it.
EXCEL_ENGINES = {".xlsx": "openpyxl", ".xls": "xlrd", ".ods": "odf"}

# The supported Excel extensions are the formats the map names, so the set
# and the map cannot drift apart. Everything else that reads a spreadsheet
# - the import chain, the capability endpoint - takes its formats from here.
EXCEL_EXTENSIONS = set(EXCEL_ENGINES)


@lru_cache(maxsize=None)
def reader_installed(module: str) -> bool:
    """True when the module that reads a spreadsheet format is installed.

    A format whose reader is missing fails at the read, not at the upload, so
    the deployment has to be able to answer the question before the interface
    offers the file.

    The answer is remembered: a reader is installed or it is not, and the
    question is asked on every answer of the capability endpoint. A
    deployment installs its readers when it is built, so the answer is the
    same for the life of the process - and a test that needs another answer
    lets the memory go with ``reader_installed.cache_clear()``.
    """
    import importlib.util

    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


# Default allowed base directories for local Excel files. Allow override via
# the EXCEL_ALLOWED_BASE_DIR env var (comma-separated list of absolute paths).
# The OS temp dir is included because the /admin/ingest/upload endpoint stages
# uploaded files via tempfile.NamedTemporaryFile, which lives there. Server-
# created temp files are trusted; the path-traversal guard below still applies.
_default_allowed = [
    os.path.abspath(os.getcwd()),
    os.path.abspath(os.path.join(os.getcwd(), "data")),
    os.path.abspath(os.path.join(os.getcwd(), "uploads")),
    os.path.abspath(tempfile.gettempdir()),
]
_env_allowed = os.getenv("EXCEL_ALLOWED_BASE_DIR", "").strip()
ALLOWED_BASE_DIRS: list[str] = (
    [p.strip() for p in _env_allowed.split(",") if p.strip()] if _env_allowed else _default_allowed
)


def _is_url(path: Path | str) -> bool:
    """Check if path is a URL."""
    s = str(path)
    return s.startswith(("http://", "https://"))


def _get_suffix(path: Path | str) -> str:
    """Extract suffix from path or URL."""
    s = str(path)
    parsed = urlparse(s)
    p = parsed.path if parsed.scheme and parsed.netloc else s
    return Path(p).suffix.lower()


def _safe_local_path(file_path: Path | str) -> Optional[Path]:
    """Return a Path if ``file_path`` resolves inside an allowed base dir.

    Validates against path traversal patterns and rejects any path whose
    resolved form lies outside one of ``ALLOWED_BASE_DIRS``. Returns ``None``
    for URLs (which are not local paths) or when the file does not exist.
    """
    if _is_url(file_path):
        return None
    if not validate_file_path(str(file_path)):
        return None
    try:
        resolved = Path(str(file_path)).resolve()
    except OSError:
        return None
    for base in ALLOWED_BASE_DIRS:
        try:
            base_resolved = Path(base).resolve()
        except OSError:
            continue
        try:
            resolved.relative_to(base_resolved)
            return resolved
        except ValueError:
            continue
    return None


class ExcelDataLoader:
    """
    Standalone Excel data loader with sheet selection and normalization.

    This loader reads Excel files (.xlsx, .xls, .ods), applies the shared
    ``format_df`` normalization pipeline from ``DataLoaderCsv``, and
    optionally converts the result into a validated ``PropertyCollection``.

    Supports both local file paths and URLs (http/https).

    Usage::

        loader = ExcelDataLoader("properties.xlsx", sheet_name="Listings")
        df = loader.load()                       # raw DataFrame
        df_norm = loader.load_normalized()       # normalized DataFrame
        collection = loader.load_collection()     # PropertyCollection

    Args:
        file_path: Path to the Excel file, or URL (http/https).
        sheet_name: Sheet name to load. None loads the first sheet.
        sheet_index: Sheet index (0-based) as alternative to name.
            Ignored when ``sheet_name`` is provided.
        header_row: Row number to use as header (0-indexed, default 0).
        max_rows: Optional cap on number of rows to return.
    """

    def __init__(
        self,
        file_path: Path | str,
        sheet_name: Optional[str] = None,
        sheet_index: Optional[int] = None,
        header_row: int = 0,
        max_rows: Optional[int] = None,
    ) -> None:
        self._raw_path = file_path
        self.file_path = (
            Path(file_path) if isinstance(file_path, str) and not _is_url(file_path) else file_path
        )
        self.sheet_name = sheet_name
        self.sheet_index = sheet_index
        self.header_row = header_row
        self.max_rows = max_rows

        # Validate file exists (only for local paths, not URLs)
        if not _is_url(file_path):
            safe_path = _safe_local_path(file_path)
            if safe_path is None:
                raise ValueError(f"Excel file path is not within an allowed directory: {file_path}")
            if safe_path.exists() and not safe_path.is_file():
                raise ValueError(f"Not a file: {safe_path}")
            if not safe_path.exists():
                logger.warning("Excel file not found: %s", sanitize_for_log(safe_path))

        # Validate extension
        suffix = _get_suffix(file_path)
        if suffix and suffix not in EXCEL_EXTENSIONS:
            raise ValueError(
                f"Unsupported format '{suffix}'. Supported: {', '.join(sorted(EXCEL_EXTENSIONS))}"
            )

    # ------------------------------------------------------------------
    # Sheet discovery
    # ------------------------------------------------------------------

    def get_sheet_names(self) -> List[str]:
        """
        Return sheet names in the workbook.

        Returns an empty list when the local file does not exist.
        For URLs, delegates to pandas which handles remote reads.
        """
        file_str = str(self._raw_path)
        suffix = _get_suffix(file_str)

        # For local paths, check existence
        if not _is_url(file_str):
            p = _safe_local_path(file_str)
            if p is None:
                logger.warning(
                    "Excel path rejected (not in allowed dir): %s", sanitize_for_log(file_str)
                )
                return []
            if not p.exists():
                logger.warning("Excel file not found: %s", sanitize_for_log(p))
                return []
            # Use the validated path going forward
            file_str = str(p)

        try:
            if suffix == ".xlsx":
                import openpyxl

                wb = openpyxl.load_workbook(file_str, read_only=True, data_only=True)
                names = list(wb.sheetnames)
                wb.close()
                return names

            if suffix == ".xls":
                import xlrd  # optional

                workbook = xlrd.open_workbook(file_str)
                return list(workbook.sheet_names())

            if suffix == ".ods":
                try:
                    from odf.opendocument import load

                    doc = load(file_str)
                    return list(doc.spreadsheets.keys())
                except ImportError:
                    xf = pd.ExcelFile(file_str, engine="odf")
                    names = list(xf.sheet_names)
                    xf.close()
                    return names

            # Fallback: let pandas detect the engine
            xf = pd.ExcelFile(file_str)
            names = list(xf.sheet_names)
            xf.close()
            return names

        except ImportError as exc:
            raise ImportError(
                "Excel file reading requires optional dependencies. "
                "For .xlsx: openpyxl. For .xls: xlrd. For .ods: odfpy."
            ) from exc
        except Exception as exc:
            logger.error(
                "Failed to read sheet names from %s: %s",
                sanitize_for_log(file_str),
                sanitize_for_log(exc),
            )
            raise

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _resolve_sheet(self) -> Optional[Union[str, int]]:
        """Return the pandas sheet_name argument."""
        if self.sheet_name:
            return self.sheet_name
        if self.sheet_index is not None:
            return self.sheet_index
        return None  # first sheet

    def _read_kwargs(self) -> dict[str, Any]:
        """Build keyword arguments for ``pd.read_excel``."""
        suffix = _get_suffix(self._raw_path)
        kwargs: dict[str, Any] = {}

        sheet = self._resolve_sheet()
        if sheet is not None:
            kwargs["sheet_name"] = sheet

        kwargs["header"] = self.header_row

        # Engine selection. The engine that reads the format is the one the
        # mapping names; `load` has already refused a format whose reader is
        # not installed, so the reader is there.
        if suffix in EXCEL_ENGINES:
            kwargs["engine"] = EXCEL_ENGINES[suffix]

        return kwargs

    def load(self) -> pd.DataFrame:
        """
        Load the Excel file into a raw DataFrame.

        Returns:
            DataFrame with the raw contents of the selected sheet.

        Raises:
            ValueError: If the file is not a supported Excel format.
            ImportError: If the required engine library is not installed.
        """
        file_str = str(self._raw_path)
        suffix = _get_suffix(file_str)
        if suffix not in EXCEL_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: {suffix}. "
                f"Excel loader supports: {', '.join(sorted(EXCEL_EXTENSIONS))}"
            )

        # The reader of the format has to be there. The capability endpoint
        # publishes the formats this deployment can read, so a file of a
        # format the deployment cannot read is refused by name - and not by
        # a failure of pandas that says nothing about the cause.
        engine = EXCEL_ENGINES.get(suffix)
        if engine is not None and not reader_installed(engine):
            raise ImportError(
                f"The reader for {suffix} files is not installed ({engine}). "
                f"Install it, or give the catalogue a file this deployment can read."
            )

        kwargs = self._read_kwargs()
        df = pd.read_excel(file_str, **kwargs)

        logger.info(
            "Excel loaded from %s (sheet=%s, header_row=%d, rows=%d)",
            sanitize_for_log(file_str),
            sanitize_for_log(self._resolve_sheet() or "default"),
            self.header_row,
            len(df),
        )
        return df

    def load_normalized(self) -> pd.DataFrame:
        """
        Load and normalize the Excel data using ``format_df``.

        Applies the shared normalization pipeline from ``DataLoaderCsv``
        (column renaming, type coercion, missing-value filling, etc.).
        """
        df = self.load()
        df_norm = DataLoaderCsv.format_df(df, rows_count=self.max_rows)
        logger.info("Normalized %d rows from %s", len(df_norm), sanitize_for_log(self.file_path))
        return df_norm

    def load_collection(
        self,
        source: Optional[str] = None,
    ) -> PropertyCollection:
        """
        Load, normalize, and validate into a ``PropertyCollection``.

        Args:
            source: Optional source identifier attached to each property.

        Returns:
            ``PropertyCollection`` with validated ``Property`` objects.
        """
        df_norm = self.load_normalized()
        collection = PropertyCollection.from_dataframe(
            df_norm,
            source=source or str(self.file_path),
            source_type="excel",
        )
        logger.info(
            "Created PropertyCollection with %d properties from %s",
            collection.total_count,
            sanitize_for_log(self.file_path),
        )
        return collection
