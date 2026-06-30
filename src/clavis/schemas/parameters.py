from typing import Any

from pydantic import BaseModel


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
