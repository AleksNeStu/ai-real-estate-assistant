"""Favorites API endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from data.schemas import normalize_property_metadata
from db.database import get_db
from db.models import User
from db.repositories import CollectionRepository, FavoriteRepository
from db.schemas import (
    FavoriteCheckResponse,
    FavoriteCreate,
    FavoriteListResponse,
    FavoriteResponse,
    FavoriteUpdate,
    FavoriteWithPropertyResponse,
)
from vector_store.chroma_store import ChromaPropertyStore

router = APIRouter(prefix="/favorites", tags=["Favorites"])


def _get_vector_store(request: Request) -> Optional[ChromaPropertyStore]:
    """Get vector store from app state."""
    return getattr(request.app.state, "vector_store", None)


def _document_to_property_dict(doc: Any) -> dict[str, Any]:
    """Convert a ChromaDB Document to a property dictionary."""
    metadata = normalize_property_metadata(doc.metadata or {})
    return {
        "id": metadata.get("id"),
        "title": metadata.get("title"),
        "city": metadata.get("city"),
        "country": metadata.get("country"),
        "price": metadata.get("price"),
        "rooms": metadata.get("rooms"),
        "bathrooms": metadata.get("bathrooms"),
        "area_sqm": metadata.get("area_sqm"),
        "property_type": metadata.get("property_type"),
        "listing_type": metadata.get("listing_type"),
        "latitude": metadata.get("latitude"),
        "longitude": metadata.get("longitude"),
        "images": metadata.get("images", []),
        "description": doc.page_content,
    }


@router.post(
    "",
    response_model=FavoriteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a property to favorites",
    description="Add a property to the user's favorites.",
)
async def add_favorite(
    request: Request,
    body: FavoriteCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FavoriteResponse:
    """Add a property to favorites."""
    repo = FavoriteRepository(session)
    collection_repo = CollectionRepository(session)

    # Check if already favorited
    existing = await repo.get_by_property(user.id, body.property_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Property already in favorites",
        )

    # Validate collection if provided
    if body.collection_id:
        collection = await collection_repo.get_by_id(body.collection_id, user.id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found",
            )

    favorite = await repo.create(
        user_id=user.id,
        property_id=body.property_id,
        collection_id=body.collection_id,
        notes=body.notes,
    )

    return FavoriteResponse.model_validate(favorite)


@router.get(
    "",
    response_model=FavoriteListResponse,
    summary="List user's favorites",
    description="Get all favorited properties for the current user with full property data.",
)
async def list_favorites(
    request: Request,
    collection_id: Optional[str] = Query(default=None, description="Filter by collection"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FavoriteListResponse:
    """Get all favorites for the current user with property data from ChromaDB."""
    repo = FavoriteRepository(session)

    # Validate collection if provided
    if collection_id:
        collection_repo = CollectionRepository(session)
        collection = await collection_repo.get_by_id(collection_id, user.id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found",
            )

    favorites = await repo.get_by_user(
        user.id,
        collection_id=collection_id,
        limit=limit,
        offset=offset,
    )
    total = await repo.count_by_user(user.id, collection_id=collection_id)

    # Fetch property data from ChromaDB
    vector_store = _get_vector_store(request)
    property_ids = [f.property_id for f in favorites]

    properties_by_id: dict[str, dict[str, Any]] = {}
    unavailable_count = 0

    if vector_store and property_ids:
        try:
            documents = vector_store.get_properties_by_ids(property_ids)
            for doc in documents:
                prop_id = doc.metadata.get("id")
                if prop_id:
                    properties_by_id[prop_id] = _document_to_property_dict(doc)
        except Exception:
            # Log error but continue - properties might be unavailable
            pass

    # Build response
    items = []
    for favorite in favorites:
        property_data = properties_by_id.get(favorite.property_id)
        is_available = property_data is not None
        if not is_available:
            unavailable_count += 1

        items.append(
            FavoriteWithPropertyResponse(
                id=favorite.id,
                user_id=favorite.user_id,
                property_id=favorite.property_id,
                collection_id=favorite.collection_id,
                notes=favorite.notes,
                created_at=favorite.created_at,
                updated_at=favorite.updated_at,
                property=property_data,
                is_available=is_available,
            )
        )

    return FavoriteListResponse(
        items=items,
        total=total,
        unavailable_count=unavailable_count,
    )


@router.get(
    "/check/{property_id}",
    response_model=FavoriteCheckResponse,
    summary="Check if property is favorited",
    description="Quick check if a property is in the user's favorites.",
)
async def check_favorite(
    property_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FavoriteCheckResponse:
    """Check if a property is favorited by the user."""
    repo = FavoriteRepository(session)
    favorite = await repo.get_by_property(user.id, property_id)

    if favorite:
        return FavoriteCheckResponse(
            is_favorited=True,
            favorite_id=favorite.id,
            collection_id=favorite.collection_id,
            notes=favorite.notes,
        )
    return FavoriteCheckResponse(is_favorited=False)


@router.get(
    "/ids",
    response_model=list[str],
    summary="Get all favorited property IDs",
    description="Get a list of all property IDs favorited by the user. Useful for UI heart icons.",
)
async def get_favorite_property_ids(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get all property IDs favorited by the user."""
    repo = FavoriteRepository(session)
    return await repo.get_property_ids_by_user(user.id)


@router.get(
    "/{favorite_id}",
    response_model=FavoriteWithPropertyResponse,
    summary="Get a favorite with property data",
    description="Get a specific favorite by ID with full property data.",
)
async def get_favorite(
    request: Request,
    favorite_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FavoriteWithPropertyResponse:
    """Get a specific favorite with property data."""
    repo = FavoriteRepository(session)
    favorite = await repo.get_by_id(favorite_id, user.id)
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found",
        )

    # Fetch property data from ChromaDB
    vector_store = _get_vector_store(request)
    property_data = None
    is_available = False

    if vector_store:
        try:
            documents = vector_store.get_properties_by_ids([favorite.property_id])
            if documents:
                is_available = True
                property_data = _document_to_property_dict(documents[0])
        except Exception:
            pass

    return FavoriteWithPropertyResponse(
        id=favorite.id,
        user_id=favorite.user_id,
        property_id=favorite.property_id,
        collection_id=favorite.collection_id,
        notes=favorite.notes,
        created_at=favorite.created_at,
        updated_at=favorite.updated_at,
        property=property_data,
        is_available=is_available,
    )


@router.patch(
    "/{favorite_id}",
    response_model=FavoriteResponse,
    summary="Update a favorite",
    description="Update a favorite's notes or move to a different collection.",
)
async def update_favorite(
    favorite_id: str,
    body: FavoriteUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FavoriteResponse:
    """Update a favorite."""
    repo = FavoriteRepository(session)
    collection_repo = CollectionRepository(session)

    favorite = await repo.get_by_id(favorite_id, user.id)
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found",
        )

    # Validate collection if provided
    if body.collection_id is not None:
        collection = await collection_repo.get_by_id(body.collection_id, user.id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found",
            )

    update_data = body.model_dump(exclude_unset=True)
    favorite = await repo.update(favorite, **update_data)

    return FavoriteResponse.model_validate(favorite)


@router.delete(
    "/{favorite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a favorite",
    description="Remove a property from favorites.",
)
async def delete_favorite(
    favorite_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove a property from favorites."""
    repo = FavoriteRepository(session)
    favorite = await repo.get_by_id(favorite_id, user.id)
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found",
        )
    await repo.delete(favorite)


@router.delete(
    "/by-property/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove favorite by property ID",
    description="Remove a property from favorites by property ID.",
)
async def delete_favorite_by_property(
    property_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove a property from favorites by property ID."""
    repo = FavoriteRepository(session)
    deleted = await repo.delete_by_property(user.id, property_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not in favorites",
        )


@router.post(
    "/{favorite_id}/move/{collection_id}",
    response_model=FavoriteResponse,
    summary="Move favorite to collection",
    description="Move a favorite to a different collection.",
)
async def move_favorite_to_collection(
    favorite_id: str,
    collection_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FavoriteResponse:
    """Move a favorite to a different collection."""
    repo = FavoriteRepository(session)
    collection_repo = CollectionRepository(session)

    # Validate collection
    collection = await collection_repo.get_by_id(collection_id, user.id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found",
        )

    favorite = await repo.get_by_id(favorite_id, user.id)
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found",
        )

    favorite = await repo.update(favorite, collection_id=collection_id)
    return FavoriteResponse.model_validate(favorite)
