from fastapi import APIRouter

from clavis.schemas.responses import StatusResponse

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return StatusResponse(status="ok", service="clavisd")
