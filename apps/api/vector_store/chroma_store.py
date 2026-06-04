"""
ChromaDB vector store implementation with persistence.

This module provides a persistent vector store for property embeddings
using ChromaDB with FastEmbed embeddings.
"""

import logging
import math
import os
import platform
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Union, cast

import pandas as pd
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.security_utils import sanitize_for_log

try:
    from langchain_chroma import Chroma
except Exception:
    Chroma = None  # type: ignore[misc,assignment]

from config.settings import settings
from data.schemas import Property, PropertyCollection

_ChromaSettings: Any = None
try:
    from chromadb.config import Settings as _ChromaSettings
except Exception:
    pass

_FastEmbedEmbeddings: Any = None
try:
    from langchain_community.embeddings.fastembed import (  # type: ignore[no-redef]
        FastEmbedEmbeddings as _FastEmbedEmbeddings,
    )
except Exception:
    pass

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

# Configure logger
logger = logging.getLogger(__name__)

_INDEXING_EXECUTOR: Optional[ThreadPoolExecutor] = None


def _get_indexing_executor() -> ThreadPoolExecutor:
    global _INDEXING_EXECUTOR
    if _INDEXING_EXECUTOR is None:
        max_workers = int(os.getenv("CHROMA_INDEXING_WORKERS", "1") or "1")
        _INDEXING_EXECUTOR = ThreadPoolExecutor(max_workers=max_workers)
    return _INDEXING_EXECUTOR


class ChromaPropertyStore:
    """
    Persistent vector store for property data using ChromaDB.

    This class handles:
    - Property embedding and storage
    - Semantic search
    - Metadata filtering
    - Persistence to disk
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "properties",
        embedding_model: str = "BAAI/bge-small-en-v1.5",
    ):
        """
        Initialize ChromaDB vector store.

        Args:
            persist_directory: Directory for persistent storage (default: ./chroma_db)
            collection_name: Name of the collection
            embedding_model: FastEmbed model to use
        """
        # Set default persist directory
        if persist_directory is None:
            persist_directory = os.path.join(os.getcwd(), "chroma_db")

        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        # Create persist directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize embeddings
        self.embeddings: Optional[Embeddings] = self._create_embeddings(embedding_model)

        # Initialize or load vector store
        self.vector_store: Optional[Chroma] = self._initialize_vector_store()
        self._vector_store_local = threading.local()
        self._vector_store_local.store = self.vector_store

        # Text splitter for long descriptions
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        self._documents: List[Document] = []
        # We no longer load all IDs into memory to avoid startup freeze
        self._doc_ids: Set[str] = set()
        self._cache_lock = threading.Lock()
        self._vector_lock = threading.Lock()
        self._indexing_event = threading.Event()
        self._index_future: Optional[Future[int]] = None

    def _get_vector_store(self) -> Optional[Chroma]:
        store = getattr(self._vector_store_local, "store", None)
        return store if store is not None else self.vector_store

    def _create_embeddings(_self, model_name: str) -> Optional[Embeddings]:
        try:
            is_windows = platform.system().lower() == "windows"
            force_fastembed = (
                os.getenv("CHROMA_FORCE_FASTEMBED") == "1" or os.getenv("FORCE_FASTEMBED") == "1"
            )
            if _FastEmbedEmbeddings is not None and not is_windows:
                return cast(Embeddings, _FastEmbedEmbeddings(model_name=model_name))
            if _FastEmbedEmbeddings is not None and is_windows and force_fastembed:
                return cast(Embeddings, _FastEmbedEmbeddings(model_name=model_name))
            if _FastEmbedEmbeddings is not None and is_windows:
                logger.warning(
                    "FastEmbed is disabled on Windows for stability. "
                    "Set CHROMA_FORCE_FASTEMBED=1 to force enable."
                )
        except Exception as e:
            logger.warning("FastEmbed initialization failed: %s", sanitize_for_log(e))

        try:
            if settings.openai_api_key:
                from langchain_openai import OpenAIEmbeddings

                return cast(Embeddings, OpenAIEmbeddings())
        except Exception as e:
            logger.warning("OpenAI embeddings unavailable: %s", sanitize_for_log(e))

        return None

    def _initialize_vector_store(self) -> Optional[Chroma]:
        """Initialize or load existing ChromaDB vector store."""
        if Chroma is None:
            logger.warning("Chroma is unavailable; vector store features are disabled")
            return None
        if self.embeddings is None:
            logger.warning("Embeddings unavailable; vector store features are disabled")
            return None

        try:
            client_settings = None
            if _ChromaSettings is not None:
                client_settings = _ChromaSettings(anonymized_telemetry=False)

            force_persist = os.getenv("CHROMA_FORCE_PERSIST") == "1"
            use_persist = force_persist or bool(settings.vector_persist_enabled)

            if use_persist:
                vector_store = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=str(self.persist_directory),
                    client_settings=client_settings,
                )

                # Check if collection has any documents
                try:
                    collection_stats = vector_store._collection.count()
                    logger.info(
                        "Loaded existing ChromaDB collection with %s documents",
                        sanitize_for_log(collection_stats),
                    )
                except Exception as e:
                    logger.warning("Could not get collection stats: %s", sanitize_for_log(e))

                # Removed blocking ID loading loop for performance
                return vector_store
            else:
                # Directly use in-memory on platforms where persistence is disabled
                vector_store = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                )
                logger.info(
                    "Using in-memory Chroma vector store (persistence disabled for this platform)"
                )
                logger.warning("Persistent vector store unavailable; using in-memory store")
                return vector_store

        except BaseException as e:
            logger.warning("Persistent Chroma init failed: %s", sanitize_for_log(e))

            # Fallback: in-memory Chroma (no persistence)
            try:
                vector_store = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                )
                logger.info("Initialized in-memory Chroma vector store (no persistence)")
                logger.warning("Persistent vector store unavailable; using in-memory store")
                return vector_store
            except BaseException as e2:
                logger.error("In-memory Chroma init failed: %s", sanitize_for_log(e2))
                raise

    def property_to_document(self, prop: Property) -> Document:
        """
        Convert Property to LangChain Document.

        Args:
            property: Property instance

        Returns:
            Document with property text and metadata
        """
        # Create comprehensive text representation
        text = prop.to_search_text()

        # Create metadata (must be JSON-serializable)
        def _nf(x: Any) -> Optional[float]:
            return float(x) if (x is not None and not pd.isna(x)) else None

        def _ni(x: Any) -> Optional[int]:
            if x is None or pd.isna(x):
                return None
            try:
                return int(float(x))
            except (TypeError, ValueError):
                return None

        raw_energy = getattr(prop, "energy_cert", None)
        energy_cert = str(raw_energy).strip() if raw_energy is not None else None
        if energy_cert == "":
            energy_cert = None

        metadata: Dict[str, Any] = {
            "id": prop.id or "unknown",
            "country": getattr(prop, "country", None),
            "region": getattr(prop, "region", None),
            "city": prop.city,
            "district": getattr(prop, "district", None),
            "price": _nf(prop.price),
            "rooms": (_nf(prop.rooms) or 0.0),
            "bathrooms": (_nf(prop.bathrooms) or 0.0),
            "price_per_sqm": _nf(getattr(prop, "price_per_sqm", None)),
            "currency": getattr(prop, "currency", None),
            "has_parking": prop.has_parking,
            "has_garden": prop.has_garden,
            "has_pool": prop.has_pool,
            "has_garage": prop.has_garage,
            "has_elevator": prop.has_elevator,
            "property_type": (
                prop.property_type.value
                if hasattr(prop.property_type, "value")
                else str(prop.property_type)
            ),
            "listing_type": (
                prop.listing_type.value
                if hasattr(prop.listing_type, "value")
                else str(prop.listing_type)
            ),
            "source_url": prop.source_url or "",
            "lat": _nf(getattr(prop, "latitude", None)),
            "lon": _nf(getattr(prop, "longitude", None)),
            "year_built": _ni(getattr(prop, "year_built", None)),
            "energy_cert": energy_cert,
        }

        # Add optional fields if present
        if prop.neighborhood:
            metadata["neighborhood"] = prop.neighborhood

        if prop.area_sqm is not None and not pd.isna(prop.area_sqm):
            metadata["area_sqm"] = float(prop.area_sqm)

        if prop.price_per_sqm is not None and not pd.isna(prop.price_per_sqm):
            metadata["price_per_sqm"] = float(prop.price_per_sqm)

        if prop.negotiation_rate:
            metadata["negotiation_rate"] = (
                prop.negotiation_rate.value
                if hasattr(prop.negotiation_rate, "value")
                else str(prop.negotiation_rate)
            )

        # Sanitize metadata: only primitives (str, int, float, bool, None); convert datetimes
        def _sanitize_val(v: Any) -> Any:
            try:
                if v is None:
                    return None
                if isinstance(v, float):
                    if pd.isna(v) or v != v:
                        return None
                    return float(v)
                if isinstance(v, (str, int, bool)):
                    return v
                if isinstance(v, (datetime, pd.Timestamp)):
                    return v.isoformat()
                # lists/dicts or other complex types are not allowed in Chroma metadata
            except Exception:
                return None

        sanitized = {}
        for k, v in metadata.items():
            sv = _sanitize_val(v)
            if sv is not None:
                sanitized[k] = sv

        metadata = sanitized

        return Document(page_content=text, metadata=metadata)

    def get_properties_by_ids(self, property_ids: List[str]) -> List[Document]:
        """
        Retrieve specific properties by their IDs.

        Args:
            property_ids: List of property IDs to retrieve

        Returns:
            List of Documents
        """
        vector_store = self._get_vector_store()
        if not vector_store:
            # Fallback to cache
            with self._cache_lock:
                return [
                    doc for doc in self._documents if str(doc.metadata.get("id")) in property_ids
                ]

        try:
            # Fetch from Chroma
            results = vector_store._collection.get(
                ids=property_ids,
                include=["documents", "metadatas"],  # type: ignore[list-item]
            )

            documents = []
            if results and results["ids"]:
                for i, _doc_id in enumerate(results["ids"]):
                    # Handle potential missing data
                    content = results["documents"][i] if results["documents"] else ""
                    metadata = results["metadatas"][i] if results["metadatas"] else {}

                    documents.append(Document(page_content=content, metadata=metadata))

            return documents
        except Exception as e:
            logger.error("Error retrieving properties by IDs: %s", sanitize_for_log(e))
            return []

    def add_properties(self, properties: List[Property], batch_size: int = 100) -> int:
        """
        Add properties to the vector store.

        Args:
            properties: List of Property instances
            batch_size: Number of properties to process at once

        Returns:
            Number of properties added
        """
        # Convert all to documents first
        documents: List[Document] = []
        for prop in properties:
            try:
                doc = self.property_to_document(prop)
                documents.append(doc)
            except Exception as e:
                logger.warning(
                    "Skipping property %s: %s", sanitize_for_log(prop.id), sanitize_for_log(e)
                )
                continue

        if not documents:
            logger.warning("No valid documents to add")
            return 0

        vector_store = self._get_vector_store()

        # If vector store is unavailable, keep documents in fallback cache only
        if vector_store is None:
            total_cached = 0
            with self._cache_lock:
                for doc in documents:
                    doc_id = str(doc.metadata.get("id", ""))
                    if doc_id and doc_id in self._doc_ids:
                        continue
                    self._documents.append(doc)
                    if doc_id:
                        self._doc_ids.add(doc_id)
                    total_cached += 1
            logger.info(
                "Vector store disabled; cached %s properties in memory",
                sanitize_for_log(total_cached),
            )
            return total_cached

        # Add documents in batches
        total_cached = 0
        total_indexed = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            batch_ids = [str(d.metadata.get("id", f"doc-{i + j}")) for j, d in enumerate(batch)]

            with self._cache_lock:
                for doc, doc_id in zip(batch, batch_ids, strict=False):
                    if doc_id and doc_id in self._doc_ids:
                        continue
                    self._documents.append(doc)
                    if doc_id:
                        self._doc_ids.add(doc_id)
                    total_cached += 1

            # 1. Filter duplicates (check against DB)
            try:
                if vector_store:
                    existing = vector_store._collection.get(ids=batch_ids, include=[])
                    existing_ids = set(existing.get("ids", []))

                    new_batch = []
                    new_ids = []
                    for doc, doc_id in zip(batch, batch_ids, strict=False):
                        if doc_id not in existing_ids:
                            new_batch.append(doc)
                            new_ids.append(doc_id)

                    if not new_batch:
                        continue

                    batch = new_batch
                    batch_ids = new_ids
            except Exception as e:
                logger.warning("Error checking duplicates: %s", sanitize_for_log(e))

            try:
                # 2. Generate Embeddings (CPU/Network) - WITHOUT LOCK
                texts = [d.page_content for d in batch]
                metadatas = [d.metadata for d in batch]

                embeddings = None
                if self.embeddings:
                    embeddings = self.embeddings.embed_documents(texts)

                # 3. Write to DB - WITH LOCK
                with self._vector_lock:
                    if embeddings:
                        EmbeddingVector = Union[Sequence[float], Sequence[int]]
                        embeddings_for_chroma: List[EmbeddingVector] = []
                        for vec in embeddings:
                            embeddings_for_chroma.append(vec)

                        MetadataValue = Union[str, int, float, bool, None]

                        def _sanitize_metadata(md: Dict[str, Any]) -> Dict[str, Any]:
                            sanitized: Dict[str, Any] = {}
                            for key, value in md.items():
                                if isinstance(value, (str, int, float, bool)) or value is None:
                                    sanitized[str(key)] = value
                                else:
                                    sanitized[str(key)] = str(value)
                            return sanitized

                        metadatas_for_chroma: List[Mapping[str, MetadataValue]] = []
                        for md in metadatas:
                            metadatas_for_chroma.append(_sanitize_metadata(md))

                        # Direct add to collection to avoid re-embedding
                        vector_store._collection.add(
                            ids=batch_ids,
                            embeddings=embeddings_for_chroma,
                            metadatas=cast(Any, metadatas_for_chroma),
                            documents=texts,
                        )
                    else:
                        # Fallback if no embeddings (rare)
                        vector_store.add_documents(batch, ids=batch_ids)

                # Update local cache for fallback search (if we want to keep it sync)
                # Note: We don't load initial docs, so this cache is partial.
                # Moved to before embedding to allow search during indexing
                # with self._cache_lock:
                #    self._documents.extend(batch)

                total_indexed += len(batch)
                logger.info(
                    "Added batch %s: %s properties",
                    sanitize_for_log(i // batch_size + 1),
                    len(batch),
                )

            except Exception as e:
                logger.error("Error adding batch: %s", sanitize_for_log(e))
                continue

        if total_indexed > 0:
            logger.info(
                "Total properties added to vector store: %s", sanitize_for_log(total_indexed)
            )

        return total_cached

    def add_property_collection(
        self,
        collection: PropertyCollection,
        replace_existing: bool = False,
        batch_size: int = 100,
    ) -> int:
        """
        Add a PropertyCollection to the vector store.

        Args:
            collection: PropertyCollection instance
            replace_existing: Whether to clear existing data first

        Returns:
            Number of properties added
        """
        if replace_existing:
            self.clear()

        return self.add_properties(collection.properties, batch_size=batch_size)

    def add_property_collection_async(
        self,
        collection: PropertyCollection,
        replace_existing: bool = False,
        batch_size: int = 100,
    ) -> Future[int]:
        """
        Add a PropertyCollection in a background thread.

        Returns:
            Future that resolves to the number of properties added.
        """
        if self._index_future is not None and not self._index_future.done():
            return self._index_future

        def _work() -> int:
            self._indexing_event.set()
            try:
                self._vector_store_local.store = self.vector_store
                if Chroma is not None and isinstance(self.vector_store, Chroma):
                    self._vector_store_local.store = self._initialize_vector_store()
                return self.add_property_collection(
                    collection,
                    replace_existing=replace_existing,
                    batch_size=batch_size,
                )
            finally:
                self._indexing_event.clear()

        executor = _get_indexing_executor()
        self._index_future = executor.submit(_work)
        return self._index_future

    def _build_chroma_filter(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Build ChromaDB filter dictionary from user filters.

        Args:
            filters: Dictionary of filters from QueryAnalysis or SearchCriteria

        Returns:
            ChromaDB compatible filter dict or None
        """
        if not filters:
            return None

        conditions = []

        # City (Case insensitive handled by query analyzer normalization,
        # but Chroma is exact match. We rely on metadata being normalized)
        if "city" in filters:
            conditions.append({"city": filters["city"]})

        # Price Range
        if "min_price" in filters:
            conditions.append({"price": {"$gte": float(filters["min_price"])}})
        if "max_price" in filters:
            conditions.append({"price": {"$lte": float(filters["max_price"])}})

        # Rooms (treat as minimum)
        if "rooms" in filters:
            conditions.append({"rooms": {"$gte": float(filters["rooms"])}})

        # Year Built
        if "year_built_min" in filters:
            conditions.append({"year_built": {"$gte": int(filters["year_built_min"])}})
        if "year_built_max" in filters:
            conditions.append({"year_built": {"$lte": int(filters["year_built_max"])}})

        # Amenities (Booleans)
        for key in [
            "has_parking",
            "has_garden",
            "has_pool",
            "has_elevator",
            "has_garage",
            "has_bike_room",
            "is_furnished",
            "pets_allowed",
            "has_balcony",
        ]:
            if filters.get(key) is True:
                conditions.append({key: True})
            elif filters.get(key) is False:
                conditions.append({key: False})

        # Energy Ratings
        if "energy_ratings" in filters and filters["energy_ratings"]:
            ratings = filters["energy_ratings"]
            if len(ratings) == 1:
                conditions.append({"energy_cert": ratings[0]})
            else:
                conditions.append({"energy_cert": {"$in": ratings}})

        # Property Type
        if "property_type" in filters:
            ptype = filters["property_type"]
            val = ptype.value if hasattr(ptype, "value") else str(ptype)
            conditions.append({"property_type": val})

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    def search(
        self, query: str, k: int = 5, filter: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> List[tuple[Document, float]]:
        """
        Search for properties by semantic similarity.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter (Chroma format or user format)
            **kwargs: Additional search parameters

        Returns:
            List of (Document, score) tuples
        """
        try:
            vector_store = self._get_vector_store()
            # We trust the lock to handle concurrency with indexing
            if vector_store is not None:
                # Build filter if it looks like user filters (flat dict)
                # If it has operators like $and, assume it's already Chroma format
                chroma_filter = filter
                if filter and not any(k.startswith("$") for k in filter.keys()):
                    # Check if it needs conversion (heuristic)
                    # Keys may be simple fields with simple values; range keys require conversion
                    if any(
                        k in ["min_price", "max_price", "year_built_min"] for k in filter.keys()
                    ):
                        chroma_filter = self._build_chroma_filter(filter)

                with self._vector_lock:
                    results = vector_store.similarity_search_with_score(
                        query=query, k=k, filter=chroma_filter, **kwargs
                    )
                    return results
            else:
                raise RuntimeError("no_vector_store")
        except Exception as e:
            # Fallback to simple text search on cached documents
            try:
                q = [t for t in query.lower().split() if t]
                scored: List[tuple[Document, float]] = []
                with self._cache_lock:
                    docs = list(self._documents)

                if not docs:
                    # If we have a vector store but search failed, maybe it's empty or locked?
                    # If we have no docs in memory, we can't do anything.
                    logger.warning("Search failed and no cached docs: %s", sanitize_for_log(e))
                    return []

                # Apply filters manually for fallback
                filtered_docs = docs
                if filter:
                    # Basic manual filtering (simplified)
                    if "city" in filter:
                        filtered_docs = [
                            d for d in filtered_docs if d.metadata.get("city") == filter["city"]
                        ]
                    # ... add more manual filters if needed, but this is fallback

                for d in filtered_docs:
                    txt = d.page_content.lower()
                    s = float(sum(1 for t in q if t in txt))
                    if s > 0:
                        scored.append((d, s))
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[:k]
            except Exception:
                logger.error("Search error: %s", sanitize_for_log(e))
                return []

    def _build_geo_filter(self, lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
        """
        Build ChromaDB filter for bounding box around a point.
        """
        # 1 deg lat ~ 111.32 km
        lat_delta = radius_km / 111.32
        min_lat = lat - lat_delta
        max_lat = lat + lat_delta

        # 1 deg lon ~ 111.32 * cos(lat) km
        # Clamp lat to -89/89 to avoid division by zero or extreme distortion
        clamped_lat = max(min(lat, 89.0), -89.0)
        lon_delta = radius_km / (111.32 * math.cos(math.radians(clamped_lat)))
        min_lon = lon - lon_delta
        max_lon = lon + lon_delta

        return [
            {"lat": {"$gte": min_lat}},
            {"lat": {"$lte": max_lat}},
            {"lon": {"$gte": min_lon}},
            {"lon": {"$lte": max_lon}},
        ]

    def _build_bbox_filter(
        self,
        min_lat: Optional[float],
        max_lat: Optional[float],
        min_lon: Optional[float],
        max_lon: Optional[float],
    ) -> List[Dict[str, Any]]:
        conditions: List[Dict[str, Any]] = []
        if min_lat is not None:
            conditions.append({"lat": {"$gte": min_lat}})
        if max_lat is not None:
            conditions.append({"lat": {"$lte": max_lat}})
        if min_lon is not None:
            conditions.append({"lon": {"$gte": min_lon}})
        if max_lon is not None:
            conditions.append({"lon": {"$lte": max_lon}})
        return conditions

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate Haversine distance in km."""
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(
            math.radians(lat2)
        ) * math.sin(dlon / 2) * math.sin(dlon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _point_in_polygon(self, lat: float, lon: float, polygon: List[List[float]]) -> bool:
        """
        Check if a point is inside a polygon using ray casting algorithm.

        Args:
            lat: Point latitude
            lon: Point longitude
            polygon: List of [lon, lat] coordinate pairs (GeoJSON format)

        Returns:
            True if point is inside polygon, False otherwise
        """
        if len(polygon) < 3:
            return False

        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i][0], polygon[i][1]  # lon, lat
            xj, yj = polygon[j][0], polygon[j][1]  # lon, lat

            # Ray casting: check if ray from point crosses edge
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside

            j = i

        return inside

    def hybrid_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 5,
        alpha: float = 0.7,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None,
        polygon: Optional[List[List[float]]] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = "desc",
        ranking_weights: Optional[Any] = None,
    ) -> List[tuple[Document, float]]:
        """
        Perform hybrid search (Vector + Keyword Rescoring) with filters, geo, and sorting.

        Args:
            query: Search query
            filters: Metadata filters
            k: Number of results
            alpha: Weight for vector score (overridden by ranking_weights if provided)
            lat: Latitude for geo-search
            lon: Longitude for geo-search
            radius_km: Radius in km
            polygon: GeoJSON polygon coordinates for polygon-based filtering
            sort_by: Field to sort by (e.g. 'price', 'price_per_sqm')
            sort_order: 'asc' or 'desc'
            ranking_weights: Optional RankingWeights object for runtime configuration.
                            When provided, its alpha value overrides the alpha parameter.

        Returns:
            List of (Document, combined_score) tuples
        """
        # Use alpha from ranking_weights if provided
        if ranking_weights is not None:
            effective_alpha = ranking_weights.alpha
        else:
            effective_alpha = alpha
        # 0. Prepare Filters
        final_filter = filters
        # Convert simple dict to Chroma filter if needed
        if filters and not any(key.startswith("$") for key in filters.keys()):
            final_filter = self._build_chroma_filter(filters)

        # Add Geo Bounding Box
        if lat is not None and lon is not None and radius_km is not None:
            geo_conditions = self._build_geo_filter(lat, lon, radius_km)
            if final_filter:
                if "$and" in final_filter:
                    final_filter["$and"].extend(geo_conditions)
                else:
                    final_filter = {"$and": [final_filter] + geo_conditions}
            else:
                final_filter = {"$and": geo_conditions}

        bbox_conditions = self._build_bbox_filter(min_lat, max_lat, min_lon, max_lon)
        if bbox_conditions:
            if final_filter:
                if "$and" in final_filter:
                    final_filter["$and"].extend(bbox_conditions)
                else:
                    final_filter = {"$and": [final_filter] + bbox_conditions}
            else:
                final_filter = {"$and": bbox_conditions}

        # 1. Get initial results from Vector Store
        # Fetch more if sorting or geo-filtering to allow for post-processing
        fetch_k = k * 5 if (sort_by or radius_km) else k * 3

        # If query is empty, we can't use similarity_search efficiently with relevance.
        # But we rely on 'search' method fallback or behavior.
        # If 'search' handles empty query by returning cached docs or random, we use that.
        vector_results = self.search(query, k=fetch_k, filter=final_filter)

        if not vector_results:
            return []

        # Post-filter for precise Geo Radius (Bounding box is square, we want circle)
        if lat is not None and lon is not None and radius_km is not None:
            filtered_results = []
            for doc, score in vector_results:
                d_lat = doc.metadata.get("lat")
                d_lon = doc.metadata.get("lon")
                if d_lat is not None and d_lon is not None:
                    dist = self._haversine(lat, lon, float(d_lat), float(d_lon))
                    if dist <= radius_km:
                        filtered_results.append((doc, score))
            vector_results = filtered_results

        # Post-filter for polygon-based geo-search
        if polygon is not None and len(polygon) >= 3:
            filtered_results = []
            for doc, score in vector_results:
                d_lat = doc.metadata.get("lat")
                d_lon = doc.metadata.get("lon")
                if d_lat is not None and d_lon is not None:
                    if self._point_in_polygon(float(d_lat), float(d_lon), polygon):
                        filtered_results.append((doc, score))
            vector_results = filtered_results

        if not vector_results:
            return []

        if not query.strip():
            # If no query, we just return results (sorted if needed)
            # Assign dummy score if needed, or keep vector score (which might be meaningless)
            combined_results = vector_results
        else:
            # 2. Rescore with BM25 or Simple Term Overlap
            # ... (BM25 logic) ...
            docs = [doc for doc, _ in vector_results]
            texts = [doc.page_content for doc in docs]
            tokenized_query = query.lower().split()

            bm25_scores = []
            if BM25Okapi:
                try:
                    tokenized_corpus = [doc.lower().split() for doc in texts]
                    bm25 = BM25Okapi(tokenized_corpus)
                    bm25_scores = bm25.get_scores(tokenized_query)
                    # Normalize BM25 scores (min-max)
                    if len(bm25_scores) > 0:
                        min_s = min(bm25_scores)
                        max_s = max(bm25_scores)
                        if max_s > min_s:
                            bm25_scores = [(s - min_s) / (max_s - min_s) for s in bm25_scores]
                        else:
                            bm25_scores = [1.0 if max_s > 0 else 0.0 for _ in bm25_scores]
                except Exception as e:
                    logger.warning("BM25 scoring failed: %s", sanitize_for_log(e))
                    bm25_scores = [0.0] * len(docs)
            else:
                # Fallback: Simple Term Frequency
                for text in texts:
                    txt_lower = text.lower()
                    score = sum(1 for term in tokenized_query if term in txt_lower)
                    bm25_scores.append(float(score))
                # Normalize
                max_s = max(bm25_scores) if bm25_scores else 0
                if max_s > 0:
                    bm25_scores = [s / max_s for s in bm25_scores]

            # 3. Combine Scores
            combined_results = []
            for i, (doc, vec_score) in enumerate(vector_results):
                sim_score = 1.0 / (1.0 + vec_score)
                keyword_score = bm25_scores[i] if i < len(bm25_scores) else 0.0
                final_score = (effective_alpha * sim_score) + (
                    (1 - effective_alpha) * keyword_score
                )
                combined_results.append((doc, final_score))

        # 4. Sort and return top K
        if sort_by and sort_by != "relevance":
            reverse = sort_order == "desc"

            def get_sort_val(item: tuple[Document, float]) -> float:
                doc = item[0]
                val = doc.metadata.get(sort_by)
                # Handle None/Missing: put at end
                if val is None:
                    # None values are always placed last
                    return float("-inf") if reverse else float("inf")
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return float("-inf") if reverse else float("inf")

            combined_results.sort(key=get_sort_val, reverse=reverse)
        else:
            combined_results.sort(key=lambda x: x[1], reverse=True)

        return combined_results[:k]

    def search_by_metadata(
        self,
        city: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rooms: Optional[float] = None,
        has_parking: Optional[bool] = None,
        k: int = 5,
    ) -> List[Document]:
        """
        Search properties by metadata filters.

        Args:
            city: Filter by city
            min_price: Minimum price
            max_price: Maximum price
            min_rooms: Minimum number of rooms
            has_parking: Filter by parking availability
            k: Number of results

        Returns:
            List of matching documents
        """
        # If vector store is missing, use fallback cache
        vector_store = self._get_vector_store()
        if vector_store is None:
            with self._cache_lock:
                docs = list(self._documents)
            filtered: List[Document] = []
            for doc in docs:
                md = doc.metadata
                if city and md.get("city") != city:
                    continue
                if has_parking is not None and md.get("has_parking") != has_parking:
                    continue
                raw_price = md.get("price")
                try:
                    price_val = float(raw_price) if raw_price is not None else None
                except (TypeError, ValueError):
                    price_val = None
                if price_val is None:
                    continue
                if min_price is not None and price_val < min_price:
                    continue
                if max_price is not None and price_val > max_price:
                    continue
                raw_rooms = md.get("rooms")
                try:
                    rooms_val = float(raw_rooms) if raw_rooms is not None else None
                except (TypeError, ValueError):
                    rooms_val = None
                if rooms_val is None:
                    continue
                if min_rooms is not None and rooms_val < min_rooms:
                    continue
                filtered.append(doc)
                if len(filtered) >= k:
                    break
            return filtered

        filter_dict: Dict[str, Any] = {}

        if city:
            filter_dict["city"] = city

        if has_parking is not None:
            filter_dict["has_parking"] = has_parking

        # Note: ChromaDB has limited support for range queries
        # For complex filtering, retrieve more results and filter in Python
        with self._vector_lock:
            results = vector_store.similarity_search(
                query="",  # Empty query for metadata-only search
                k=k * 5,  # Retrieve more for filtering
                filter=filter_dict if filter_dict else None,
            )

        # Apply additional filters
        filtered = []
        for doc in results:
            metadata = doc.metadata

            # Price filters
            if min_price is not None and metadata.get("price", 0) < min_price:
                continue
            if max_price is not None and metadata.get("price", float("inf")) > max_price:
                continue

            # Rooms filter
            if min_rooms is not None and metadata.get("rooms", 0) < min_rooms:
                continue

            filtered.append(doc)

            if len(filtered) >= k:
                break

        return filtered

    def get_retriever(
        self, search_type: str = "mmr", k: int = 5, fetch_k: int = 20, **kwargs: Any
    ) -> BaseRetriever:
        """
        Get a LangChain retriever for this vector store.

        Args:
            search_type: Type of search ('similarity', 'mmr', 'similarity_score_threshold')
            k: Number of documents to return
            fetch_k: Number of documents to fetch for MMR
            **kwargs: Additional retriever parameters

        Returns:
            LangChain retriever instance
        """
        stats = self.get_stats()
        # Use DB retriever only if we actually have documents in the DB
        db_count = stats.get("db_document_count", 0)

        vector_store = self._get_vector_store()
        if vector_store is not None and db_count > 0:
            return vector_store.as_retriever(
                search_type=search_type, search_kwargs={"k": k, "fetch_k": fetch_k, **kwargs}
            )
        else:

            class FallbackRetriever(BaseRetriever):
                docs: List[Document]
                kk: int

                class Config:
                    arbitrary_types_allowed = True

                def _get_relevant_documents(
                    self,
                    query: str,
                    *,
                    run_manager: Optional[CallbackManagerForRetrieverRun] = None,
                ) -> List[Document]:
                    q = [t for t in query.lower().split() if t]
                    scored: List[tuple[Document, float]] = []
                    for d in self.docs:
                        txt = d.page_content.lower()
                        s = float(sum(1 for t in q if t in txt))
                        if s > 0:
                            scored.append((d, s))
                    scored.sort(key=lambda x: x[1], reverse=True)
                    return [d for d, _s in scored[: self.kk]]

            with self._cache_lock:
                docs = list(self._documents)
            return FallbackRetriever(docs=docs, kk=k)

    def clear(self) -> None:
        """Clear all documents from the vector store."""
        try:
            vector_store = self._get_vector_store()
            if vector_store is not None:
                with self._vector_lock:
                    vector_store.delete_collection()
                    new_store = self._initialize_vector_store()
                    self.vector_store = new_store
                    self._vector_store_local.store = new_store
            with self._cache_lock:
                self._documents = []
                self._doc_ids = set()
            logger.info("Vector store cleared")

        except Exception as e:
            logger.error("Error clearing vector store: %s", sanitize_for_log(e))
            with self._cache_lock:
                self._documents = []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with store statistics
        """
        try:
            db_count = 0
            cache_count = 0

            with self._cache_lock:
                cache_count = len(self._documents)

            vector_store = self._get_vector_store()
            if vector_store is not None:
                with self._vector_lock:
                    try:
                        db_count = vector_store._collection.count()
                    except Exception:
                        pass

            count = db_count if db_count > 0 else cache_count

            emb_cls = type(self.embeddings).__name__ if self.embeddings is not None else "None"
            if "OpenAIEmbeddings" in emb_cls:
                emb_provider = "openai"
                emb_model = getattr(self.embeddings, "model", "openai")
            elif "FastEmbedEmbeddings" in emb_cls:
                emb_provider = "fastembed"
                emb_model = getattr(self.embeddings, "model_name", "BAAI/bge-small-en-v1.5")
            else:
                emb_provider = "none"
                emb_model = "none"

            return {
                "total_documents": count,
                "db_document_count": db_count,
                "cache_document_count": cache_count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
                "embedding_model": emb_model,
                "embedding_provider": emb_provider,
            }
        except Exception as e:
            return {"error": str(e), "total_documents": len(self._documents)}

    def delete_by_source(self, source_url: str) -> None:
        """
        Delete all properties from a specific source.

        Args:
            source_url: Source URL to filter by
        """
        try:
            vector_store = self._get_vector_store()
            if vector_store is None:
                return
            with self._vector_lock:
                vector_store.delete(filter={"source_url": source_url})
            logger.info("Deleted properties from source: %s", sanitize_for_log(source_url))

        except Exception as e:
            logger.error("Error deleting by source: %s", sanitize_for_log(e))

    def delete_by_source_type(self, source_type: str) -> None:
        """
        Delete all properties from a specific source type.

        Args:
            source_type: Source type to filter by (csv, excel, url, portal)
        """
        try:
            vector_store = self._get_vector_store()
            if vector_store is None:
                return
            with self._vector_lock:
                vector_store.delete(filter={"source_platform": source_type})
            logger.info("Deleted properties from source_type: %s", sanitize_for_log(source_type))

        except Exception as e:
            logger.error("Error deleting by source_type: %s", sanitize_for_log(e))

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<ChromaPropertyStore: {stats.get('total_documents', 0)} documents, "
            f"collection='{self.collection_name}'>"
        )


def get_vector_store(
    persist_directory: Optional[str] = None,
    collection_name: str = "properties",
    embedding_model: Optional[str] = None,
) -> ChromaPropertyStore:
    """
    Get cached vector store instance.

    Args:
        persist_directory: Directory for persistent storage
        collection_name: Collection name
        embedding_model: Embedding model identifier

    Returns:
        ChromaPropertyStore instance
    """
    return ChromaPropertyStore(
        persist_directory=persist_directory,
        collection_name=collection_name,
        embedding_model=embedding_model or settings.embedding_model,
    )
