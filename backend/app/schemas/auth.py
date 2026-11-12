from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class _EmailNormalizationMixin(BaseModel):
    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def normalize_email(cls, value: object) -> object:
        # Trim + lowercase before format validation so storage is canonical.
        return value.strip().lower() if isinstance(value, str) else value


class RegisterIn(_EmailNormalizationMixin):
    email: EmailStr
    # 8 chars is the policy minimum; 128 caps huge-input abuse.
    password: str = Field(min_length=8, max_length=128)


class LoginIn(_EmailNormalizationMixin):
    email: EmailStr
    # No min_length: any wrong password must reach verification and return the
    # same generic 401 instead of a validation error.
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
