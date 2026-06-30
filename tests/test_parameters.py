import pytest

from clavis.core.errors import InvalidParameterError
from clavis.parameters.loader import load_parameter_definitions
from clavis.parameters.validation import validate_options


def test_parameter_definition_json_can_be_loaded() -> None:
    definitions = load_parameter_definitions("samidare")
    assert definitions.channelParameters[0].name == "power"


def test_invalid_parameter_values_are_rejected() -> None:
    definitions = load_parameter_definitions("samidare")
    with pytest.raises(InvalidParameterError):
        validate_options({"gain": 3}, definitions.channelParameters)
