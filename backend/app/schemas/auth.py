import re
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class _EmailNormalizationMixin(BaseModel):
    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def normalize_email(cls, value: object) -> object:
        # Trim + lowercase before format validation so storage is canonical.
        return value.strip().lower() if isinstance(value, str) else value


class _FullNameMixin(BaseModel):
    @field_validator("full_name", mode="before", check_fields=False)
    @classmethod
    def normalize_full_name(cls, value: object) -> object:
        # Collapse runs of whitespace so " Ada  Lovelace " and "Ada Lovelace"
        # are stored identically.
        return " ".join(value.split()) if isinstance(value, str) else value


_INDIA_NATIONAL_PATTERN = re.compile(r"^[6-9]\d{9}$")


class _PhoneMixin(BaseModel):
    @field_validator("phone", mode="before", check_fields=False)
    @classmethod
    def normalize_phone(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value

        # Clients send the bare national number (or one with common separators);
        # the country code is chosen entirely by the server. Users may NOT
        # override it by typing +91… or +1… into the field.
        digits = re.sub(r"[\s().\-]", "", value)
        if not digits:
            return None
        if digits.startswith("+"):
            raise ValueError(
                "Enter your 10-digit mobile number without the country code; +91 is added automatically."
            )
        if not _INDIA_NATIONAL_PATTERN.fullmatch(digits):
            raise ValueError(
                "Enter your 10-digit Indian mobile number (starts 6, 7, 8 or 9)."
            )
        return f"+91{digits}"


class RegisterIn(_EmailNormalizationMixin, _FullNameMixin, _PhoneMixin):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    phone: str | None = None
    # 8 chars is the policy minimum; 128 caps huge-input abuse.
    password: str = Field(min_length=8, max_length=128)


class LoginIn(_EmailNormalizationMixin):
    email: EmailStr
    # No min_length: any wrong password must reach verification and return the
    # same generic 401 instead of a validation error.
    password: str = Field(min_length=1, max_length=128)


class UserUpdate(_FullNameMixin):
    """Only fields a user may edit themselves. Extras are rejected loudly."""

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=120)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountIn(BaseModel):
    # No min_length: a wrong password must reach verification and get the same
    # generic error, not a validation error.
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
