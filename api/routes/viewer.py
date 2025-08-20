from typing import Dict

from fastapi import APIRouter, Depends, Response

from api.dependencies.security import verify_user_access
from api.services import viewer as viewer_service

router = APIRouter(
    prefix="/viewer",
    tags=["viewer"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{slide_id}.dzi")
async def get_dzi(
    slide_id: int,
    current_user: Dict = Depends(verify_user_access),
) -> Response:
    """
    Get DZI XML descriptor for a slide.
    Returns XML for OpenSeadragon viewer.
    Requires authentication and slide ownership.
    """
    # Get DZI XML from service
    xml_content = await viewer_service.create_dzi(
        slide_id=slide_id,
        user_id=current_user["id"]
    )
    
    # Return XML response with proper content type
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
        }
    )


@router.get("/{slide_id}_files/{level}/{col}_{row}.jpg")
async def get_tile(
    slide_id: int,
    level: int,
    col: int,
    row: int,
    current_user: Dict = Depends(verify_user_access),
) -> Response:
    """
    Get a specific tile for Deep Zoom viewing.
    Returns JPEG image data for the requested tile coordinates.
    Requires authentication and slide ownership.
    """
    # Get tile data from service
    tile_bytes = await viewer_service.get_tile(
        slide_id=slide_id,
        level=level,
        col=col,
        row=row,
        user_id=current_user["id"]
    )
    
    # Return JPEG response
    return Response(
        content=tile_bytes,
        media_type="image/jpeg"
    )
