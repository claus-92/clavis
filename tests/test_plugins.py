from clavis.boards.base import AcquisitionBoard
from clavis.clients.registry import ClientRegistry
from clavis.core.factory import BoardFactory
from clavis.plugins import BoardPluginRegistry
from clavis.schemas import BoardConfig
from tests.fake_plugin import plugin as fake_plugin


def test_factory_creates_board_through_registered_plugin() -> None:
    plugins = BoardPluginRegistry()
    plugins.register(fake_plugin())
    factory = BoardFactory(plugins, ClientRegistry())

    board = factory.create(BoardConfig(board_id="dev-003", board_type="fake", name="Fake"))

    assert isinstance(board, AcquisitionBoard)
    assert board.get_id() == "dev-003"


def test_board_config_allows_plugin_specific_fields() -> None:
    config = BoardConfig(board_id="samidare-001", board_type="samidare", name="SAMIDARE", host="192.0.2.1")

    data = config.model_dump()
    assert data["host"] == "192.0.2.1"
