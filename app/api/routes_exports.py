from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user_hash
from app.db import get_session
from app.services.export_service import tableau_place_summary_csv

router = APIRouter()


@router.get("/exports/tableau/place-summary.csv")
def export_place_summary(
    user_id_hash: Annotated[str, Depends(current_user_hash)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    return Response(
        content=tableau_place_summary_csv(session, user_id_hash),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=place-summary.csv"},
    )
