from pydantic import BaseModel
from typing import Annotated


class BrokerWithoutID(BaseModel):
    """Broker instance without id"""
    name: Annotated[str, "Broker name"]


class Broker(BrokerWithoutID):
    """Broker instance with ID"""
    id: Annotated[int, "Broker ID"]


class Brokers(BaseModel):
    """List of brokers"""
    brokers: Annotated[list[Broker], "List of broker instances"]