import os

from fastapi import FastAPI, HTTPException

from .devtools_models import IngestRequest, IngestResult
from .infrai_vector import InfraiError, InfraiVectorClient
from .ingest_pipeline import ingest_records

app = FastAPI(title="Developer-tools vector ingest")


@app.post("/ingest", response_model=IngestResult)
def ingest(request: IngestRequest) -> IngestResult:
    try:
        client = InfraiVectorClient()
        collection = os.environ.get("INFRAI_COLLECTION", "developer-tool-events")
        return ingest_records(request, client, collection)
    except InfraiError as error:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(
            status_code=status,
            detail={"code": error.code, "error": error.detail},
        ) from error


def run() -> None:
    import uvicorn

    uvicorn.run("devtools_ingest.ingest_service:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
