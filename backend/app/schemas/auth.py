import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=64, examples=["client_good"])
    password: str = Field(min_length=1, max_length=128, examples=["client_good123"])


class CompanyShort(BaseModel):
    id: uuid.UUID
    name: str
    inn: str


class UserOut(BaseModel):
    id: uuid.UUID
    login: str
    full_name: str
    role: str  # client / employee
    role_label: str
    position: str | None
    position_label: str | None
    company: CompanyShort | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # секунд
    user: UserOut
