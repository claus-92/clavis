from typing import Any

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - Pydantic v1 compatibility
    ConfigDict = None  # type: ignore[assignment]


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
    global_options: dict[str, Any] = Field(default_factory=dict)
    group_options: dict[str, dict[str, Any]] = Field(default_factory=dict)
    channel_options: dict[str, dict[str, Any]] = Field(default_factory=dict)


class BoardConfig(BaseModel):
    if ConfigDict is not None:
        model_config = ConfigDict(extra="allow")

    board_id: str
    board_type: str
    name: str
    asic: str = "unknown"
    fpga: str = "unknown"
    firmware_version: str = "unknown"
    transport: dict[str, Any] = Field(default_factory=dict)
    client: dict[str, Any] = Field(default_factory=dict)

    if ConfigDict is None:
        class Config:
            extra = "allow"


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


class ParameterDefinitions(BaseModel):
    generalParameters: list[ParameterDefinition]
    channelParameters: list[ParameterDefinition]
    groupParameters: list[ParameterDefinition]


class BoardParameters(BaseModel):
    if ConfigDict is not None:
        model_config = ConfigDict(populate_by_name=True)

    global_: dict[str, Any] = Field(default_factory=dict, alias="global")
    groups: dict[str, dict[str, Any]] = Field(default_factory=dict)
    channels: dict[str, dict[str, Any]] = Field(default_factory=dict)

    if ConfigDict is None:

        class Config:
            allow_population_by_field_name = True


class BoardConfigEntry(BaseModel):
    config: BoardConfig
    parameters: BoardParameters = Field(default_factory=BoardParameters)


class SystemConfig(BaseModel):
    boards: list[BoardConfigEntry]


class StatusResponse(BaseModel):
    status: str
    service: str
