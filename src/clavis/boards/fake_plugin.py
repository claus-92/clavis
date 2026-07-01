from typing import Any

from pydantic import BaseModel, Field

from clavis.boards.fake import FakeAcquisitionBoard
from clavis.clients.registry import ClientRegistry
from clavis.parameters.loader import load_parameter_definitions
from clavis.plugins import BoardPlugin
from clavis.schemas import BoardMetadata, ParameterDefinitions
from clavis.transport.fake import FakeTransport


class FakeBoardConfig(BaseModel):
    board_id: str
    board_type: str = "fake"
    name: str
    asic: str = "fake"
    fpga: str = "fake"
    firmware_version: str = "fake"
    transport: dict[str, Any] = Field(default_factory=dict)
    client: dict[str, Any] = Field(default_factory=dict)


def create_fake_board(config: BaseModel, _: ClientRegistry) -> FakeAcquisitionBoard:
    if isinstance(config, FakeBoardConfig):
        fake_config = config
    else:
        data = config.model_dump() if hasattr(config, "model_dump") else config.dict()
        fake_config = FakeBoardConfig.model_validate(data) if hasattr(FakeBoardConfig, "model_validate") else FakeBoardConfig.parse_obj(data)
    metadata = BoardMetadata(
        board_id=fake_config.board_id,
        name=fake_config.name,
        asic=fake_config.asic,
        fpga=fake_config.fpga,
        firmware_version=fake_config.firmware_version,
        board_type="fake",
    )
    return FakeAcquisitionBoard(metadata, FakeTransport())


def load_fake_parameters() -> ParameterDefinitions:
    return load_parameter_definitions("samidare")


def plugin() -> BoardPlugin:
    return BoardPlugin(
        board_type="fake",
        display_name="Fake Board",
        config_model=FakeBoardConfig,
        create_board=create_fake_board,
        load_parameters=load_fake_parameters,
    )
