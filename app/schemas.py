from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SetupAdminRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=200)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class DocumentCreateRequest(BaseModel):
    # Keep document types data-driven. The database/config is the source of truth,
    # so adding a new official template does not require changing this schema.
    type_code: str = Field(min_length=2, max_length=8, pattern=r"^[A-Za-z0-9_-]+$")
    status: Literal["draft", "saved"] = "saved"
    fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type_code")
    @classmethod
    def normalize_type_code(cls, value: str) -> str:
        return value.strip().upper()


class DocumentUpdateRequest(BaseModel):
    status: Literal["draft", "saved"] = "saved"
    fields: dict[str, Any] = Field(default_factory=dict)


class DeleteRequest(BaseModel):
    confirmation: str


class UserCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=200)
    role: Literal["admin", "editor", "viewer"]


class UserUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    role: Literal["admin", "editor", "viewer"]
    is_active: bool = True
    password: str | None = Field(default=None, min_length=10, max_length=200)


class PagePermissionsUpdateRequest(BaseModel):
    page_keys: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("page_keys")
    @classmethod
    def normalize_page_keys(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            key = str(item).strip()
            if key and key not in cleaned:
                cleaned.append(key)
        return cleaned


class AttachmentNotesRequest(BaseModel):
    notes: str = Field(default="", max_length=1000)
    print_order: int = Field(default=0, ge=0, le=10000)


class PrintRequest(BaseModel):
    attachment_ids: list[int] = Field(default_factory=list)

    @field_validator("attachment_ids")
    @classmethod
    def unique_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class RestoreBackupRequest(BaseModel):
    confirmation: str


class LoanCreateRequest(BaseModel):
    borrower_name: str = Field(min_length=3, max_length=160)
    principal_amount: float = Field(gt=0, le=999999999999)
    months_total: int = Field(ge=1, le=600)
    minimum_payment: float = Field(gt=0, le=999999999999)

    @field_validator("borrower_name")
    @classmethod
    def normalize_borrower_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class LoanUpdateRequest(LoanCreateRequest):
    pass


class LoanPaymentCreateRequest(BaseModel):
    amount: float = Field(gt=0, le=999999999999)
    notes: str = Field(default="", max_length=1000)
