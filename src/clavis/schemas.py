from typing import Any

from pydantic import BaseModel


class BoardMetadata(BaseModel):
    board_id: str
    name: str
    asic: str
    fpga: str
    firmware_version: str


class BoardStatus(BaseModel):
    board_id: str
    connected: bool
    powered: bool
    global_options: dict[str, Any] = {}
    group_options: dict[str, dict[str, Any]] = {}
    channel_options: dict[str, dict[str, Any]] = {}


class ParameterDefinition(BaseModel):
    name: str
    type: str
    defaultValue: Any
    options: list[Any]
    description: str


class ParameterDefinitions(BaseModel):
    generalParameters: list[ParameterDefinition]
    channelParameters: list[ParameterDefinition]
    groupParameters: list[ParameterDefinition]


class StatusResponse(BaseModel):
    status: str
    service: str
