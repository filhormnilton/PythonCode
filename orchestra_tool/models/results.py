"""
Modelos de dados (dataclasses) que representam os resultados das operações.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ClonedKey:
    business_key: str
    new_business_key: Optional[str]
    internal_id: Optional[str]
    sap_item: str
    voltage_code: Any
    package_code: Any
    rated_power: Any
    frame_size: Any
    excitation_type: Any
    im_code: Any
    flange: Any
    disc: Any
    tbox_raw_material: Any
    avr_model: Any
    avr_installation: Any
    status: Any

    @classmethod
    def columns(cls) -> list[str]:
        return [
            "Business Key", "New Business Key", "Internal Id", "SAP item",
            "Voltage Code", "Package Code", "Rated Power", "Frame",
            "Excitation type", "ImCode", "Flange", "Disc",
            "Tbox raw material", "AVR model", "AVR installation", "Status",
        ]

    def to_row(self) -> tuple:
        return (
            self.business_key, self.new_business_key, self.internal_id,
            self.sap_item, self.voltage_code, self.package_code,
            self.rated_power, self.frame_size, self.excitation_type,
            self.im_code, self.flange, self.disc, self.tbox_raw_material,
            self.avr_model, self.avr_installation, self.status,
        )


@dataclass
class UpdateResult:
    business_key: str
    internal_id: str
    sap_item: str
    status: Any

    @classmethod
    def columns(cls) -> list[str]:
        return ["Business Key", "Internal Id", "SAP item", "Status"]

    def to_row(self) -> tuple:
        return (self.business_key, self.internal_id, self.sap_item, self.status)


@dataclass
class DifferenceConf:
    business_key: str
    internal_id: str
    sap_item: str
    attribute: str
    value_s: Any
    value_t: Any

    @classmethod
    def columns(cls) -> list[str]:
        return ["Business Key", "Internal Id", "SAP item", "Atribute", "Value s", "Value t"]

    def to_row(self) -> tuple:
        return (
            self.business_key, self.internal_id, self.sap_item,
            self.attribute, self.value_s, self.value_t,
        )


@dataclass
class DifferenceItem(DifferenceConf):
    pass


@dataclass
class BrokenConstraint:
    business_key: str
    internal_id: str
    sap_item: str
    name: str
    behavior: str
    layer: str

    @classmethod
    def columns(cls) -> list[str]:
        return [
            "Business Key", "Internal Id", "SAP item",
            "Constraint Name", "Constraint Behavior", "Constraint Internal Default Layer",
        ]

    def to_row(self) -> tuple:
        return (
            self.business_key, self.internal_id, self.sap_item,
            self.name, self.behavior, self.layer,
        )


@dataclass
class LinkedFert:
    new_business_key: str
    internal_id: str
    sap_item: str
    linked: str

    @classmethod
    def columns(cls) -> list[str]:
        return ["New Business Key", "Internal Id", "SAP Item", "Linked"]

    def to_row(self) -> tuple:
        return (self.new_business_key, self.internal_id, self.sap_item, self.linked)


@dataclass
class DuplicatedFert:
    internal_id: str
    record_id: str
    pccm_id: str
    new_business_key: str
    sap_item: str
    linked: str

    @classmethod
    def columns(cls) -> list[str]:
        return ["Internal ID", "Record ID", "ID", "New Business Key", "SAP Item", "Linked"]

    def to_row(self) -> tuple:
        return (
            self.internal_id, self.record_id, self.pccm_id,
            self.new_business_key, self.sap_item, self.linked,
        )


@dataclass
class OperationContext:
    cloned_keys: list[ClonedKey] = field(default_factory=list)
    updates: list[UpdateResult] = field(default_factory=list)
    differences_conf: list[DifferenceConf] = field(default_factory=list)
    differences_item: list[DifferenceItem] = field(default_factory=list)
    broken_constraints: list[BrokenConstraint] = field(default_factory=list)
    linked_ferts: list[LinkedFert] = field(default_factory=list)
    duplicated_ferts: list[DuplicatedFert] = field(default_factory=list)