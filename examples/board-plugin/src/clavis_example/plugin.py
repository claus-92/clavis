import json
from importlib.resources import files

from pydantic import BaseModel

from clavis.clients.registry import ClientRegistry
from clavis.plugins import BoardPlugin
from clavis.schemas import BoardMetadata, ParameterDefinitions
from clavis_example.board import ExampleBoard


class ExampleConfig(BaseModel):
    board_id: str
    board_type: str = "example"
    name: str


def create_board(config: BaseModel, _: ClientRegistry) -> ExampleBoard:
    validated = ExampleConfig.model_validate(config.model_dump())
    metadata = BoardMetadata(
        board_id=validated.board_id,
        name=validated.name,
        asic="unknown",
        fpga="unknown",
        firmware_version="unknown",
        board_type="example",
    )
    return ExampleBoard(metadata)


def load_parameters() -> ParameterDefinitions:
    path = files("clavis_example") / "parameter_definitions" / "example.json"
    return ParameterDefinitions.model_validate(json.loads(path.read_text(encoding="utf-8")))


def plugin() -> BoardPlugin:
    return BoardPlugin(
        board_type="example",
        display_name="Example board",
        config_model=ExampleConfig,
        create_board=create_board,
        load_parameters=load_parameters,
    )
