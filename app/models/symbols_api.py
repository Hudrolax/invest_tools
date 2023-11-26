from pydantic import BaseModel
from typing import Annotated


class SymbolWithoutID(BaseModel):
    """A symbol instance without id"""
    name: Annotated[str, "Symbol name"]
    broker_id: Annotated[int, "Broker ID"]


class Symbol(SymbolWithoutID):
    """A symbol instance with ID"""
    id: Annotated[int, "Symbol ID"]


class Symbols(BaseModel):
    """List of symbols"""
    symbols: Annotated[list[Symbol], "List of symbol instances"]