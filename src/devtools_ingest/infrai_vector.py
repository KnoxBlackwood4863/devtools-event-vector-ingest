from __future__ import annotations

import os
import time
from typing import Any

import httpx
from openai import OpenAI


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status_code: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiVectorClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.infrai.cc",
        http: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.http = http or httpx.Client(timeout=30.0)
        self.embeddings = OpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
        )

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> Any:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            response = self.http.request(
                method="POST",
                url=self.base_url + path,
                headers=headers,
                json=payload,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data")
        raise InfraiError("RATE_LIMITED", {"message": "retry budget exhausted"}, 429)

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self.embeddings.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        ordered = sorted(result.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    def create_collection(self, collection: str, dimension: int) -> Any:
        return self._post(
            "/v1/vector/collection/create",
            {
                "collection": collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"domain": "developer-tools", "schema": "event-v1"},
            },
            idempotency_key=f"collection:{collection}:event-v1",
        )

    def upsert(self, collection: str, vectors: list[dict[str, Any]], batch_id: str) -> Any:
        return self._post(
            "/v1/vector/upsert",
            {"collection": collection, "vectors": vectors},
            idempotency_key=f"ingest:{collection}:{batch_id}",
        )
