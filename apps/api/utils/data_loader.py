import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List, Optional

import pandas as pd

from core.security_utils import sanitize_for_log
from data.csv_loader import DataLoaderCsv
from data.schemas import PropertyCollection

logger = logging.getLogger(__name__)


class ParallelDataLoader:
    """
    Handles parallel loading of multiple data files.
    """

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers

    def load_files(
        self, files: List[Any], progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[PropertyCollection]:
        """
        Load multiple files in parallel.

        Args:
            files: List of uploaded files (Streamlit UploadedFile objects) or paths
            progress_callback: Optional function(progress, message) to call with updates

        Returns:
            List of PropertyCollection objects
        """
        results = []
        total_files = len(files)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_single_file, file): file for file in files
            }

            completed_count = 0
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                filename = getattr(file, "name", str(file))

                try:
                    collection = future.result()
                    if collection:
                        results.append(collection)
                except Exception as e:
                    logger.error(
                        "Error loading file %s: %s", sanitize_for_log(filename), sanitize_for_log(e)
                    )

                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count / total_files, f"Processed {filename}")

        return results

    def _process_single_file(self, file: Any) -> Optional[PropertyCollection]:
        """Process a single file: read, format, and convert to collection."""
        try:
            name = getattr(file, "name", str(file))
            name_lower = name.lower()

            # Read dataframe
            # Note: file pointer needs to be at 0 if it was read before
            if hasattr(file, "seek"):
                file.seek(0)

            if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
                df = pd.read_excel(file)
            else:
                # Handle CSV
                df = pd.read_csv(file)

            # Format dataframe
            df_formatted = DataLoaderCsv.format_df(df)

            # Convert to collection
            return PropertyCollection.from_dataframe(df_formatted, source=name)
        except Exception as e:
            logger.error("Failed to process file: %s", sanitize_for_log(e))
            raise e
