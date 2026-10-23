import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import Money


class CompanyOut(BaseModel):
    id: uuid.UUID
    inn: str
    ogrn: str
    company_type: str
    company_type_label: str
    name: str
    okved: str
    industry: str
    registration_date: date
    region: str
    annual_revenue: Money | None
    employees_count: int


class DocumentOut(BaseModel):
    id: uuid.UUID
    kind: str
    kind_label: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    created_at: datetime
    download_url: str
