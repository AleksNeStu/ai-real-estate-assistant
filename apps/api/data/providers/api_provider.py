"""
API Data Provider Implementation.

This module provides a generic API provider and a Mock implementation
for fetching property data from external services.
"""

import logging
from typing import List, Optional

import pandas as pd
import requests

from core.security_utils import sanitize_for_log
from data.providers.base import BaseDataProvider
from data.schemas import Property

logger = logging.getLogger(__name__)


class APIProvider(BaseDataProvider):
    """
    Generic API Provider for fetching property data.

    Attributes:
        api_url (str): Base URL of the API.
        api_key (str): API Key for authentication.
        timeout (int): Request timeout in seconds.
    """

    def __init__(self, api_url: str, api_key: Optional[str] = None, timeout: int = 10):
        super().__init__(source=api_url)
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def validate_source(self) -> bool:
        """
        Check if the API is reachable.

        Returns:
            bool: True if reachable, False otherwise.
        """
        try:
            response = requests.get(str(self.source), headers=self.headers, timeout=self.timeout)
            return response.status_code in [
                200,
                401,
                403,
            ]  # 401/403 means reachable but auth failed
        except requests.RequestException:
            logger.error("Failed to connect to API: %s", sanitize_for_log(self.source))
            return False

    def load_data(self) -> pd.DataFrame:
        """
        Load data from the API.

        Returns:
            pd.DataFrame: DataFrame containing raw property data.
        """
        try:
            response = requests.get(
                f"{str(self.source)}/properties", headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            # specific mapping logic should be handled by subclasses or a mapping config
            # Here we assume the API returns a list of dicts compatible with our schema
            return pd.DataFrame(data)
        except Exception as e:
            logger.error("Error loading data from API: %s", sanitize_for_log(e))
            return pd.DataFrame()

    def get_properties(self) -> List[Property]:
        """
        Get validated Property objects.

        Returns:
            List[Property]: List of Property objects.
        """
        df = self.load_data()
        properties = []
        for _, row in df.iterrows():
            try:
                data = row.to_dict()
                prop = Property(**data)
                properties.append(prop)
            except Exception as e:
                logger.warning("Skipping invalid property row: %s", sanitize_for_log(e))
        return properties


class MockRealEstateAPIProvider(APIProvider):
    """
    Mock Provider to simulate a Real Estate API.
    Useful for testing and development without a real API key.
    """

    def __init__(self) -> None:
        super().__init__(api_url="https://mock.api.realestate.com", api_key="mock-key")

    def validate_source(self) -> bool:
        """Always returns True for mock provider."""
        return True

    def load_data(self) -> pd.DataFrame:
        """
        Simulate API response.
        """
        mock_data = [
            {
                "id": "mock_1",
                "title": "Modern Apartment in Warsaw",
                "description": "Beautiful 2-bedroom apartment near city center.",
                "city": "Warsaw",
                "price": 3500,
                "currency": "PLN",
                "property_type": "apartment",
                "listing_type": "rent",
                "rooms": 2,
                "area_sqm": 55.0,
            },
            {
                "id": "mock_2",
                "title": "Cozy Studio in Krakow",
                "description": "Perfect for students.",
                "city": "Krakow",
                "price": 2000,
                "currency": "PLN",
                "property_type": "studio",
                "listing_type": "rent",
                "rooms": 1,
                "area_sqm": 30.0,
            },
        ]
        return pd.DataFrame(mock_data)

    def get_properties(self) -> List[Property]:
        """
        Get properties from mock data.
        """
        df = self.load_data()
        properties = []
        for _, row in df.iterrows():
            data = row.to_dict()
            properties.append(Property(**data))
        return properties
