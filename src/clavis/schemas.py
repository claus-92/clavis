from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BoardMetadata(BaseModel):
    board_id: str
    name: str
    asic: str
    fpga: str
    firmware_version: str
    board_type: str = "unknown"


class BoardStatus(BaseModel):
    board_id: str
    connected: bool
    powered: bool
    acquiring: bool = False
    status_fresh: bool = True
    global_options: dict[str, Any] = Field(default_factory=dict)
    group_options: dict[str, dict[str, Any]] = Field(default_factory=dict)
    channel_options: dict[str, dict[str, Any]] = Field(default_factory=dict)


class BoardConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    board_id: str
    board_type: str
    name: str
    asic: str = "unknown"
    fpga: str = "unknown"
    firmware_version: str = "unknown"
    transport: dict[str, Any] = Field(default_factory=dict)
    client: dict[str, Any] = Field(default_factory=dict)

class BoardTypeInfo(BaseModel):
    board_type: str
    display_name: str
    config_schema: dict[str, Any]


class ParameterDefinition(BaseModel):
    name: str
    type: str
    defaultValue: Any
    options: list[Any]
    description: str
    minimum: int | float | None = None
    maximum: int | float | None = None


class ParameterDefinitions(BaseModel):
    generalParameters: list[ParameterDefinition]
    channelParameters: list[ParameterDefinition]
    groupParameters: list[ParameterDefinition]


class BoardParameters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    global_: dict[str, Any] = Field(default_factory=dict, alias="global")
    groups: dict[str, dict[str, Any]] = Field(default_factory=dict)
    channels: dict[str, dict[str, Any]] = Field(default_factory=dict)

class BoardConfigEntry(BaseModel):
    config: BoardConfig
    parameters: BoardParameters = Field(default_factory=BoardParameters)


class SystemConfig(BaseModel):
    boards: list[BoardConfigEntry]


class StatusResponse(BaseModel):
    status: str
    service: str
