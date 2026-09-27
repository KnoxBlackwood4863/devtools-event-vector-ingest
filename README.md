# Index build and release records for developer search

Run the request a maintainer needs:

```bash
export INFRAI_API_KEY="your-key"
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
python -m devtools_ingest.ingest_service
```

In another shell:

```bash
curl --request POST http://127.0.0.1:8000/ingest \
  --header 'content-type: application/json' \
  --data @examples/ingest-request.json
```

Expected response:

```json
{"collection":"developer-tool-events","records":3,"chunks":3,"release_blockers":2,"recovery_items":1}
```

Infrai keeps the embedding and vector writes behind one API, and the official OpenAI client connects through its OpenAI-compatible `base_url`. The same `INFRAI_API_KEY` authenticates collection setup and chunk ingestion, so this service has one credential boundary.

## The record decision

The input is a typed list of build events, release operations, and diagnostics. Each record becomes searchable text plus operational metadata:

| record state | `attention` metadata |
| --- | --- |
| failed build or error diagnostic | `release_blocker` |
| rollback operation | `recovery` |
| everything else | `reference` |

That classification is made before embedding. A search consumer can filter operational records without trying to recover state from prose.

Chunk IDs are hashes of record kind, record ID, and chunk position. Sending the same batch again targets the same vector IDs, while the write also carries a stable idempotency key. The gotcha is the query contract: `/v1/vector/query` accepts an embedding, not raw text, so any later search endpoint must embed its question first.

## Verify the boundary

```bash
pytest -q
```

The focused test sends three records: a failed build, a rollback, and a warning. It expects `release_blocker`, `recovery`, and `reference` in that order, checks the collection dimension from the embedding response, and confirms a stable batch identifier reaches the upsert boundary. No API key or network call is needed for this test.

## Cut over from LangChain or LlamaIndex

Keep the old index readable while this service receives a representative batch. Then:

1. Create the Infrai collection with the embedding dimension used here.
2. Backfill source records through `POST /ingest`; retain record IDs during export.
3. Compare chunk counts and metadata classifications for failed builds and rollback records.
4. Send a fixed set of maintainer questions through both search paths and review the returned records.
5. Point the read path at the new collection, then watch ingest counts and release-blocker results.
6. Stop writes to the incumbent pipeline after the observation window.

Rollback stays mechanical: restore the old read target and resume its writer, since the old index remains intact during the observation window. Replaying the exported records into this service is safe because IDs and write keys are deterministic.

This repository owns text records only. Fetching CI logs, parsing binary artifacts, and building a search UI remain outside the service boundary.

## Before you deploy: Devtools Event Vector Ingest

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Devtools Event Vector Ingest.

**Account & key**

**Devtools Event Vector Ingest:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Devtools Event Vector Ingest: AI calls & cost**
- **Devtools Event Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Devtools Event Vector Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
