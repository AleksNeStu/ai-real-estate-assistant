import json
import logging
from pathlib import Path
from typing import Any, List

import pandas as pd
import requests

from core.security_utils import sanitize_for_log
from data.providers.base import BaseDataProvider
from data.schemas import Property

logger = logging.getLogger(__name__)


class JSONDataProvider(BaseDataProvider):
    """Data provider for JSON files or APIs returning JSON lists."""

    def _convert_github_url(self, url: str) -> str:
        """Convert GitHub URL to raw content URL."""
        if "github.com" in url and "/blob/" in url:
            return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        return url

    def validate_source(self) -> bool:
        """Check if the source file or URL exists."""
        src_str = str(self.source)
        if src_str.startswith(("http://", "https://")):
            src_str = self._convert_github_url(src_str)
            try:
                response = requests.head(src_str, allow_redirects=True, timeout=5)
                return response.status_code < 400
            except requests.RequestException:
                return False
        return Path(self.source).is_file()

    def load_data(self) -> pd.DataFrame:
        """Load data from the JSON source into a DataFrame."""
        if self._cache is not None:
            return self._cache

        data = self._fetch_json()

        # Normalize data: ensure it's a list of dicts
        if isinstance(data, dict):
            # If it's a single dict, maybe wrap it? Or maybe it has a key 'properties'?
            if "properties" in data and isinstance(data["properties"], list):
                data = data["properties"]
            elif "data" in data and isinstance(data["data"], list):
                data = data["data"]
            else:
                # Treat as single item
                data = [data]

        if not isinstance(data, list):
            raise ValueError(
                f"JSON data must be a list or contain a list in 'properties'/'data' keys. Got {type(data)}"
            )

        df = pd.DataFrame(data)
        self._cache = df
        return df

    def get_properties(self) -> List[Property]:
        """Convert loaded data to Property objects."""
        data_list = self._fetch_json()

        # Normalize logic repeated here to get raw dicts, or use load_data and to_dict
        # Using load_data() -> DataFrame -> to_dict might lose some nested structure if not careful,
        # but Property schema is flat-ish.
        # Let's use the raw JSON list to avoid DataFrame conversion artifacts (like NaNs for None).

        if isinstance(data_list, dict):
            if "properties" in data_list and isinstance(data_list["properties"], list):
                data_list = data_list["properties"]
            elif "data" in data_list and isinstance(data_list["data"], list):
                data_list = data_list["data"]
            else:
                data_list = [data_list]

        properties = []
        for item in data_list:
            if not isinstance(item, dict):
                continue

            try:
                # Pydantic handles validation and type conversion
                prop = Property(**item)
                properties.append(prop)
            except Exception as e:
                logger.warning("Skipping invalid property item: %s", sanitize_for_log(e))
                continue

        return properties

    def _fetch_json(self) -> Any:
        """Helper to fetch raw JSON data."""
        if isinstance(self.source, (str, Path)):
            src_str = str(self.source)
            if src_str.startswith(("http://", "https://")):
                src_str = self._convert_github_url(src_str)
                response = requests.get(src_str, timeout=10)
                response.raise_for_status()
                return response.json()
            else:
                with open(self.source, "r", encoding="utf-8") as f:
                    return json.load(f)
        raise ValueError("Invalid source type")
