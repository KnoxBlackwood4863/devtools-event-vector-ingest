from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class BuildEvent(BaseModel):
    kind: Literal["build"]
    record_id: str = Field(min_length=1, max_length=120)
    project: str = Field(min_length=1, max_length=120)
    status: Literal["started", "passed", "failed"]
    occurred_at: datetime
    summary: str = Field(min_length=1)
    log: str = ""


class ReleaseOperation(BaseModel):
    kind: Literal["release"]
    record_id: str = Field(min_length=1, max_length=120)
    project: str = Field(min_length=1, max_length=120)
    action: Literal["deploy", "promote", "rollback"]
    version: str = Field(min_length=1, max_length=80)
    occurred_at: datetime
    summary: str = Field(min_length=1)
    notes: str = ""


class Diagnostic(BaseModel):
    kind: Literal["diagnostic"]
    record_id: str = Field(min_length=1, max_length=120)
    project: str = Field(min_length=1, max_length=120)
    severity: Literal["info", "warning", "error"]
    code: str = Field(min_length=1, max_length=120)
    occurred_at: datetime
    summary: str = Field(min_length=1)
    detail: str = ""


DeveloperRecord = Annotated[
    Union[BuildEvent, ReleaseOperation, Diagnostic],
    Field(discriminator="kind"),
]


class IngestRequest(BaseModel):
    records: list[DeveloperRecord] = Field(min_length=1, max_length=100)


class IngestResult(BaseModel):
    collection: str
    records: int
    chunks: int
    release_blockers: int
    recovery_items: int
