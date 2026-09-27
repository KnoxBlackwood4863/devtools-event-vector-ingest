from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from .devtools_models import BuildEvent, DeveloperRecord, Diagnostic, ReleaseOperation

Attention = Literal["reference", "release_blocker", "recovery"]


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    text: str
    metadata: dict[str, Any]


def attention_for(record: DeveloperRecord) -> Attention:
    if isinstance(record, BuildEvent) and record.status == "failed":
        return "release_blocker"
    if isinstance(record, Diagnostic) and record.severity == "error":
        return "release_blocker"
    if isinstance(record, ReleaseOperation) and record.action == "rollback":
        return "recovery"
    return "reference"


def record_text(record: DeveloperRecord) -> str:
    if isinstance(record, BuildEvent):
        tail = record.log
        heading = f"Build {record.status}: {record.project}"
    elif isinstance(record, ReleaseOperation):
        tail = record.notes
        heading = f"Release {record.action}: {record.project} {record.version}"
    else:
        tail = record.detail
        heading = f"Diagnostic {record.severity}: {record.code} in {record.project}"
    return "\n\n".join(part for part in (heading, record.summary, tail) if part.strip())


def split_text(text: str, max_chars: int = 700) -> list[str]:
    if max_chars < 80:
        raise ValueError("max_chars must be at least 80")
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    pieces: list[str] = []
    for paragraph in paragraphs:
        pieces.extend(
            paragraph[start : start + max_chars]
            for start in range(0, len(paragraph), max_chars)
        )

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = piece
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def chunk_record(record: DeveloperRecord, max_chars: int = 700) -> list[DocumentChunk]:
    attention = attention_for(record)
    occurred_at = record.occurred_at.isoformat()
    output: list[DocumentChunk] = []
    for index, text in enumerate(split_text(record_text(record), max_chars)):
        digest = sha256(f"{record.kind}:{record.record_id}:{index}".encode()).hexdigest()[:24]
        output.append(
            DocumentChunk(
                id=digest,
                text=text,
                metadata={
                    "record_id": record.record_id,
                    "project": record.project,
                    "kind": record.kind,
                    "attention": attention,
                    "occurred_at": occurred_at,
                    "chunk_index": index,
                    "text": text,
                },
            )
        )
    return output
