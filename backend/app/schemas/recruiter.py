import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.recruiter import RecruiterState


class RecruiterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(validation_alias="recruiter_id")
    email: str
    name: str = Field(validation_alias="full_name")
    account_state: RecruiterState
    granted_scopes: list[str]


class RecruiterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str
