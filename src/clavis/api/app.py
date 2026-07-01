from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from clavis.core.errors import ClavisError
from clavis.core.service import ClavisService
from clavis.schemas import BoardConfig, BoardMetadata, BoardStatus, BoardTypeInfo, ParameterDefinitions, StatusResponse


api_router = APIRouter(prefix="/api")


def service(request: Request) -> ClavisService:
    return request.app.state.service


@api_router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return StatusResponse(status="ok", service="clavisd")


@api_router.get("/boards", response_model=list[BoardMetadata])
def list_boards(request: Request) -> list[BoardMetadata]:
    return service(request).list_boards()


@api_router.get("/board-types", response_model=list[BoardTypeInfo])
def list_board_types(request: Request) -> list[BoardTypeInfo]:
    return service(request).list_board_types()


@api_router.post("/boards", response_model=BoardMetadata)
def create_board(config: BoardConfig, request: Request) -> BoardMetadata:
    return service(request).create_board(config)


@api_router.post("/boards/discover", response_model=list[BoardMetadata])
def discover_boards(request: Request) -> list[BoardMetadata]:
    return service(request).discover_boards()


@api_router.get("/boards/{board_id}", response_model=BoardMetadata)
def get_board(board_id: str, request: Request) -> BoardMetadata:
    return service(request).get_board(board_id)


@api_router.get("/boards/{board_id}/config", response_model=BoardConfig)
def get_board_config(board_id: str, request: Request) -> BoardConfig:
    return service(request).get_board_config(board_id)


@api_router.delete("/boards/{board_id}", status_code=204)
def delete_board(board_id: str, request: Request) -> None:
    service(request).delete_board(board_id)


@api_router.get("/boards/{board_id}/status", response_model=BoardStatus)
def get_board_status(board_id: str, request: Request) -> BoardStatus:
    return service(request).get_board_status(board_id)


@api_router.get("/boards/{board_id}/parameters", response_model=ParameterDefinitions)
def get_board_parameters(board_id: str, request: Request) -> ParameterDefinitions:
    return service(request).get_board_parameters(board_id)


@api_router.post("/boards/{board_id}/connect", response_model=BoardStatus)
def connect_board(board_id: str, request: Request) -> BoardStatus:
    return service(request).connect_board(board_id)


@api_router.post("/boards/{board_id}/disconnect", response_model=BoardStatus)
def disconnect_board(board_id: str, request: Request) -> BoardStatus:
    return service(request).disconnect_board(board_id)


@api_router.post("/boards/{board_id}/power/on", response_model=BoardStatus)
def power_on(board_id: str, request: Request) -> BoardStatus:
    return service(request).power_on(board_id)


@api_router.post("/boards/{board_id}/power/off", response_model=BoardStatus)
def power_off(board_id: str, request: Request) -> BoardStatus:
    return service(request).power_off(board_id)


@api_router.post("/boards/{board_id}/global", response_model=BoardStatus)
def set_global(board_id: str, options: dict[str, Any], request: Request) -> BoardStatus:
    return service(request).set_global(board_id, options)


@api_router.post("/boards/{board_id}/groups/{group_id}", response_model=BoardStatus)
def set_group(board_id: str, group_id: str, options: dict[str, Any], request: Request) -> BoardStatus:
    return service(request).set_group(board_id, group_id, options)


@api_router.post("/boards/{board_id}/channels/{channel_id}", response_model=BoardStatus)
def set_channel(board_id: str, channel_id: str, options: dict[str, Any], request: Request) -> BoardStatus:
    return service(request).set_channel(board_id, channel_id, options)


def create_app() -> FastAPI:
    app = FastAPI(title="clavis")
    app.state.service = ClavisService()
    app.include_router(api_router)

    @app.exception_handler(ClavisError)
    async def clavis_error_handler(_: Request, exc: ClavisError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    return app


app = create_app()
