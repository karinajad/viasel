import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

ROLES = ("oem", "distributor", "integrator", "supplier")
STATUSES = ("prospect", "approved", "preferred", "hold", "disqualified")
# a vendor you can't buy from shouldn't quietly appear in a bid dropdown
BIDDABLE = ("approved", "preferred", "prospect")


class VendorWrite(BaseModel):
    name: str
    code: str | None = None
    role: str = "supplier"
    oem_names: list[str] | None = None
    factory_country: str | None = None
    factory_location: str | None = None
    integration_location: str | None = None
    sub_supplier: str | None = None
    status: str = "approved"
    status_note: str | None = None
    notes: str | None = None


class VendorPatch(BaseModel):
    name: str | None = None
    code: str | None = None
    role: str | None = None
    oem_names: list[str] | None = None
    factory_country: str | None = None
    factory_location: str | None = None
    integration_location: str | None = None
    sub_supplier: str | None = None
    status: str | None = None
    status_note: str | None = None
    notes: str | None = None


class VendorContactWrite(BaseModel):
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None


class VendorContactRead(VendorContactWrite):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    code: str | None
    role: str
    oem_names: list | None
    factory_country: str | None
    factory_location: str | None
    integration_location: str | None
    sub_supplier: str | None
    status: str
    status_note: str | None
    notes: str | None
    created_at: datetime


class VendorDetail(VendorRead):
    contacts: list[VendorContactRead] = []
    bid_count: int = 0
    award_count: int = 0
