"""Rejestr Cen Nieruchomości (RCN) — official Polish transaction prices.

The RCN is the register of real-estate transactions kept by the starostas and
published by Główny Urząd Geodezji i Kartografii. Since 13 February 2026 its data
is free of charge (Dz.U. 2025 poz. 1542) and is exported as GeoParquet, refreshed
weekly:

    https://opendata.geoportal.gov.pl/InneDane/latest_exports/rcn_transakcje_ceny/

No API key, no licence, no scraping: these are the prices people actually paid,
which is what separates this from a portal's automated valuation model.
"""

from data.rcn.rcn_client import (
    RCN_EXPORT_URL,
    RCN_VOIVODESHIPS,
    RcnExportError,
    download_export,
    parse_rcn_address,
    read_export,
)
from data.rcn.rcn_models import RCNAddress, RCNTransaction

__all__ = [
    "RCNAddress",
    "RCN_EXPORT_URL",
    "RCNTransaction",
    "RCN_VOIVODESHIPS",
    "RcnExportError",
    "download_export",
    "parse_rcn_address",
    "read_export",
]
