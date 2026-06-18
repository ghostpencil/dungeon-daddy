from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class ConsumeKitCharge(BaseModel):
    kind: Literal["consume_kit_charge"] = "consume_kit_charge"
    item_id: str
    reason: str


class ConsumeItem(BaseModel):
    kind: Literal["consume_item"] = "consume_item"
    item_id: str
    reason: str


class GiveItem(BaseModel):
    kind: Literal["give_item"] = "give_item"
    item_id: str
    to_actor_id: str


class TakeItem(BaseModel):
    kind: Literal["take_item"] = "take_item"
    item_id: str


class EquipItem(BaseModel):
    kind: Literal["equip_item"] = "equip_item"
    item_id: str


class UnequipItem(BaseModel):
    kind: Literal["unequip_item"] = "unequip_item"
    item_id: str


PlayerCommand = Annotated[
    Union[ConsumeKitCharge, ConsumeItem, GiveItem, TakeItem, EquipItem, UnequipItem],
    Field(discriminator="kind"),
]
