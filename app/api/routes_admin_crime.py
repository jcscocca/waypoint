from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crime.seattle_socrata import SeattleSocrataClient
from app.db import get_session
from app.services.crime_ingestion_service import ingest_crime_incidents

MAX_SOCRATA_LIMIT = 5000
MAX_SOCRATA_OFFSET = 1_000_000

router = APIRouter()


def require_admin_ingest_token(
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    settings = get_settings()
    if not settings.admin_ingest_token or x_admin_token != settings.admin_ingest_token:
        raise HTTPException(status_code=403, detail="Admin token required")


@router.post(
    "/admin/crime/ingest/socrata",
    dependencies=[Depends(require_admin_ingest_token)],
)
def ingest_socrata(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=MAX_SOCRATA_LIMIT)] = MAX_SOCRATA_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_SOCRATA_OFFSET)] = 0,
) -> dict[str, int]:
    settings = get_settings()
    client = SeattleSocrataClient(
        base_url=settings.socrata_base_url,
        dataset_id=settings.socrata_dataset_id,
        app_token=settings.socrata_app_token,
    )
    incidents = client.fetch_page(limit=limit, offset=offset)
    return ingest_crime_incidents(session, incidents)
