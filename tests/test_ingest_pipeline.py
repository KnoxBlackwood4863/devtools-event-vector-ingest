from datetime import datetime, timezone

from devtools_ingest.devtools_models import IngestRequest
from devtools_ingest.ingest_pipeline import ingest_records


class RecordingWriter:
    def __init__(self) -> None:
        self.vectors: list[dict[str, object]] = []
        self.batch_id = ""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0, 0.5] for text in texts]

    def create_collection(self, collection: str, dimension: int) -> object:
        assert collection == "ci-events-test"
        assert dimension == 3
        return {}

    def upsert(
        self, collection: str, vectors: list[dict[str, object]], batch_id: str
    ) -> object:
        self.vectors = vectors
        self.batch_id = batch_id
        return {}


def test_ingest_marks_release_blockers_and_rollback_recovery() -> None:
    at = datetime(2026, 9, 4, 8, 30, tzinfo=timezone.utc).isoformat()
    request = IngestRequest.model_validate(
        {
            "records": [
                {
                    "kind": "build",
                    "record_id": "build-1842",
                    "project": "cli",
                    "status": "failed",
                    "occurred_at": at,
                    "summary": "Linux package job failed.",
                    "log": "The package smoke test exited before publishing.",
                },
                {
                    "kind": "release",
                    "record_id": "release-92",
                    "project": "cli",
                    "action": "rollback",
                    "version": "3.8.1",
                    "occurred_at": at,
                    "summary": "Returned the stable channel to 3.8.0.",
                },
                {
                    "kind": "diagnostic",
                    "record_id": "diag-501",
                    "project": "cli",
                    "severity": "warning",
                    "code": "DEPRECATED_FLAG",
                    "occurred_at": at,
                    "summary": "A legacy flag was used by one job.",
                },
            ]
        }
    )
    writer = RecordingWriter()

    result = ingest_records(request, writer, "ci-events-test")

    attentions = [vector["metadata"]["attention"] for vector in writer.vectors]  # type: ignore[index]
    assert attentions == ["release_blocker", "recovery", "reference"]
    assert result.release_blockers == 1
    assert result.recovery_items == 1
    assert len(writer.batch_id) == 24
