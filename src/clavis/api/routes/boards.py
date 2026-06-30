from typing import Any

from fastapi import APIRouter, Request

from clavis.core.service import ClavisService
from clavis.schemas.board import BoardMetadata, BoardStatus
from clavis.schemas.parameters import ParameterDefinitions

router = APIRouter(prefix="/boards")


def service(request: Request) -> ClavisService:
    return request.app.state.service


@router.get("", response_model=list[BoardMetadata])
def list_boards(request: Request) -> list[BoardMetadata]:
    return service(request).list_boards()


@router.post("/discover", response_model=list[BoardMetadata])
def discover_boards(request: Request) -> list[BoardMetadata]:
    return service(request).discover_boards()


@router.get("/{board_id}", response_model=BoardMetadata)
def get_board(board_id: str, request: Request) -> BoardMetadata:
    return service(request).get_board(board_id)


@router.get("/{board_id}/status", response_model=BoardStatus)
def get_board_status(board_id: str, request: Request) -> BoardStatus:
    return service(request).get_board_status(board_id)


@router.get("/{board_id}/parameters", response_model=ParameterDefinitions)
def get_board_parameters(board_id: str, request: Request) -> ParameterDefinitions:
    return service(request).get_board_parameters(board_id)


@router.post("/{board_id}/connect", response_model=BoardStatus)
def connect_board(board_id: str, request: Request) -> BoardStatus:
    return service(request).connect_board(board_id)


@router.post("/{board_id}/disconnect", response_model=BoardStatus)
def disconnect_board(board_id: str, request: Request) -> BoardStatus:
    return service(request).disconnect_board(board_id)


@router.post("/{board_id}/power/on", response_model=BoardStatus)
def power_on(board_id: str, request: Request) -> BoardStatus:
    return service(request).power_on(board_id)


@router.post("/{board_id}/power/off", response_model=BoardStatus)
def power_off(board_id: str, request: Request) -> BoardStatus:
    return service(request).power_off(board_id)


@router.post("/{board_id}/global", response_model=BoardStatus)
def set_global(board_id: str, options: dict[str, Any], request: Request) -> BoardStatus:
    return service(request).set_global(board_id, options)


@router.post("/{board_id}/groups/{group_id}", response_model=BoardStatus)
def set_group(board_id: str, group_id: str, options: dict[str, Any], request: Request) -> BoardStatus:
    return service(request).set_group(board_id, group_id, options)


@router.post("/{board_id}/channels/{channel_id}", response_model=BoardStatus)
def set_channel(board_id: str, channel_id: str, options: dict[str, Any], request: Request) -> BoardStatus:
    return service(request).set_channel(board_id, channel_id, options)
