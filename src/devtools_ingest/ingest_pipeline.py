from hashlib import sha256
from typing import Any

from .devtools_chunker import DocumentChunk, chunk_record
from .devtools_models import IngestRequest, IngestResult


def ingest_records(
    request: IngestRequest,
    writer: Any,
    collection: str,
) -> IngestResult:
    chunks: list[DocumentChunk] = [
        chunk for record in request.records for chunk in chunk_record(record)
    ]
    embeddings = writer.embed([chunk.text for chunk in chunks])
    if len(embeddings) != len(chunks) or not embeddings:
        raise ValueError("embedding response does not match the chunk batch")

    writer.create_collection(collection, len(embeddings[0]))
    vectors: list[dict[str, object]] = [
        {
            "id": chunk.id,
            "embedding": embedding,
            "metadata": chunk.metadata,
        }
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]
    batch_material = "|".join(chunk.id for chunk in chunks)
    batch_id = sha256(batch_material.encode()).hexdigest()[:24]
    writer.upsert(collection, vectors, batch_id)

    return IngestResult(
        collection=collection,
        records=len(request.records),
        chunks=len(chunks),
        release_blockers=sum(
            chunk.metadata["attention"] == "release_blocker" for chunk in chunks
        ),
        recovery_items=sum(chunk.metadata["attention"] == "recovery" for chunk in chunks),
    )
